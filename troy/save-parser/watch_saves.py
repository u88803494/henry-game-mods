#!/usr/bin/env python3
"""Watch the TROY save directory and append a per-turn snapshot for every new save.

Each new `.save` file is parsed with esf_parser and reduced to a compact JSON
line: turn, resources, unit roster with experience levels, and horde buildings.
Full parse trees are never kept — they are ~30 MB each once decompressed.

    python3 watch_saves.py                    # watch forever
    python3 watch_saves.py --once             # process pending saves and exit
    python3 watch_saves.py --backfill 20      # also parse the 20 newest existing saves

Output is JSON Lines at snapshots.jsonl (gitignored), one object per save.
"""

import argparse
import json
import os
import re
import sys
import threading
import time
import traceback

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from esf_parser import parse_esf_bytes

DEFAULT_SAVE_DIR = os.path.expanduser(
    "~/Library/Application Support/Feral Interactive/Troy/VFS/User/AppData/"
    "Roaming/The Creative Assembly/Troy/save_games"
)
DEFAULT_OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "snapshots.jsonl")

# Resource pools worth tracking; god attitudes and the Mythos pools are skipped.
RESOURCE_KEYS = {
    "troy_food", "troy_wood", "troy_stones", "troy_bronze", "troy_gold",
}


def children(node):
    if isinstance(node, dict) and "_g" in node:
        for group in node["_g"]:
            for child in group:
                yield child


def find_all(node, record_name, out=None):
    if out is None:
        out = []
    if isinstance(node, dict) and node.get("_r") == record_name:
        out.append(node)
    for child in children(node):
        find_all(child, record_name, out)
    return out


def first_str(node, depth=0, limit=6):
    """First string found in a shallow walk — used for slot/unit keys."""
    if isinstance(node, str) and node:
        return node
    if depth < limit and isinstance(node, dict):
        for child in children(node):
            found = first_str(child, depth + 1, limit)
            if found:
                return found
    return None


def player_faction(root, want="penthesilea"):
    for faction in find_all(root, "FACTION"):
        for child in children(faction):
            if isinstance(child, str) and want in child:
                return child, faction
    return None, None


def read_resources(faction):
    """Each pool inside POOLED_RESOURCE is the triple (key, amount, FACTOR node).

    Matching on the trailing POOLED_RESOURCE_FACTOR is what makes this safe:
    plain "string followed by int" also matches breakdown entries such as
    ('looting', 27) and unrelated nodes elsewhere under the faction.
    """
    out = {}
    for pool in find_all(faction, "POOLED_RESOURCE"):
        seq = list(children(pool))
        for i in range(len(seq) - 2):
            key, value, factor = seq[i], seq[i + 1], seq[i + 2]
            if not isinstance(key, str) or not isinstance(value, int):
                continue
            if not (isinstance(factor, dict) and factor.get("_r") == "POOLED_RESOURCE_FACTOR"):
                continue
            if key in RESOURCE_KEYS and key not in out:
                out[key] = value
    return out


def read_units(faction):
    """UNIT primitives are [id, men, max_men, ?, ?, experience, level, progress, ...]."""
    units = []
    for unit in find_all(faction, "UNIT"):
        key_nodes = find_all(unit, "UNIT_RECORD_KEY")
        key = first_str(key_nodes[0]) if key_nodes else None
        prims = [c for c in children(unit) if not isinstance(c, dict)]
        if key is None or len(prims) < 8:
            continue
        units.append({
            "key": key,
            "men": prims[1],
            "max_men": prims[2],
            "exp": prims[5],
            "level": prims[6],
            "progress": round(prims[7], 4) if isinstance(prims[7], float) else prims[7],
        })
    return units


def read_buildings(faction):
    slots = []
    for index, slot in enumerate(find_all(faction, "MILITARY_FORCE_SLOT")):
        key = first_str(slot)
        # Empty slots only carry the generic horde_primary/horde_secondary labels.
        if key in (None, "horde_primary", "horde_secondary"):
            key = None
        slots.append({"slot": index, "building": key})
    return slots


def read_technologies(faction):
    techs = set()

    def walk(node):
        if isinstance(node, str) and node.startswith("troy_tech_"):
            techs.add(node)
        for child in children(node):
            walk(child)

    walk(faction)
    return sorted(techs)


def split_name(path):
    """Save names are "<label>.<turn><campaign-id>.save".

    The campaign id has no fixed width — it is just a number, so it can be 9 or
    10 digits depending on the campaign. That makes the turn undecidable from
    the name alone; the authoritative turn comes from CAMPAIGN_CALENDAR inside
    the save. `number` is kept whole here and only used to group saves.
    """
    name = os.path.basename(path)
    match = re.match(r"^(.*?)\.?(\d+)\.save$", name)
    label, number = (match.group(1), match.group(2)) if match else (name, "")
    return name, label, number


def campaign_of(path, width=9):
    """Group key for a save. Trailing `width` digits are always part of the id."""
    return split_name(path)[2][-width:]


def read_turn(root):
    """CAMPAIGN_CALENDAR holds DATE(turn, season, ...) — the real turn number."""
    for calendar in find_all(root, "CAMPAIGN_CALENDAR"):
        for date in find_all(calendar, "DATE"):
            values = [c for c in children(date) if isinstance(c, int)]
            if values:
                return values[0], (values[1] if len(values) > 1 else None)
    return None, None


def summarise(path):
    name, label, number = split_name(path)

    root = parse_esf_bytes(open(path, "rb").read())
    faction_key, faction = player_faction(root)
    if faction is None:
        raise ValueError("player faction not found in save")
    turn, season = read_turn(root)

    return {
        "file": name,
        "label": label,
        "campaign": number[-9:],
        "turn": turn,
        "season": season,
        "mtime": round(os.path.getmtime(path), 3),
        "faction": faction_key,
        "resources": read_resources(faction),
        "units": read_units(faction),
        "buildings": read_buildings(faction),
        "technologies": read_technologies(faction),
    }


def stable(path, settle=2.0, tries=10):
    """Wait until the file stops growing — the game may still be writing it."""
    last = -1
    for _ in range(tries):
        try:
            size = os.path.getsize(path)
        except OSError:
            return False
        if size == last and size > 0:
            return True
        last = size
        time.sleep(settle)
    return False


def load_seen(out_path):
    seen = set()
    if os.path.exists(out_path):
        with open(out_path, encoding="utf-8") as handle:
            for line in handle:
                try:
                    seen.add(json.loads(line)["file"])
                except (ValueError, KeyError):
                    continue
    return seen


def report(snap):
    res = snap["resources"]
    levelled = sorted(
        (u for u in snap["units"] if u["level"] >= 4),
        key=lambda u: (-u["level"], -u["progress"]),
    )
    built = sum(1 for b in snap["buildings"] if b["building"])
    parts = [f"turn {snap['turn']}"]
    parts.append(" ".join(f"{k.replace('troy_', '')}={v}" for k, v in sorted(res.items())))
    parts.append(f"buildings {built}/{len(snap['buildings'])}")
    if levelled:
        top = levelled[0]
        parts.append(f"top: {top['key'].split('_')[-1]} L{top['level']} {top['progress']:.0%}")
    return " | ".join(parts)


def process(path, out_path, seen):
    name = os.path.basename(path)
    if name in seen:
        return False
    if not stable(path):
        return False
    try:
        snap = summarise(path)
    except Exception:
        print(f"[skip] {name}", file=sys.stderr)
        traceback.print_exc(file=sys.stderr)
        seen.add(name)  # do not retry a save that will not parse
        return False
    with open(out_path, "a", encoding="utf-8") as handle:
        handle.write(json.dumps(snap, ensure_ascii=False) + "\n")
    seen.add(name)
    print(report(snap), flush=True)
    return True


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--save-dir", default=DEFAULT_SAVE_DIR)
    parser.add_argument("--out", default=DEFAULT_OUT)
    parser.add_argument("--interval", type=float, default=20.0)
    parser.add_argument("--once", action="store_true", help="process pending saves and exit")
    parser.add_argument("--backfill", type=int, default=0,
                        help="also process the N newest existing saves")
    parser.add_argument("--campaign", default=None,
                        help="campaign id to follow (default: the newest save's campaign)")
    args = parser.parse_args()

    if not os.path.isdir(args.save_dir):
        print(f"save dir not found: {args.save_dir}", file=sys.stderr)
        return 1

    def listing():
        entries = []
        for name in os.listdir(args.save_dir):
            if not name.endswith(".save"):
                continue
            full = os.path.join(args.save_dir, name)
            try:
                entries.append((os.path.getmtime(full), full))
            except OSError:
                continue
        entries.sort()
        return entries

    all_saves = listing()
    if not all_saves:
        print("no saves found", file=sys.stderr)
        return 1

    # One campaign at a time: other campaigns have their own Amazon faction as an
    # AI, so without this filter every unrelated save yields a bogus snapshot.
    campaign = args.campaign or campaign_of(all_saves[-1][1])
    mine = [e for e in all_saves if campaign_of(e[1]) == campaign]
    print(f"campaign {campaign}: {len(mine)} saves on disk", file=sys.stderr)

    seen = load_seen(args.out)
    start = time.time()

    for _, path in mine[-args.backfill:] if args.backfill else []:
        process(path, args.out, seen)

    if args.once and not args.backfill:
        for mtime, path in mine:
            if mtime >= start:
                process(path, args.out, seen)
    if args.once:
        return 0

    print(f"watching {args.save_dir} (every {args.interval:.0f}s)", file=sys.stderr)
    while True:
        for mtime, path in listing():
            if mtime >= start and campaign_of(path) == campaign:
                process(path, args.out, seen)
        time.sleep(args.interval)


if __name__ == "__main__":
    code = [0]

    def target():
        try:
            code[0] = main() or 0
        except KeyboardInterrupt:
            code[0] = 0
        except Exception:
            traceback.print_exc()
            code[0] = 1

    try:
        threading.stack_size(1024 * 1024 * 1024)
    except (ValueError, RuntimeError) as exc:
        print("stack_size warn:", exc, file=sys.stderr)
    thread = threading.Thread(target=target)
    thread.start()
    thread.join()
    sys.exit(code[0])
