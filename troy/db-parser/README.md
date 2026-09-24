# Total War Saga: TROY — DB Table Parser

Reads the game's own **DB tables** straight out of its PackFiles, without RPFM
or any other GUI tool. Two small modules:

- `packfile.py` — unpacks the PFH5 container (`data_db.pack`, `data.pack`, `local_zh.pack`, ...)
- `db.py` — decodes a binary DB table into plain Python dicts

## Why this exists, next to `save-parser/`

These answer different questions, and conflating them costs a lot of wasted
effort:

| | answers | example |
|---|---|---|
| `save-parser/` | **what is true in this campaign right now** | who owns that region, how full is the garrison, which units are in this army |
| `db-parser/` | **what the rules are** | which building unlocks which unit, what a sling's armour-piercing value is |

Unit stats, building chains and mission definitions are *not* in the save at
all — the save only references them by key. Reverse-engineering the save to
answer a rules question is a detour; it has to come from here.

## Usage

```bash
# one-off: fetch the community schema (note the hyphen in rpfm-schemas)
curl -LO https://raw.githubusercontent.com/Frodo45127/rpfm-schemas/master/schema_troy.ron

python3 db.py "/Users/Shared/Epic Games/TotalWarSagaTROY/TroyData/data/data_db.pack" missile_weapons
python3 packfile.py .../data_db.pack "projectile|missile"   # list matching tables
```

```python
from db import read_table

version, fields, rows, used, total = read_table(pack, "projectiles", "schema_troy.ron")
assert used == total          # see "Verifying a decode" below
```

`schema_troy.ron` is gitignored — it's a 6.7 MB third-party file, and it's one
`curl` away.

## Verifying a decode

Records are packed back to back with no padding, so a correct decode consumes
**exactly** the length of the blob. `decode()` returns the byte count for this
reason, and the CLI exits non-zero when it doesn't match.

This matters more than it sounds: a single wrong field type doesn't raise, it
silently shifts every value after it. Numbers that look plausible are not
evidence the decode was right — the byte count is.

## Status

Verified exact on, among others:

| table | version | rows |
|---|---|---|
| `missile_weapons` | 11 | 104 |
| `projectiles` | 46 | 125 |

Known failures: **`missions`** (version 9) and **`land_units`** (version 44)
both run off the end of the blob. Diagnosed so far: the schema *does* define
those versions, and every field type they use (`StringU8`, `OptionalStringU8`,
`I32`, `F32`, `Boolean`) is already implemented — so it isn't a missing type.
Most likely the field list is subtly wrong for this build of the game, which
would make `patches.ron` from the same schema repo the next thing to try.

Until that's fixed, unit-level lookups (which weapon a given unit carries) and
mission definitions aren't reachable; weapon- and projectile-level data is.

## Localisation: keys to in-game names

Everything above speaks in keys. `loc.py` turns them into what the game
actually shows:

```bash
python3 loc.py "/Users/Shared/Epic Games/TotalWarSagaTROY/TroyData/data/local_zh.pack" growth
```

```python
from loc import load_from_pack, display_name

loc = load_from_pack(".../local_zh.pack")          # 60,061 entries
display_name(loc, "troy_amazons_penthesilea_horde_growth_3")   # '家奴'
display_name(loc, "troy_dlc1_ama_pen_furies")                  # '憤怒者'
```

The language packs are SEGA/Creative Assembly's own text and are **not**
redistributed here — read them from the game install (`local_zh.pack` for
Traditional Chinese, `local_en.pack` for English, next to `data.pack`).

`display_name()` tries each known naming convention in turn, because a key can
be filed under several tables (`building_levels_onscreen_name_`,
`land_units_onscreen_name_`, `missions_localised_title_`, and so on).
`building_culture_variants_name_` needs special handling: it appends the
subculture straight onto the building key with no separator, so an exact
lookup misses and a prefix scan is required.

This matters more than it sounds. Working from keys alone invites plausible
but wrong translations — `pen_furies` reads as "Furies", the Greek Erinyes,
but the game calls them **憤怒者**; `pen_hippomachoi` is not a transliteration
in-game but **亞馬遜槍騎兵**. Analysis written in invented names doesn't
survive contact with the actual UI.

LOC format: `FF FE` BOM, `"LOC"`, one padding byte, u32 version, u32 count,
then entries of key + value + one trailing bool. Strings are a u16 *character*
count followed by that many UTF-16LE units — characters, not bytes. As with DB
tables, a correct parse consumes the blob exactly, and `parse_loc` raises if
it doesn't.

## Format notes

Both files carry the format details in their module docstrings — PFH5 header
and index layout in `packfile.py`, table header and the length-prefixed string
encoding in `db.py`. The ESF/CAAB notes for save files live in
`../save-parser/README.md`.

## License

MIT, same as the rest of this repo.
