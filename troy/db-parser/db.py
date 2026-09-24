#!/usr/bin/env python3
"""Decode TROY's binary DB tables into plain Python dicts.

DB tables are where the game's *rules* live — unit stats, projectile values,
building chains, tech effects, mission definitions. (Save files, by contrast,
only hold the *state* of one campaign; see ../save-parser/.)

    python3 db.py <pack> <table> [--schema schema_troy.ron] [--limit N]
    python3 db.py data_db.pack missile_weapons
    python3 db.py data_db.pack projectiles --limit 5

The binary carries no field names or types, so a schema is required. Grab the
community-maintained one (note the hyphen — `rpfm_schemas` with an underscore
is a different, non-existent repo):

    curl -LO https://raw.githubusercontent.com/Frodo45127/rpfm-schemas/master/schema_troy.ron

Table layout
------------
    FD FE FC FF              GUID marker (optional)
    u16 + UTF-16 chars       GUID string
    FC FD FE FF              version marker (optional)
    i32                      table version -> picks the field list from schema
    u8                       one mystery byte, always 1 in vanilla
    i32                      record count
    records...               fields back to back, no padding or alignment

Strings are length-prefixed, not NUL-terminated: u16 length, then that many
bytes (UTF-8) or that many UTF-16 code units. `Optional*` strings put a single
0/1 byte in front — when it's 0 the string is absent entirely, not empty.

Verification
------------
`decode()` returns how many bytes it consumed alongside the rows. Because
records are packed with no slack, a correct decode lands *exactly* on the end
of the blob; anything else means the schema and the data disagree. Always
check it — a wrong field type silently shifts every subsequent value rather
than raising.
"""

import argparse
import re
import struct
import sys

from packfile import read_pack

GUID_MARKER = b"\xfd\xfe\xfc\xff"
VERSION_MARKER = b"\xfc\xfd\xfe\xff"


def load_schema(path):
    """Parse RPFM's .ron schema into {table_name: {version: [(field, type)]}}.

    Field order is the order they appear in the file, which is the
    serialisation order for every table verified so far.

    Do NOT sort by `ca_order`: that is the assembly-kit column order and does
    not match the binary layout. `projectiles_tables` proves it — its ca_order
    values run 0,1,2,3,5,...,16,4,17,... yet the file order decodes byte-exact.
    """
    tables, table, version, pending = {}, None, None, None
    re_table = re.compile(r'^\s{8}"([^"]+)":\s*\[')
    re_version = re.compile(r"^\s+version:\s*(-?\d+),")
    re_name = re.compile(r'^\s+name:\s*"([^"]*)",')
    re_type = re.compile(r"^\s+field_type:\s*(\w+),")

    for line in open(path, encoding="utf-8"):
        match = re_table.match(line)
        if match:
            table = match.group(1)
            tables.setdefault(table, {})
            version = None
            continue
        if table is None:
            continue
        match = re_version.match(line)
        if match:
            version = int(match.group(1))
            tables[table][version] = []
            continue
        match = re_name.match(line)
        if match:
            pending = match.group(1)
            continue
        match = re_type.match(line)
        if match and version is not None and pending is not None:
            tables[table][version].append((pending, match.group(1)))
            pending = None
    return tables


class Reader:
    """Little-endian cursor over a table blob."""

    def __init__(self, blob):
        self.blob, self.pos = blob, 0

    def _unpack(self, fmt, size):
        value = struct.unpack_from(fmt, self.blob, self.pos)[0]
        self.pos += size
        return value

    def u8(self):
        value = self.blob[self.pos]
        self.pos += 1
        return value

    def u16(self):
        return self._unpack("<H", 2)

    def i16(self):
        return self._unpack("<h", 2)

    def i32(self):
        return self._unpack("<i", 4)

    def i64(self):
        return self._unpack("<q", 8)

    def f32(self):
        return round(self._unpack("<f", 4), 4)

    def f64(self):
        return round(self._unpack("<d", 8), 4)

    def str_u8(self):
        length = self.u16()
        value = self.blob[self.pos:self.pos + length].decode("utf-8", "replace")
        self.pos += length
        return value

    def str_u16(self):
        length = self.u16()
        value = self.blob[self.pos:self.pos + length * 2].decode("utf-16-le", "replace")
        self.pos += length * 2
        return value


READERS = {
    "StringU8": lambda r: r.str_u8(),
    "OptionalStringU8": lambda r: r.str_u8() if r.u8() else "",
    "StringU16": lambda r: r.str_u16(),
    "OptionalStringU16": lambda r: r.str_u16() if r.u8() else "",
    "I16": lambda r: r.i16(),
    "I32": lambda r: r.i32(),
    "I64": lambda r: r.i64(),
    "F32": lambda r: r.f32(),
    "F64": lambda r: r.f64(),
    "Boolean": lambda r: bool(r.u8()),
    "ColourRGB": lambda r: r.i32(),
}


def decode(blob, versions, name=""):
    """Decode one table blob. Returns (version, fields, rows, bytes_consumed).

    If the declared version's field list doesn't consume the blob exactly, the
    trailing fields are dropped one at a time and the decode retried. Schemas
    are maintained against the newest patch, so a table can legitimately carry
    fewer columns than its version claims — `land_units_tables` v44 defines 63
    fields but this build stores only the first 61 (`onscreen_name` and
    `concealed_name` are absent). Only an exact byte match is accepted, so a
    shortened field list can't be mistaken for a correct one.
    """
    reader = Reader(blob)
    if blob[:4] == GUID_MARKER:
        reader.pos = 4
        reader.str_u16()
    version = None
    if blob[reader.pos:reader.pos + 4] == VERSION_MARKER:
        reader.pos += 4
        version = reader.i32()
    reader.u8()
    count = reader.i32()
    start = reader.pos

    fields = versions.get(version)
    if fields is None:
        raise KeyError(f"{name}: no schema for version {version} (have {sorted(versions)})")

    for width in range(len(fields), 0, -1):
        trimmed = fields[:width]
        reader.pos = start
        try:
            rows = [
                {fname: READERS[ftype](reader) for fname, ftype in trimmed}
                for _ in range(count)
            ]
        except (IndexError, struct.error, UnicodeDecodeError):
            continue
        if reader.pos == len(blob):
            return version, trimmed, rows, reader.pos

    raise ValueError(
        f"{name}: no field count from 1..{len(fields)} decodes version {version} exactly"
    )


def read_table(pack_path, table, schema_path):
    """Convenience wrapper: open a pack, decode one `<table>_tables` entry."""
    data, index, _ = read_pack(pack_path)
    key = f"db\\{table}_tables\\data__"
    if key not in index:
        raise KeyError(f"{key} not in pack")
    offset, size, _flag = index[key]
    blob = data[offset:offset + size]
    schema = load_schema(schema_path)
    version, fields, rows, used = decode(blob, schema[f"{table}_tables"], table)
    return version, fields, rows, used, len(blob)


def main():
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("pack")
    parser.add_argument("table", help="table name without the _tables suffix")
    parser.add_argument("--schema", default="schema_troy.ron")
    parser.add_argument("--limit", type=int, default=3)
    args = parser.parse_args()

    version, fields, rows, used, total = read_table(args.pack, args.table, args.schema)
    exact = used == total
    print(f"{args.table}: version={version} rows={len(rows)} fields={len(fields)}")
    print(f"decoded {used}/{total} bytes {'(exact)' if exact else '(MISMATCH — schema is wrong)'}")
    print("fields:", ", ".join(f"{n}:{t}" for n, t in fields))
    for row in rows[:args.limit]:
        print(" ", row)
    return 0 if exact else 1


if __name__ == "__main__":
    sys.exit(main())
