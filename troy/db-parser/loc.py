#!/usr/bin/env python3
"""Read TROY's localisation tables, so db and save keys can be shown as names.

    python3 loc.py <pack>                    # entry counts
    python3 loc.py <pack> growth             # list keys matching a regex
    python3 loc.py <pack> --export loc.json  # cache to JSON for other tools

Or import it:

    from loc import load_index, display_name

    index = load_index(".../local_zh.pack")
    display_name(index, "troy_dlc1_ama_pen_furies")     # '憤怒者'
    display_name(index, "troy_amazons_penthesilea_horde_growth_3")   # '家奴'

Why two indexes
---------------
Loc keys are `<table>_<field>_<record key>`, e.g.

    land_units_onscreen_name_troy_dlc1_ama_pen_furies

but saves and db tables store the bare record key. `full` keeps the loc keys
verbatim; `short` strips the table prefix so a record key looks up directly.
Some tables also glue a culture suffix onto the record key, which has to come
off the right-hand side as well.

The language packs are SEGA/Creative Assembly's own text and are **not**
redistributed here. Read them from the game install (`local_zh.pack` for
Traditional Chinese, `local_en.pack` for English), and treat any exported JSON
as a local cache — it is gitignored for the same reason.

LOC format
----------
    FF FE        byte order mark
    "LOC"        3 bytes ASCII
    00           one padding byte
    u32          version (1 in shipped files)
    u32          entry count
    entries...   key + text + one trailing tooltip flag byte each

Strings are a u16 *character* count followed by that many UTF-16LE units —
characters, not bytes. As with db.py, a correct parse lands exactly on the end
of the blob; `parse_loc` raises rather than returning a plausible partial.
"""

import argparse
import json
import re
import struct
import sys

from packfile import read_pack

BOM = b"\xff\xfe"
MAGIC = b"LOC"

# Loc keys are "<table>_<field>_<record key>". These are the tables whose
# record keys actually appear in saves and db rows.
PREFIXES = (
    "land_units_onscreen_name_",
    "main_units_onscreen_name_",
    "unit_class_onscreen_name_",
    "building_culture_variants_name_",
    "building_levels_onscreen_name_",
    "regions_onscreen_",
    "regions_battle_name_",
    "factions_screen_name_",
    "technologies_onscreen_name_",
    "character_skills_localised_name_",
    "ancillaries_onscreen_name_",
    "missions_localised_title_",
)

# building_culture_variants keys append a subculture straight onto the record
# key with no separator, so it has to be trimmed from the right as well.
SUFFIXES = (
    "troy_amazons_sbc_horde_amazons",
    "troy_rem_sbc_hordes_aethiopians",
)


def parse_loc(blob):
    """Parse one .loc blob into ({key: text}, version). Raises unless exact."""
    if blob[:2] != BOM or blob[2:5] != MAGIC:
        raise ValueError(f"not a LOC table: starts with {blob[:5]!r}")

    pos = 6  # BOM + "LOC" + one padding byte
    version, count = struct.unpack_from("<II", blob, pos)
    pos += 8

    entries = {}
    for _ in range(count):
        values = []
        for _ in range(2):  # key, then text
            length = struct.unpack_from("<H", blob, pos)[0]
            pos += 2
            values.append(blob[pos:pos + length * 2].decode("utf-16-le", "replace"))
            pos += length * 2
        pos += 1  # tooltip flag
        entries[values[0]] = values[1]

    if pos != len(blob):
        raise ValueError(f"LOC parse consumed {pos} of {len(blob)} bytes")
    return entries, version


def strip_key(loc_key):
    """Reduce a loc key to the bare record key that saves and db rows store."""
    for prefix in PREFIXES:
        if not loc_key.startswith(prefix):
            continue
        bare = loc_key[len(prefix):]
        for suffix in SUFFIXES:
            if bare.endswith(suffix):
                bare = bare[:-len(suffix)]
                break
        return bare or None
    return None


def load_index(pack_path):
    """Read every .loc in a language pack. Returns {'full': ..., 'short': ...}."""
    data, index, _meta = read_pack(pack_path)

    full = {}
    tables = 0
    for name in sorted(index):
        if not name.lower().endswith(".loc"):
            continue
        offset, size, _flag = index[name]
        if size == 0:
            continue
        try:
            entries, _version = parse_loc(data[offset:offset + size])
        except ValueError as exc:
            print(f"[skip] {name}: {exc}", file=sys.stderr)
            continue
        full.update(entries)
        tables += 1

    short = {}
    for loc_key, text in full.items():
        bare = strip_key(loc_key)
        if bare and bare not in short:
            short[bare] = text

    return {"full": full, "short": short, "tables": tables}


def load_cached(path):
    """Load a JSON cache written by --export."""
    with open(path, encoding="utf-8") as handle:
        return json.load(handle)


def display_name(index, key, default=None):
    """Record key -> in-game name. Accepts an index or a bare {key: text} dict."""
    short = index.get("short") if isinstance(index, dict) and "short" in index else index
    if key in short:
        return short[key]

    # Fall back to scanning the full table for a prefixed form, which covers
    # tables not listed in PREFIXES.
    full = index.get("full") if isinstance(index, dict) and "full" in index else {}
    for loc_key, text in full.items():
        if loc_key.endswith(key):
            return text
    return default


def main():
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("pack", help="a language pack, e.g. local_zh.pack")
    parser.add_argument("pattern", nargs="?", help="regex filter on the key")
    parser.add_argument("--export", metavar="PATH", help="write {full, short} JSON")
    parser.add_argument("--limit", type=int, default=40)
    args = parser.parse_args()

    index = load_index(args.pack)
    print(
        f"{index['tables']} loc tables, {len(index['full']):,} entries "
        f"({len(index['short']):,} keyed by record)",
        file=sys.stderr,
    )

    if args.export:
        with open(args.export, "w", encoding="utf-8") as handle:
            json.dump({"full": index["full"], "short": index["short"]},
                      handle, ensure_ascii=False)
        print(f"-> {args.export}", file=sys.stderr)

    if args.pattern:
        regex = re.compile(args.pattern, re.I)
        hits = [(k, v) for k, v in index["short"].items() if regex.search(k)]
        print(f"{len(hits):,} record keys matching '{args.pattern}'\n")
        for key, value in sorted(hits)[:args.limit]:
            print(f"  {key:56s} {value}")
        if len(hits) > args.limit:
            print(f"  ... and {len(hits) - args.limit:,} more")
    return 0


if __name__ == "__main__":
    sys.exit(main())
