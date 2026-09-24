#!/usr/bin/env python3
"""Build less_bookkeeping.pack — less resource babysitting, same battles.

    python3 build.py                      # upkeep at 50%
    python3 build.py --upkeep 0.75        # gentler
    python3 build.py --persistent-favour  # also try the favour change (see below)

Every table is read out of the *installed* game, modified in memory, and written
back. Nothing is copied from another mod, so the output always matches whatever
patch and DLC the game currently has — which is the whole reason for building
our own instead of installing a pack authored in 2020 against an older table
layout.

Changes
-------
A. Unit upkeep scaled (default 0.5), in
   `resource_cost_pooled_resource_junctions_tables`.

   408 rows carry `*_upkeep` costs, all negative (negative = expenditure),
   drawn from `troy_food_units` and `troy_bronze_units`. Those are exactly the
   two resources that run dry in a horde campaign. Halving them applies to
   every faction — the table is global, the AI pays the same rates.

B. (opt-in, off by default) Favour persistence, in `pooled_resources_tables`.

   All nine `troy_god_attitude_*` pools ship with `persistent_factors: False`,
   which is the closest thing in the data to the "favour degenerates" behaviour
   that the most-endorsed Nexus mod removes. Flipping it to True is a one-field
   change and is applied to every god for every faction. It is NOT enabled by
   default because the exact runtime meaning of the flag was not confirmed —
   see README before turning it on.

Verification
------------
The build re-reads its own pack and re-decodes the tables, so a corrupt write
fails here rather than in the game. The encoder itself is covered by
../../db-parser/roundtrip_test.py, which reproduces all 802 vanilla tables
byte-for-byte.
"""

import argparse
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "..", "db-parser"))

from db import encode, read_table_full  # noqa: E402
from packfile import PFH_TYPE_MOD, read_pack, write_pack  # noqa: E402

GAME_DB = "/Users/Shared/Epic Games/TotalWarSagaTROY/TroyData/data/data_db.pack"
SCHEMA = os.path.join(HERE, "..", "..", "db-parser", "schema_troy.ron")

UPKEEP_TABLE = "resource_cost_pooled_resource_junctions"
POOLS_TABLE = "pooled_resources"
GOD_POOL_PREFIX = "troy_god_attitude_"


def pack_path(table):
    return f"db\\{table}_tables\\data__"


def scale_upkeep(rows, factor):
    """Scale every `*_upkeep` amount. Returns (new_rows, changed_count)."""
    out, changed = [], 0
    for row in rows:
        row = dict(row)
        if "upkeep" in str(row["resource_cost"]) and row["amount"]:
            row["amount"] = int(round(row["amount"] * factor))
            changed += 1
        out.append(row)
    return out, changed


def make_favour_persistent(rows):
    """Set persistent_factors on the nine god attitude pools."""
    out, changed = [], 0
    for row in rows:
        row = dict(row)
        if str(row["key"]).startswith(GOD_POOL_PREFIX) and not row["persistent_factors"]:
            row["persistent_factors"] = True
            changed += 1
        out.append(row)
    return out, changed


def build(upkeep_factor, persistent_favour, out_path):
    files = {}
    summary = []

    header, fields, rows = read_table_full(GAME_DB, UPKEEP_TABLE, SCHEMA)
    new_rows, changed = scale_upkeep(rows, upkeep_factor)
    files[pack_path(UPKEEP_TABLE)] = encode(new_rows, fields, header)
    summary.append(f"{UPKEEP_TABLE}: {changed} upkeep amounts x{upkeep_factor}")

    if persistent_favour:
        header, fields, rows = read_table_full(GAME_DB, POOLS_TABLE, SCHEMA)
        new_rows, changed = make_favour_persistent(rows)
        files[pack_path(POOLS_TABLE)] = encode(new_rows, fields, header)
        summary.append(f"{POOLS_TABLE}: {changed} god pools set persistent")

    write_pack(out_path, files, pack_type=PFH_TYPE_MOD)
    return summary


def verify(out_path, upkeep_factor, persistent_favour):
    """Re-read the pack we just wrote and confirm the intended deltas."""
    data, index, meta = read_pack(out_path)
    assert meta["bytes_accounted"] == meta["total_size"], "pack index/body mismatch"

    vanilla = {}
    for table in ([UPKEEP_TABLE] + ([POOLS_TABLE] if persistent_favour else [])):
        _h, _f, rows = read_table_full(GAME_DB, table, SCHEMA)
        vanilla[table] = rows
        assert pack_path(table) in index, f"{table} missing from pack"

    ok = True

    _h, _f, modded = read_table_full(out_path, UPKEEP_TABLE, SCHEMA)
    base = vanilla[UPKEEP_TABLE]
    assert len(modded) == len(base), "row count changed"
    touched = untouched = 0
    for before, after in zip(base, modded):
        is_upkeep = "upkeep" in str(before["resource_cost"]) and before["amount"]
        if is_upkeep:
            expected = int(round(before["amount"] * upkeep_factor))
            if after["amount"] != expected:
                print(f"  BAD {before['resource_cost']}: {after['amount']} != {expected}")
                ok = False
            touched += 1
        else:
            if after != before:
                print(f"  BAD untouched row changed: {before['resource_cost']}")
                ok = False
            untouched += 1
    print(f"  {UPKEEP_TABLE}: {touched} scaled, {untouched} untouched")

    if persistent_favour:
        _h, _f, modded = read_table_full(out_path, POOLS_TABLE, SCHEMA)
        for before, after in zip(vanilla[POOLS_TABLE], modded):
            if str(before["key"]).startswith(GOD_POOL_PREFIX):
                if after["persistent_factors"] is not True:
                    print(f"  BAD {before['key']} not persistent")
                    ok = False
            elif after != before:
                print(f"  BAD untouched pool changed: {before['key']}")
                ok = False
        print(f"  {POOLS_TABLE}: nine god pools set persistent, rest untouched")

    return ok


def main():
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--upkeep", type=float, default=0.5,
                        help="multiplier for unit upkeep (default 0.5)")
    parser.add_argument("--persistent-favour", action="store_true",
                        help="also set persistent_factors on god pools (unverified, see README)")
    parser.add_argument("--out", default=os.path.join(HERE, "less_bookkeeping.pack"))
    args = parser.parse_args()

    summary = build(args.upkeep, args.persistent_favour, args.out)
    print(args.out)
    for line in summary:
        print("  " + line)
    print("verifying:")
    ok = verify(args.out, args.upkeep, args.persistent_favour)
    print("verified:", "yes" if ok else "NO")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
