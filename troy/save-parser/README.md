# Total War Saga: TROY — Save File Parser

Reads `.save` files from *A Total War Saga: TROY* directly, without any
in-game mod or DLL injection. Decompresses the nested LZMA-compressed ESF
(CAAB) structure and walks the full node tree into plain Python objects
(dicts/lists/primitives) so you can query faction state, army composition,
diplomacy, technology, territory, etc. straight from the save file.

## Why this exists

Reverse-engineered from scratch by reading the actual save bytes — no
existing Troy-specific save reader was available. Useful for anyone who
wants to script analysis of their own campaign (trend tracking across
turns, army audits, "what changed since last save") without touching the
game process itself.

## Save file location (macOS, Feral port)

```
~/Library/Application Support/Feral Interactive/Troy/VFS/User/AppData/Roaming/The Creative Assembly/Troy/save_games/
```

On Windows it's the equivalent `.../The Creative Assembly/Troy/save_games/`
under `%APPDATA%`.

## Usage

```bash
python3 esf_parser.py <path-to-.save> <output.pkl>
```

Or import directly:

```python
from esf_parser import parse_esf_bytes

data = open("mysave.save", "rb").read()
root = parse_esf_bytes(data)  # recursively decompresses + parses
```

`root` is a dict: `{'_r': record_name, '_v': version, '_g': [[child, ...], ...]}`
for record nodes; primitive nodes are native Python values (int/float/str/
bool/bytes/tuple/list). Write a small recursive `find_all(node, record_name)`
helper to search the tree — see the format notes below for the node names
you'll actually want (`FACTION`, `MILITARY_FORCE`, `CHARACTER`, `REGION`,
`FACTION_PROVINCE_MANAGER`, `OLD_DIPLOMACY_MANAGER`, `POOLED_RESOURCE_MANAGER`,
`FACTION_TECHNOLOGY_MANAGER`, ...).

Needs a thread with a large stack for deep recursion on real save files —
see the `__main__` block for the `threading.stack_size(1024*1024*1024)`
pattern.

## Format notes (ESF / CAAB)

- Outer file: 16-byte header (`CA AB 00 00` magic, unknown u32, timestamp,
  string-table offset), then a node tree, then three string tables (record
  names, UTF-16 strings, ASCII strings).
- The root record's last child is usually a `COMPRESSED_DATA` node holding
  the *entire rest of the save* as an LZMA1-compressed inner ESF (same
  format, recursively). `parse_esf_bytes` detects and unwraps this
  automatically.
- CAULEB128 (the length-prefix encoding used throughout) is MSB-first, not
  standard LEB128: `value = (value << 7) | (byte & 0x7f)`, continuing while
  the high bit is set.
- Full node-type marker table and record-header bit layout are in the
  constants at the top of `esf_parser.py`, derived from reading
  [RPFM](https://github.com/Frodo45127/rpfm)'s Rust implementation
  (`rpfm_lib/src/files/esf/`), which handles the same CAAB format used
  across several Total War titles.

## Unit / building / character names

The parser gives you *keys* (`troy_ith_ambushers`, `troy_main_dan_ithaca`,
etc.), not display names. To resolve these to readable text you need the
game's own localisation pack (`local_zh.pack` for Traditional Chinese, or
`local_en.pack` for English, etc.) — **not included here**, since that file
contains SEGA/Creative Assembly's own text and isn't ours to redistribute.
It's a PackFile (`PFH5` format) sitting next to `data.pack` in your game
install; extracting the `text/localisation__.loc` entry from it and parsing
that `.loc` format (UTF-16 string table keyed by hashed string names) gives
you the key→text mapping.

On this machine (Epic Games install), the Traditional Chinese pack lives at:

```
/Users/Shared/Epic Games/TotalWarSagaTROY/TroyData/data/local_zh.pack
```

Ask if you want the extraction script for this too — it's a similar amount
of code (parse the `PFH5` PackFile index, pull out `text/localisation__.loc`,
then parse the `.loc` UTF-16 string table). Regenerate `loc_zh.json` locally
from that path whenever you need it; it's gitignored so it never gets
committed.

## License

MIT, same as the rest of this repo.
