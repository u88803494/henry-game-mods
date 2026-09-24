# TW Civ Emblems

A mod for *Age of Empires II: Definitive Edition* that overlays a 1-2
character Traditional Chinese abbreviation on every civilization's emblem
badge — the small icon shown next to each player on the scoreboard, and
on the civilization icons in the tech-tree screen.

一個《世紀帝國二：決定版》的模組，把 1-2 個字的繁體中文縮寫疊在每個文明的
徽章上——計分板上每個玩家旁邊的小圖示，還有科技樹畫面的文明圖示，兩個地方
共用同一批貼圖，所以會一起生效。

## The Problem

The official client shows a bare crest with no text — no quick way to tell
which civilization an opponent is playing without hovering or reading the
sidebar. English-labeled community mods exist, but a 3-letter Latin
abbreviation isn't faster to read than the crest itself for a Traditional
Chinese speaker.

官方版本的徽章完全沒有文字——不滑鼠移過去或看側欄，很難一眼認出對手在玩
哪個文明。社群裡有英文縮寫版的模組，但對慣用繁體中文的人來說，三個字母的
英文縮寫並不會比看徽章本身更快。

## What It Does

55 civilizations, each badge overlaid with a common, recognizable
Traditional Chinese character (or two, when disambiguation requires it) —
see [`docs/civ-abbreviation-table.md`](docs/civ-abbreviation-table.md) for
the full table and the disambiguation rule.

55 個文明，每個徽章疊上一個常見、一眼就懂的繁體中文字（需要消歧義時延伸成
兩個字）——完整對照表與消歧義規則見
[`docs/civ-abbreviation-table.md`](docs/civ-abbreviation-table.md)。

## Engineering Notes

### Text opacity was picked by measuring, not by looking at a big preview

Semi-transparent text looks more refined blown up on a desktop preview,
but the in-game badge renders at roughly 28px — far smaller. Several
opacity levels were downscaled to that real size and inspected before
picking 80%: below 70%, labels — especially the 2-character ones — blur
into the badge artwork and stop being readable at a glance, which defeats
the mod's entire purpose.

半透明的文字在桌面大圖預覽上看起來比較精緻，但遊戲裡的徽章實際顯示大小只有
28px 左右——小得多。定案前把幾個透明度縮到那個實際尺寸比對過：70% 以下，
標籤（尤其兩個字的）會糊進徽章底圖，瞄一眼根本認不出來，整個 mod 的目的就
沒了。

### The base art can't come from another emblem mod

The obvious shortcut — compositing Chinese text onto an existing
English-labeled emblem mod's PNGs — fails silently for narrow single
characters: the Chinese glyph doesn't always fully cover the English
letters baked into the source art, leaving a stray fragment visible behind
it. The fix was sourcing blank (text-free) crest art directly from the
game's own install instead. Full story in [`SOURCE.md`](SOURCE.md).

看起來最省事的做法——把中文字疊在既有英文版徽章模組的 PNG 上——會在單一個
比較窄的字上悄悄出包：中文字不一定能完全蓋住底圖裡燒進去的英文字母，後面
會露出一小截殘影。修法是改成直接從遊戲自己的安裝目錄拿完全空白、沒有燒字
的底圖。完整經過見 [`SOURCE.md`](SOURCE.md)。

## Conflicts with

If the Steam Workshop mod **"Better Civ Emblems"** is also subscribed and
enabled, both mods touch the exact same texture paths — whichever has the
higher `Priority` number in `mod-status.json` wins. Disable "Better Civ
Emblems", or make sure this mod's `Priority` is set higher, to avoid the
English-labeled version silently winning after a mod list change (e.g. a
game reinstall can re-enable previously-subscribed mods).

如果 Steam Workshop 的 **"Better Civ Emblems"** 也同時訂閱且啟用，兩個模組
會動到完全相同的貼圖路徑——`mod-status.json` 裡 `Priority` 數字大的那個蓋過
另一個。要嘛停用 "Better Civ Emblems"，要嘛確保這個模組的 `Priority` 排得
更高，不然模組清單一有變動（例如重灌遊戲可能重新啟用先前訂閱過的模組），
英文版就會悄悄蓋回來。

## Source & License

See [`SOURCE.md`](SOURCE.md) — base art is official game assets, no
third-party mod data is redistributed; the script here is MIT-licensed.

見 [`SOURCE.md`](SOURCE.md)——底圖是官方遊戲素材，沒有轉散布任何第三方模組
的資料；這裡的程式碼採 MIT 授權。

## Reproducing

```bash
pip install Pillow
python3 scripts/build.py
```

Requires a local *Age of Empires II: Definitive Edition* Steam install
(reads base art from there) and macOS (reads the PingFang TC system font —
see [`SOURCE.md`](SOURCE.md) for what to substitute on other platforms).
Output lands in `mod/widgetui/textures/menu/civs/` — drop the `mod/`
folder into your `mods/local/` directory and enable it from the in-game
Mods screen.

需要本機安裝《世紀帝國二：決定版》Steam 版（從那裡讀底圖）與 macOS（讀
PingFang TC 系統字型——其他平台要換字型路徑見 [`SOURCE.md`](SOURCE.md)）。
輸出會寫到 `mod/widgetui/textures/menu/civs/`——把 `mod/` 資料夾丟進你的
`mods/local/` 目錄，在遊戲內的 Mods 畫面勾選即可。
