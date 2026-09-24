# Total War Saga: TROY — DB Table Parser

Reads and writes the game's own **DB tables** straight out of its PackFiles,
without RPFM or any other GUI tool. Three modules:

- `packfile.py` — unpacks and builds PFH5 containers (`data_db.pack`, `data.pack`, `local_zh.pack`, mod packs)
- `db.py` — decodes a binary DB table into plain Python dicts, and encodes them back
- `loc.py` — reads the localisation tables, so keys can be shown as in-game names

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

**All 802 tables in `data_db.pack` decode, and all 802 re-encode byte-exact.**
`roundtrip_test.py` is the gate:

```bash
python3 roundtrip_test.py     # decode -> encode -> compare, exits non-zero on any mismatch
```

Two things were needed to get every table, both worth knowing before touching
another Total War title:

- **Tables predating the version marker carry no version at all.** Their schema
  is filed under `0`. `decode()` looks up `0` in that case but reports `version`
  as `None`, so `encode()` knows not to write a marker back.
- **A schema can define more fields than a given build stores.** `land_units`
  v44 defines 63 but this build has 61 (`onscreen_name` and `concealed_name`
  came later). `decode()` drops trailing fields and retries, accepting only an
  exact byte match — so a shortened list can't be mistaken for a correct one.

Do **not** sort fields by `ca_order`: that is the assembly-kit display order,
not the serialisation order. `projectiles_tables` proves it — its `ca_order`
runs `0,1,2,3,5,…,16,4,17` while file order decodes byte-exact.

## Localisation: keys to in-game names

Everything above speaks in keys. `loc.py` turns them into what the game shows:

```bash
python3 loc.py ".../local_zh.pack"                      # counts
python3 loc.py ".../local_zh.pack" growth               # search record keys
python3 loc.py ".../local_zh.pack" --export loc_zh.json # cache for other tools
```

```python
from loc import load_index, display_name

index = load_index(".../local_zh.pack")
display_name(index, "troy_dlc1_ama_pen_furies")                 # '憤怒者'
display_name(index, "troy_amazons_penthesilea_horde_growth_3")  # '家奴'
```

`../save-parser/watch_saves.py` imports `display_name` from here rather than
carrying its own copy, so there is one implementation. It loads the exported
JSON instead of the 12 MB pack, because a watcher parses saves continuously
and shouldn't re-read the language pack every time.

### Two indexes

Loc keys are `<table>_<field>_<record key>`:

    land_units_onscreen_name_troy_dlc1_ama_pen_furies

but saves and DB rows store the bare record key. So `load_index()` returns
both: `full` keeps loc keys verbatim (60,061 entries), `short` strips the
table prefix so a record key looks up directly (6,949). Some tables also glue
a culture suffix onto the record key, which has to come off the right as well
— see `PREFIXES` and `SUFFIXES`.

### Why this matters

Working from keys alone invites plausible but wrong translations. `pen_furies`
reads as "Furies", the Greek Erinyes, but the game calls them **憤怒者**;
`pen_hippomachoi` is **亞馬遜槍騎兵** in-game, not a transliteration;
`gen_oathsworn` is **守誓者**, not 誓約者. Analysis written in invented names
doesn't survive contact with the actual UI.

### Format

    FF FE        byte order mark
    "LOC"        3 bytes ASCII
    00           one padding byte
    u32          version (1 in shipped files)
    u32          entry count
    entries...   key + text + one trailing tooltip flag byte

Strings are a u16 *character* count followed by that many UTF-16LE units —
characters, not bytes. Same acceptance rule as DB tables: a correct parse
consumes the blob exactly, otherwise `parse_loc` raises.

The language packs are SEGA/Creative Assembly's own text and are **not**
redistributed here; read them from the game install, and treat exported JSON
as a local cache (it is gitignored).

## Format notes

Both files carry the format details in their module docstrings — PFH5 header
and index layout in `packfile.py`, table header and the length-prefixed string
encoding in `db.py`. The ESF/CAAB notes for save files live in
`../save-parser/README.md`.

## License

MIT, same as the rest of this repo.
