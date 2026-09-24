#!/usr/bin/env python3
"""Reader for TROY's PFH5 PackFiles (`data.pack`, `data_db.pack`, `local_zh.pack`, ...).

A PackFile is the container format the game ships its data in: a small header,
a flat index of every packed file, then all the file bodies concatenated in
index order.

    python3 packfile.py <pack> [regex]     # list entries, optionally filtered

Or import it:

    data, index, meta = read_pack("data_db.pack")
    offset, size, flag = index["db\\\\missile_weapons_tables\\\\data__"]
    blob = data[offset:offset + size]

Format notes (PFH5, as used by TROY)
------------------------------------
Header is 28 bytes, all little-endian u32:

    0x00  "PFH5" magic
    0x04  bitmask / pack type
    0x08  dependency count      (number of PackFile names this one depends on)
    0x0C  dependency block size
    0x10  file count
    0x14  index size            (bytes, starting at 0x1C)
    0x18  timestamp

The index starts at 0x1C and is `index size` bytes long. Each entry is:

    u32   uncompressed size of the file body
    u8    flag (0 in every vanilla TROY pack seen so far)
    ...   NUL-terminated path, backslash-separated ("db\\foo_tables\\data__")

File bodies follow immediately after the index, in the same order as the
index, with no padding — so each body's offset is just the running sum of all
preceding sizes. There is no per-file offset stored anywhere.
"""

import re
import struct
import sys
import time

MAGIC = b"PFH5"
HEADER_SIZE = 0x1C


def read_pack(path):
    """Parse a PackFile. Returns (raw_bytes, {path: (offset, size, flag)}, meta)."""
    data = open(path, "rb").read()
    if data[:4] != MAGIC:
        raise ValueError(f"not a PFH5 PackFile: magic is {data[:4]!r}")

    _bitmask, _dep_count, _dep_size, file_count, index_size, _ts = struct.unpack_from(
        "<IIIIII", data, 4
    )

    offset = HEADER_SIZE
    index_end = offset + index_size
    entries = []
    while offset < index_end:
        size = struct.unpack_from("<I", data, offset)[0]
        offset += 4
        flag = data[offset]
        offset += 1
        end = data.index(b"\0", offset)
        entries.append((data[offset:end].decode("latin-1"), size, flag))
        offset = end + 1

    # Bodies are concatenated in index order; offsets are implicit.
    index, cursor = {}, index_end
    for name, size, flag in entries:
        index[name] = (cursor, size, flag)
        cursor += size

    meta = {
        "file_count": file_count,
        "index_entries": len(entries),
        "index_size": index_size,
        "data_start": index_end,
        "total_size": len(data),
        "bytes_accounted": cursor,
    }
    return data, index, meta


# --------------------------------------------------------------------------
# Writing
# --------------------------------------------------------------------------

PFH_TYPE_BOOT = 0
PFH_TYPE_RELEASE = 1
PFH_TYPE_PATCH = 2
PFH_TYPE_MOD = 3
PFH_TYPE_MOVIE = 4


def write_pack(path, files, pack_type=PFH_TYPE_MOD, timestamp=None):
    """Write a PFH5 PackFile.

    `files` maps an in-pack path to its bytes. Paths use backslashes, matching
    how the game stores them (e.g. "script\\campaign\\main_troy\\mod\\x.lua").

    `pack_type` must be PFH_TYPE_MOD for anything the in-game Mod Manager is
    meant to list; a Release-typed pack loads only if the game itself ships it.

    The layout mirrors read_pack(): 28-byte header, then the index, then every
    body concatenated in index order. Because offsets are implicit, index order
    and body order MUST agree — this writes both from the same iteration.
    """
    if timestamp is None:
        timestamp = int(time.time())

    index = bytearray()
    bodies = bytearray()
    for name, content in files.items():
        if isinstance(content, str):
            content = content.encode("utf-8")
        index += struct.pack("<I", len(content))
        index += b"\x00"                       # flag byte, 0 in vanilla packs
        index += name.encode("latin-1") + b"\x00"
        bodies += content

    header = MAGIC + struct.pack(
        "<IIIIII",
        pack_type,      # bitmask / pack type
        0,              # dependency count
        0,              # dependency block size
        len(files),     # file count
        len(index),     # index size
        timestamp,
    )
    with open(path, "wb") as fh:
        fh.write(header)
        fh.write(index)
        fh.write(bodies)
    return len(header) + len(index) + len(bodies)


def main(argv):
    if len(argv) < 2:
        print(__doc__.strip().splitlines()[2], file=sys.stderr)
        print("usage: packfile.py <pack> [regex]", file=sys.stderr)
        return 2

    data, index, meta = read_pack(argv[1])
    ok = "OK" if meta["bytes_accounted"] == meta["total_size"] else "MISMATCH"
    print(f"{meta['index_entries']} entries, {meta['total_size']} bytes ({ok})")

    pattern = re.compile(argv[2], re.I) if len(argv) > 2 else None
    for name in sorted(index):
        if pattern is None or pattern.search(name):
            _offset, size, flag = index[name]
            print(f"  {size:9d}  flag={flag}  {name}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
