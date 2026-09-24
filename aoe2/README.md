# Age of Empires II: Definitive Edition

## Mods

- [`tw-upgrade-stats/`](tw-upgrade-stats/) — adds real numbers to the
  official Traditional Chinese client's upgrade buttons and unit cards.
  為官方繁體中文版的升級按鈕與單位卡補上實際數值。
- [`tw-civ-emblems/`](tw-civ-emblems/) — overlays a Traditional Chinese
  abbreviation on each civilization's emblem badge (scoreboard & tech
  tree). 在每個文明的徽章上疊繁體中文縮寫（計分板與科技樹畫面）。

## Installing

Each mod's own README has full details, but in general: local mods for this
game live in a per-account folder scanned only at game startup:

```
~/Library/Application Support/Feral Interactive/Age Of Empires II/VFS/User/
  Games/Age of Empires 2 DE/<your SteamID64>/mods/local/
```

Drop a mod's folder in there, restart the game once, then enable it from
the in-game Mods screen. **Only hand-edit `mod-status.json`** in that same
directory while the game process is fully closed — confirmed with
`pgrep -fl "AoE2DE|Age of Empires"` first. Edits made while the game is
running get silently overwritten on exit; edits made while it's closed
persist correctly, and survive even a full Steam reinstall of the game
binaries (`mod-status.json` and `mods/local/` live in a separate Feral
VFS user-data directory that reinstalling the Steam app doesn't touch).
Always back the file up before editing it.

每個模組自己的 README 有完整細節，但一般來說：這款遊戲的本機模組放在依帳號
區分的資料夾，**只在遊戲啟動時掃描一次**（見上方路徑）。把模組資料夾丟進去、
重開一次遊戲、在遊戲內的 Mods 畫面勾選即可。**只在遊戲完全關閉時手動編輯**
同目錄下的 `mod-status.json`——先用 `pgrep -fl "AoE2DE|Age of Empires"`
確認行程不存在。遊戲執行中編輯會在結束時被默默覆寫；關閉狀態下編輯的內容
會正確保留，就算重灌 Steam 上的遊戲本體也不受影響（`mod-status.json` 跟
`mods/local/` 放在另一個獨立的 Feral VFS 使用者資料目錄，重灌遊戲不會動到
那裡）。動手前一定先備份這個檔案。

## Mod priority convention

`Priority` in `mod-status.json` is a single unique 1-N integer shared
across every mod (enabled and disabled together) — the game uses it as
load order, and when two mods touch the same resource file, the higher
number wins.

`mod-status.json` 裡的 `Priority` 是所有模組（不管啟用還是停用）共用同一組
不重複的 1-N 整數——遊戲用它決定載入順序，兩個模組動到同一份資源檔時，
數字大的蓋過數字小的。

Only the enabled block is kept meaningfully ordered, as consecutive
integers starting at 1. Disabled mods just need unique numbers — they're
appended after the enabled block in whatever relative order they were
already in, never hand-curated.

只有「啟用中」的那段會維持有意義的排序，從 1 開始連續編號。停用的模組只需要
數字不重複，接在啟用清單後面、維持它們原本的相對順序，不特地整理。

Enabled mods are grouped into five categories, in this fixed relative
order — a mod that changes core game rules (e.g. `KJ - 1000 population`)
belongs to none of them and is never enabled, full stop:

啟用中的模組分五類，固定照這個相對順序排——會改動遊戲規則本身的模組（例如
`KJ - 1000 population`）不屬於以下任何一類，原則是絕對不啟用：

1. **識別／指示類 (identification aids)** — labels, pointers, indicators
   that help you recognize something faster during a match.
   幫你在對戰中更快認出東西是什麼的標籤、指標、提示。
2. **視覺／特效類 (visual / cosmetic)** — makes the screen clearer or nicer
   without changing what information is shown.
   讓畫面更清楚或好看，不改變顯示的資訊本身。
3. **音效類 (audio)**
4. **內容／劇本類 (content / campaigns)** — custom scenarios.
   自製戰役。
5. **文字翻譯類 (text / localization)**

When adding a new mod: place it immediately after the last existing
member of its category — never append it to the very end of the whole
list. This is purely for the list to stay navigable as it grows; the game
itself doesn't care.

加入新模組時：插進它所屬分類裡「現有清單中最後一個」的鄰居後面——不要丟到
整份清單最後。這純粹是為了讓清單在變大之後還讀得懂，遊戲本身不在乎這個。

Current enabled set, by category (Priority order within each):

目前啟用中的模組，依分類列出（各分類內照 Priority 排序）：

| 分類 Category | 模組 Mods |
|---|---|
| 識別／指示類 | Building Foundation Label、Bigger and Eye-catching Relic、Monk Pointer、New Fish Border、Standard AI Recognition、**TW-Civ-Emblems**、Age Passage Reminder、Improved Tech Tree UI Mod |
| 視覺／特效類 | 2020 Spring - Lush Terrains、Improved Mangonel Shot Visibility、Transparent White Monk Conversions FX、Binary Code Research FX、[PYRO] 2020 Spring Color Palette、Huge Number |
| 音效類 | T90 - No Defeat Sound |
| 內容／劇本類 | 1310_Three Kingdoms Cao Caos Ambition |
| 文字翻譯類 | **TW-Upgrade-Stats** |

Mods bolded above live in this repo. A prior write-up of how this scheme
came together lives in the henry-atlas archive, as a point-in-time
snapshot rather than a maintained doc:
[`raw/2026-09-17-世紀帝國模組排序方式.md`](../../henry-atlas/raw/2026-09-17-世紀帝國模組排序方式.md).

上面粗體的模組在這個 repo 裡。這套分類是怎麼定出來的完整過程記在
henry-atlas 的 raw（當時的想法快照，不是持續更新的文件）：
[`raw/2026-09-17-世紀帝國模組排序方式.md`](../../henry-atlas/raw/2026-09-17-世紀帝國模組排序方式.md)。
