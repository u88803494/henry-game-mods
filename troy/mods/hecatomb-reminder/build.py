#!/usr/bin/env python3
"""Build hecatomb_reminder.pack from the Lua source next to this script.

    python3 build.py [output.pack]

The pack must be PFH_TYPE_MOD for the in-game Mod Manager to list it, and the
Lua has to live under script/campaign/main_troy/mod/ with a filename matching
the function it defines — that is what lib_mod_loader looks for.
"""

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "db-parser"))
from packfile import write_pack, read_pack, PFH_TYPE_MOD

HERE = os.path.dirname(os.path.abspath(__file__))
SCRIPT = "hecatomb_reminder.lua"
IN_PACK = "script\\campaign\\main_troy\\mod\\" + SCRIPT


def main():
    out = sys.argv[1] if len(sys.argv) > 1 else os.path.join(HERE, "hecatomb_reminder.pack")
    source = open(os.path.join(HERE, SCRIPT), "rb").read()
    size = write_pack(out, {IN_PACK: source}, pack_type=PFH_TYPE_MOD)

    # Verify by reading it back: the byte count must land exactly, and the
    # payload must survive the round trip.
    data, index, meta = read_pack(out)
    offset, length, _flag = index[IN_PACK]
    ok = data[offset:offset + length] == source and meta["bytes_accounted"] == meta["total_size"]
    print(f"{out}\n  {size} bytes, {meta['index_entries']} entry, verified: {'yes' if ok else 'NO'}")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
