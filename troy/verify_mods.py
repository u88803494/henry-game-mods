#!/usr/bin/env python3
"""Tell you whether TROY actually loaded your mods, without needing the game open.

Run it after quitting the game:

    python3 verify_mods.py

It reads what the game left behind — the mod folder, the Lua mod log, and the
VFS log — and reports whether each pack was found, loaded, and executed.

Why this exists
---------------
Verifying a mod normally means watching the game: did the Mod Manager list it,
did the script run, did anything break. But TROY writes all of that to disk, so
the answer is recoverable afterwards. That matters when the person who can
launch the game and the person reading the logs aren't in the same place.

For the Lua log to say anything useful the mod must call ModLog(); for the VFS
log to exist at all, `vfs_log_level` in preferences.script.txt must be 1 or
higher (0 = off, which is the default).
"""

import os
import re
import sys

FERAL_ROOT = os.path.expanduser(
    "~/Library/Application Support/Feral Interactive/Troy/VFS"
)
MODS_DIR = os.path.join(FERAL_ROOT, "Local", "mods")
GAME_DATA = os.path.join(
    FERAL_ROOT, "User", "AppData", "Roaming", "The Creative Assembly", "Troy"
)
LOGS_DIR = os.path.join(GAME_DATA, "logs")
PREFS = os.path.join(GAME_DATA, "scripts", "preferences.script.txt")

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "db-parser"))


def rel_age(path):
    """'3 minutes ago' style, so you can tell logs from this run apart from old ones."""
    import time

    try:
        delta = time.time() - os.path.getmtime(path)
    except OSError:
        return "missing"
    for limit, unit, name in ((60, 1, "s"), (3600, 60, "m"), (86400, 3600, "h")):
        if delta < limit:
            return f"{int(delta / unit)}{name} ago"
    return f"{int(delta / 86400)}d ago"


def check_packs():
    """Every .pack in the mod folder, with its contents listed."""
    print("== mod folder ==")
    print(f"   {MODS_DIR}")
    if not os.path.isdir(MODS_DIR):
        print("   MISSING — the game has never created it")
        return []

    packs = sorted(f for f in os.listdir(MODS_DIR) if f.endswith(".pack"))
    if not packs:
        print("   no .pack files")
        return []

    from packfile import read_pack

    names = []
    for pack in packs:
        path = os.path.join(MODS_DIR, pack)
        size = os.path.getsize(path)
        try:
            data, index, meta = read_pack(path)
            ok = meta["bytes_accounted"] == meta["total_size"]
            entries = sorted(index)
            print(f"\n   {pack}  ({size:,} bytes, {rel_age(path)})")
            print(f"      structure: {'valid' if ok else 'CORRUPT'}, {len(entries)} entries")
            for entry in entries[:6]:
                print(f"        {entry}")
            if len(entries) > 6:
                print(f"        ... and {len(entries) - 6} more")
            # Lua mods are the ones the mod loader will try to execute by name.
            # In-pack paths use backslashes, which os.path.basename does not
            # split on POSIX — take the last segment manually.
            for entry in entries:
                if entry.endswith(".lua"):
                    names.append(entry.replace("\\", "/").rsplit("/", 1)[-1][:-4])
        except Exception as exc:
            print(f"\n   {pack}  ({size:,} bytes)")
            print(f"      UNREADABLE: {type(exc).__name__}: {exc}")
    return names


def check_vfs_setting():
    print("\n== vfs_log_level ==")
    try:
        text = open(PREFS, encoding="utf-8", errors="replace").read()
    except OSError:
        print("   preferences.script.txt not found")
        return
    match = re.search(r"^vfs_log_level (\d+);", text, re.M)
    if not match:
        print("   setting not present")
        return
    level = int(match.group(1))
    note = "off — VFS log will not be written" if level == 0 else "on"
    print(f"   {level}  ({note})")


def check_lua_log(expected):
    """The mod loader prints a Loading/Executing banner even with zero mods."""
    path = os.path.join(LOGS_DIR, "lua_mod_log.txt")
    print("\n== lua_mod_log.txt ==")
    if not os.path.exists(path):
        print("   missing — the game has not run the mod loader yet")
        return
    print(f"   {rel_age(path)}, {os.path.getsize(path):,} bytes")
    text = open(path, encoding="utf-8", errors="replace").read()

    for section in ("Loading Mods", "Executing Mods"):
        # Content between this banner and the next one (or end of file).
        pattern = re.compile(
            re.escape(section) + r"\s*\*+\s*(.*?)(?=\*{10,}|\Z)", re.S
        )
        match = pattern.search(text)
        body = (match.group(1).strip() if match else "")
        print(f"\n   [{section}]")
        if body:
            for line in body.splitlines():
                if line.strip():
                    print(f"      {line.strip()}")
        else:
            print("      (empty)")

    if expected:
        print("\n   expected from the packs above:")
        for name in expected:
            hit = name in text
            print(f"      {'FOUND   ' if hit else 'NOT SEEN'} {name}")

    # Anything our own mods logged via ModLog().
    tagged = [l for l in text.splitlines() if l.strip().startswith("[")]
    if tagged:
        print("\n   mod output:")
        for line in tagged[-25:]:
            print(f"      {line.strip()}")


def check_other_logs():
    print("\n== other logs ==")
    if not os.path.isdir(LOGS_DIR):
        print("   logs directory missing")
        return
    for name in sorted(os.listdir(LOGS_DIR)):
        path = os.path.join(LOGS_DIR, name)
        if not os.path.isfile(path):
            continue
        size = os.path.getsize(path)
        flag = ""
        if name == "no_clean_exit":
            flag = "  <- game did not exit cleanly (crash or force quit)"
        if re.search(r"vfs", name, re.I):
            flag = "  <- VFS log, lists which packs were mounted"
        print(f"   {name:24s} {size:>9,} bytes  {rel_age(path):>10s}{flag}")

    # Surface errors from the general log, which is where script failures land.
    info = os.path.join(LOGS_DIR, "log_info.log.txt")
    if os.path.exists(info):
        text = open(info, encoding="utf-8", errors="replace").read()
        bad = [l for l in text.splitlines()
               if re.search(r"error|fail|exception|script_error", l, re.I)]
        if bad:
            print(f"\n   errors in log_info.log.txt ({len(bad)} lines, last 10):")
            for line in bad[-10:]:
                print(f"      {line.strip()[:160]}")


def main():
    print("TROY mod verification\n")
    expected = check_packs()
    check_vfs_setting()
    check_lua_log(expected)
    check_other_logs()
    print(
        "\nWhat to look for:\n"
        "  - each pack reports 'structure: valid'\n"
        "  - [Loading Mods] and [Executing Mods] name your Lua file\n"
        "  - 'mod output' shows the lines your mod logged\n"
        "  - no_clean_exit present means the game crashed or was force quit"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
