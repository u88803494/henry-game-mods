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
        # No rounding: round(x, 4) is lossy and would stop encode() from
        # reproducing the original bytes. Round at the point of display.
        return self._unpack("<f", 4)

    def f64(self):
        return self._unpack("<d", 8)

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


class Writer:
    """Little-endian byte builder — the mirror of Reader."""

    def __init__(self):
        self.parts = []

    def u8(self, value):
        self.parts.append(bytes((value & 0xFF,)))

    def u16(self, value):
        self.parts.append(struct.pack("<H", value))

    def i16(self, value):
        self.parts.append(struct.pack("<h", value))

    def i32(self, value):
        self.parts.append(struct.pack("<i", value))

    def i64(self, value):
        self.parts.append(struct.pack("<q", value))

    def f32(self, value):
        self.parts.append(struct.pack("<f", value))

    def f64(self, value):
        self.parts.append(struct.pack("<d", value))

    def str_u8(self, value):
        raw = value.encode("utf-8")
        self.u16(len(raw))
        self.parts.append(raw)

    def str_u16(self, value):
        raw = value.encode("utf-16-le")
        self.u16(len(raw) // 2)
        self.parts.append(raw)

    def optional_str_u8(self, value):
        # Vanilla never stores a present-but-empty optional string (verified
        # across all 802 tables: 106,644 present, 181,062 absent, 0 empty), so
        # "" unambiguously means absent and the round trip stays exact.
        if value:
            self.u8(1)
            self.str_u8(value)
        else:
            self.u8(0)

    def optional_str_u16(self, value):
        if value:
            self.u8(1)
            self.str_u16(value)
        else:
            self.u8(0)

    def getvalue(self):
        return b"".join(self.parts)


WRITERS = {
    "StringU8": lambda w, v: w.str_u8(v),
    "OptionalStringU8": lambda w, v: w.optional_str_u8(v),
    "StringU16": lambda w, v: w.str_u16(v),
    "OptionalStringU16": lambda w, v: w.optional_str_u16(v),
    "I16": lambda w, v: w.i16(v),
    "I32": lambda w, v: w.i32(v),
    "I64": lambda w, v: w.i64(v),
    "F32": lambda w, v: w.f32(v),
    "F64": lambda w, v: w.f64(v),
    "Boolean": lambda w, v: w.u8(1 if v else 0),
    "ColourRGB": lambda w, v: w.i32(v),
}


def encode(rows, fields, header=None):
    """Serialise rows back into a table blob — the mirror of decode().

    `header` is the dict from read_header(); pass the one you decoded so the
    GUID, version marker and record count are reproduced exactly. Omit it and
    you get a bare table with no GUID and no version marker, which the game
    will reject for any table that normally has them.

    Round-tripping vanilla (decode -> encode) reproduces the original bytes
    exactly; `roundtrip_test.py` asserts this across every table in the pack.
    """
    header = header or {}
    writer = Writer()

    guid = header.get("guid")
    if guid is not None:
        writer.parts.append(GUID_MARKER)
        writer.str_u16(guid)

    version = header.get("version")
    if version is not None:
        writer.parts.append(VERSION_MARKER)
        writer.i32(version)

    writer.u8(header.get("mystery", 1))
    writer.i32(len(rows))

    for row in rows:
        for fname, ftype in fields:
            WRITERS[ftype](writer, row[fname])
    return writer.getvalue()


def read_header(blob):
    """Split a table blob into its header and the offset where records start.

    Returns (header, body_offset). `header` carries everything encode() needs
    to rebuild the prologue byte-for-byte:

        guid     GUID string, or None when the blob has no GUID marker
        version  table version, or None when there is no version marker —
                 tables predating the marker must NOT get one bolted on
        mystery  the single byte after the version (always 1 in vanilla)
        count    record count
    """
    reader = Reader(blob)
    guid = None
    if blob[:4] == GUID_MARKER:
        reader.pos = 4
        guid = reader.str_u16()
    version = None
    if blob[reader.pos:reader.pos + 4] == VERSION_MARKER:
        reader.pos += 4
        version = reader.i32()
    mystery = reader.u8()
    count = reader.i32()
    return {"guid": guid, "version": version, "mystery": mystery, "count": count}, reader.pos


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
    header, start = read_header(blob)
    version, count = header["version"], header["count"]
    reader = Reader(blob)

    # Tables predating the version marker carry no version at all; their schema
    # is filed under 0. `version` stays None so encode() knows not to write a
    # marker back, but the lookup uses 0.
    fields = versions.get(0 if version is None else version)
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


def read_table_full(pack_path, table, schema_path):
    """Like read_table(), but also returns the header needed to re-encode.

    Returns (header, fields, rows). Feed header straight back into encode().
    """
    data, index, _ = read_pack(pack_path)
    key = f"db\\{table}_tables\\data__"
    if key not in index:
        raise KeyError(f"{key} not in pack")
    offset, size, _flag = index[key]
    blob = data[offset:offset + size]
    schema = load_schema(schema_path)
    header, _start = read_header(blob)
    _version, fields, rows, used = decode(blob, schema[f"{table}_tables"], table)
    if used != len(blob):
        raise ValueError(f"{table}: decode consumed {used}/{len(blob)} bytes")
    return header, fields, rows


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
        print(" ", {k: (round(v, 4) if isinstance(v, float) else v) for k, v in row.items()})
    return 0 if exact else 1


if __name__ == "__main__":
    sys.exit(main())
