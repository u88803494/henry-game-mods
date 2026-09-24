# hecatomb_reminder

Reminds you when a **hecatomb or prayer is available but unused** — the thing
that's easy to forget because nothing in the game nags you about it.

## How it decides "available"

The game already works this out. In the gods panel, the action button sits in
state `"active"` exactly when the action can be afforded and isn't on cooldown:

```lua
find_uicomponent(core:get_ui_root(),
    "gods_and_favor", "container_hecatomb_prayer", "hecatomb_holder", "action_button")
    :CurrentState() == "active"
```

Reading that state instead of recomputing costs means the mod can never
disagree with the game. (Path confirmed against `troy_constants.lua`, where the
tutorial uses the same one.)

When the gods panel is closed the button doesn't exist, so it falls back to
"how many turns since the last hecatomb", tracked via `FactionInitiatesHecatomb`
and `cm:set_saved_value`.

## What it does

| Event | Action |
|---|---|
| `FactionTurnStart` | Check and log; also logs every god's favour and tier |
| `FactionAboutToEndTurn` | Same check, plus **pulses the button** — same moment the game's own end-turn warnings fire |
| `FactionInitiatesHecatomb` | Resets the counter, stops the pulse |

`FactionAboutToEndTurn` is unused by all 247 vanilla Lua files, so nothing
collides with it.

## Build and install

```bash
python3 build.py          # -> hecatomb_reminder.pack, verified by reading it back
cp hecatomb_reminder.pack ~/Library/Application\ Support/Feral\ Interactive/Troy/VFS/Local/mods/
```

Then enable it in the Mod Manager on the game's main menu.

The pack must be `PFH_TYPE_MOD` (3) or the Mod Manager won't list it, and the
Lua must sit at `script/campaign/main_troy/mod/<name>.lua` with a function of
the same name — that's the contract `lib_mod_loader.lua` documents.

## Debugging

Everything goes through `ModLog()` plus `out()`, prefixed `[hecatomb_reminder]`.
`ModLog` writes to `lua_mod_log.txt`; script errors land in the logs directory:

```
~/Library/Application Support/Feral Interactive/Troy/VFS/User/AppData/Roaming/The Creative Assembly/Troy/logs/
```

If the mod seems dead, check that the log has the `loaded` line — that tells
you whether the mod loader found it at all, which separates "pack is wrong"
from "script is wrong".

## Status

**Written from the API surface, not yet run in-game.** Every function used was
verified to exist in the shipped Lua (`lib_campaign_manager.lua`,
`lib_common.lua`, `events.lua`), but the load path and the UI component lookup
still need one real campaign turn to confirm.

Things to check on first run:

- Does `[hecatomb_reminder] loaded` appear in the log?
- With the gods panel **open**, does ending the turn pulse the button?
- With it closed, does the turn-count fallback fire after 5 turns?

## Tuning

- `REMIND_AFTER_TURNS` — how long before the closed-panel fallback complains
- `ACTIONS` — drop `prayer` if you only care about hecatombs
