# less_bookkeeping

Less resource babysitting, same battles. Built from the **installed** game's own
tables, so it matches whatever patch and DLC are present.

## Why build instead of install

The most-endorsed Troy mods on Nexus were all published in **August 2020**, and
Total War db mods **replace whole tables**. A 2020 `main_units` table dropped on
a 1.4 + Mythos install overwrites every unit added since — giants, centaurs,
hydras, the entire Amazon roster. Reading the current tables and writing back
only the fields we touch avoids that class of failure entirely.

The second reason is fairness. 8 of Nexus's top 20 are "Player Only"; every
change here edits a table the whole game shares, so the AI pays the same rates.

## Changes

### A. Unit upkeep at 50% (default, always on)

Table: `resource_cost_pooled_resource_junctions_tables`

404 rows hold `*_upkeep` amounts (negative = expenditure), drawn from
`troy_food_units` and `troy_bronze_units`. All are scaled; no other row is
touched, and no row is added or removed.

Measured on a 20-unit Penthesilea horde (turn 44):

| | vanilla | modded | per turn |
|---|---|---|---|
| food upkeep | −2,325 | −1,165 | **+1,160** |
| bronze upkeep | −280 | −139 | **+141** |

Use `--upkeep 0.75` for a gentler version.

### B. Favour persistence (opt-in, **off by default**)

Table: `pooled_resources_tables`, flag `persistent_factors`

All nine `troy_god_attitude_*` pools ship with `persistent_factors: False`.
This is the closest thing in the data to the "god's favour degenerates"
behaviour that Nexus's most-endorsed mod (296 endorsements) removes.

**The flag's exact runtime behaviour was not confirmed.** What was ruled out
first: the strings `entropy`, `decay` and `degeneration` appear **nowhere** in
the db or in any of the 247 shipped Lua files; `troy_favour.lua` is purely
event-driven (battles, buildings, diplomacy) with no per-turn drain; and
`_kv_rules` and `campaign_variables` have no decay entry either. The pooled
resource flag is what remains, and it is a plausible mechanism — but it is
inference, not proof.

Enable with `--persistent-favour` if you want to try it. It applies to every
god and every faction.

## Build

```bash
python3 build.py                      # upkeep 50%
python3 build.py --upkeep 0.75
python3 build.py --persistent-favour
```

The build re-reads its own output and diffs it against the game's tables, so a
bad write fails at build time rather than in the game. The encoder underneath
is covered by `../../db-parser/roundtrip_test.py`, which reproduces **all 802
vanilla tables byte-for-byte** — the strongest available evidence that what we
write is indistinguishable from what the game already loads.

## Install

```bash
cp less_bookkeeping.pack \
  ~/Library/Application\ Support/Feral\ Interactive/Troy/VFS/Local/mods/
```

Then enable it in the Mod Manager on the game's main menu.

Install **one mod at a time and play three turns between each** — stacked mods
make it impossible to tell which one caused a problem.

## Verify in game

1. Load the turn-44 save; confirm the unit list is intact and mythological
   units still exist (this is the check that a table got clobbered)
2. Open the army panel and confirm upkeep is roughly half
3. Play three turns and confirm no crash

## Revert

In order of severity:

1. Untick it in the Mod Manager, restart the game
2. Move `less_bookkeeping.pack` out of the `mods/` folder
3. If a save is damaged, restore from
   `.../Troy/VFS/User/AppData/Roaming/The Creative Assembly/Troy/save_games_backup_before_mods/`

Change A only rewrites numbers in existing rows, so removing the pack restores
vanilla rates with no lingering state.

## What this deliberately does not do

- No player-only bonuses
- No edits to `main_units` / `land_units` (large tables, high risk, low payoff)
- No combat stat changes — the goal is less admin, not an easier fight
