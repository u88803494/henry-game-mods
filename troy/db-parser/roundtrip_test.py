#!/usr/bin/env python3
"""Prove encode() is an exact mirror of decode() across every table in a pack.

    python3 roundtrip_test.py [pack] [--schema schema_troy.ron]

For each `db\\*_tables\\data__` entry: decode it, encode the result, and compare
against the original bytes. A table passes only on a byte-for-byte match.

Why this is the acceptance test
-------------------------------
There is no way to ask TROY "is this table valid?" short of launching it. But
if our encoder reproduces the shipped bytes exactly, for every table, then by
construction the game can read what we write — the output is indistinguishable
from what it already loads. That makes this the gate a mod build has to clear
before anything reaches the game.

Exit code is 0 only when every decodable table round-trips exactly.
"""

import argparse
import sys

from db import decode, encode, load_schema, read_header
from packfile import read_pack

DEFAULT_PACK = "/Users/Shared/Epic Games/TotalWarSagaTROY/TroyData/data/data_db.pack"


def table_entries(index):
    """Yield (table_name, pack_key) for every db table in the pack."""
    for key in sorted(index):
        parts = key.split("\\")
        if len(parts) == 3 and parts[0] == "db" and parts[2] == "data__":
            yield parts[1], key


def main():
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("pack", nargs="?", default=DEFAULT_PACK)
    parser.add_argument("--schema", default="schema_troy.ron")
    parser.add_argument("--verbose", action="store_true", help="list every table")
    args = parser.parse_args()

    data, index, _ = read_pack(args.pack)
    schema = load_schema(args.schema)

    exact, mismatched, undecodable = [], [], []

    for name, key in table_entries(index):
        offset, size, _flag = index[key]
        blob = data[offset:offset + size]
        versions = schema.get(name)
        if not versions:
            undecodable.append((name, "no schema entry"))
            continue
        try:
            header, _start = read_header(blob)
            _version, fields, rows, used = decode(blob, versions, name)
            if used != len(blob):
                undecodable.append((name, f"decoded {used}/{len(blob)}"))
                continue
        except Exception as exc:
            undecodable.append((name, f"{type(exc).__name__}: {exc}"))
            continue

        rebuilt = encode(rows, fields, header)
        if rebuilt == blob:
            exact.append(name)
            if args.verbose:
                print(f"  ok       {name} ({len(rows)} rows)")
        else:
            detail = f"{len(rebuilt)} vs {len(blob)} bytes"
            if len(rebuilt) == len(blob):
                first = next(i for i, (a, b) in enumerate(zip(rebuilt, blob)) if a != b)
                detail = f"same length, first difference at byte {first}"
            mismatched.append((name, detail))
            print(f"  MISMATCH {name}: {detail}")

    total = len(exact) + len(mismatched) + len(undecodable)
    print()
    print(f"byte-exact round trip : {len(exact)}/{total}")
    print(f"mismatched            : {len(mismatched)}")
    print(f"not decodable         : {len(undecodable)}")

    for name, why in undecodable:
        print(f"  - {name}: {why}")

    return 0 if not mismatched else 1


if __name__ == "__main__":
    sys.exit(main())
