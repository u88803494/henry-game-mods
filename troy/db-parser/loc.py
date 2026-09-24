#!/usr/bin/env python3
"""Read TROY's localisation tables, so db keys can be shown as in-game names.

    python3 loc.py <pack> [regex]        # list matching key/value pairs
    python3 loc.py local_zh.pack growth  # e.g. -> 家奴, 戰奴, 被俘的奴隸

Or import it:

    from loc import load_from_pack, display_name

    loc = load_from_pack(".../local_zh.pack")
    display_name(loc, "troy_amazons_penthesilea_horde_growth_3")   # '家奴'

Why this matters
----------------
Everything else in this directory speaks in keys — `growth_3`, `resources_2`,
`troy_sling_stone_poor`. The game speaks in names. Without this, any analysis
has to be translated by hand before it means anything to a player.

The language packs are SEGA/Creative Assembly's own text and are NOT
redistributed here. Read them from wherever the game is installed, e.g.
`.../TroyData/data/local_zh.pack` (Traditional Chinese) or `local_en.pack`.

LOC format
----------
    FF FE                byte order mark
    "LOC"                3 bytes, ASCII
    00                   one padding byte
    u32                  version (1 in the shipped files)
    u32                  entry count
    entries...           key + value + one trailing bool byte each

Strings are u16 *character* count followed by that many UTF-16LE code units --
note the count is characters, not bytes, so the byte length is twice that.

As with db.py, a correct parse lands exactly on the end of the blob; anything
else means the format assumption is wrong, so `parse_loc` raises rather than
returning a plausible-looking partial result.
"""

import argparse
import os
import re
import struct
import sys

from packfile import read_pack

BOM = b"\xff\xfe"
MAGIC = b"LOC"
DEFAULT_ENTRY = "text\\localisation__.loc"

# How the game names things, by table. Learned by inspecting local_zh.pack:
# a key may appear under several of these, so lookups try them in order.
#
# `building_culture_variants_name_` is the odd one out -- the subculture is
# appended directly to the building key with no separator, which is why
# display_name() also tries a prefix match for it.
NAME_PATTERNS = (
    "building_culture_variants_name_{key}",
    "building_levels_onscreen_name_{key}",
    "land_units_onscreen_name_{key}",
    "main_units_onscreen_name_{key}",
    "units_custom_battle_permissions_onscreen_name_{key}",
    "missions_localised_title_{key}",
    "campaign_localised_strings_localised_string_{key}",
    "factions_screen_name_{key}",
    "regions_onscreen_{key}",
    "technologies_onscreen_name_{key}",
    "unit_description_short_texts_text_{key}",
)


def parse_loc(blob):
    """Parse a .loc blob into {key: value}. Raises if it doesn't consume exactly."""
    if blob[:2] != BOM or blob[2:5] != MAGIC:
        raise ValueError(f"not a LOC file: starts with {blob[:5]!r}")

    pos = 6  # BOM + "LOC" + one padding byte
    version = struct.unpack_from("<I", blob, pos)[0]
    pos += 4
    count = struct.unpack_from("<I", blob, pos)[0]
    pos += 4

    def read_string(at):
        length = struct.unpack_from("<H", blob, at)[0]
        at += 2
        text = blob[at:at + length * 2].decode("utf-16-le", "replace")
        return text, at + length * 2

    entries = {}
    for _ in range(count):
        key, pos = read_string(pos)
        value, pos = read_string(pos)
        pos += 1  # trailing bool
        entries[key] = value

    if pos != len(blob):
        raise ValueError(
            f"LOC parse consumed {pos} of {len(blob)} bytes -- format mismatch"
        )
    return entries, version


def load_from_pack(pack_path, entry=DEFAULT_ENTRY):
    """Pull the localisation table straight out of a language pack."""
    data, index, _meta = read_pack(pack_path)
    if entry not in index:
        available = [k for k in index if k.endswith(".loc")]
        raise KeyError(f"{entry} not in pack; found {available}")
    offset, size, _flag = index[entry]
    entries, _version = parse_loc(data[offset:offset + size])
    return entries


def display_name(loc, key, default=None):
    """Best-effort key -> in-game name, trying each known naming convention."""
    for pattern in NAME_PATTERNS:
        candidate = pattern.format(key=key)
        if candidate in loc:
            return loc[candidate]

    # building_culture_variants_name_ appends a subculture with no separator,
    # so an exact match fails and we have to look for the prefix instead.
    prefix = "building_culture_variants_name_" + key
    for loc_key, value in loc.items():
        if loc_key.startswith(prefix):
            return value
    return default


def main():
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("pack", help="a language pack, e.g. local_zh.pack")
    parser.add_argument("pattern", nargs="?", help="regex filter on the key")
    parser.add_argument("--entry", default=DEFAULT_ENTRY)
    parser.add_argument("--limit", type=int, default=40)
    args = parser.parse_args()

    loc = load_from_pack(args.pack, args.entry)
    print(f"{len(loc):,} entries")

    if not args.pattern:
        return 0

    regex = re.compile(args.pattern, re.I)
    hits = [(k, v) for k, v in loc.items() if regex.search(k)]
    print(f"{len(hits):,} matching '{args.pattern}'\n")
    for key, value in sorted(hits)[:args.limit]:
        print(f"  {key:76s} {value}")
    if len(hits) > args.limit:
        print(f"  ... and {len(hits) - args.limit:,} more")
    return 0


if __name__ == "__main__":
    sys.exit(main())
