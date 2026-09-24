# Source & License

## Where the art comes from

The base emblem art (104×104 PNG per civilization, text-free) is copied
**unmodified** from the official *Age of Empires II: Definitive Edition*
game install —
`AgeOfEmpires2Data/widgetui/textures/menu/civs/*.png` — which ships with
every legitimate copy of the game. Nothing here is redrawn or traced.

基礎徽章素材（每個文明一張 104×104、沒有燒字的 PNG）**原封不動**取自
《世紀帝國二：決定版》官方遊戲安裝目錄——
`AgeOfEmpires2Data/widgetui/textures/menu/civs/*.png`——每一份合法遊戲安裝
都有這批檔案，這裡沒有重繪或描圖。

## What role the Steam Workshop mod played

The Steam Workshop mod **"Better Civ Emblems"** (workshop id `3259`, by
`Xyrr6134`) was consulted only to discover that this same texture path is
reused across multiple UI screens (scoreboard **and** the tech-tree
screen) and to confirm the 104×104 size convention. **No code, text, or
image data was copied from that mod** — its own badges have English
letters baked directly into the pixel art, which is exactly what made it
unusable as a base (see "A wrong turn" below).

Steam Workshop 模組 **"Better Civ Emblems"**（workshop id `3259`，作者
`Xyrr6134`）只在這件事上被參考過：發現同一份貼圖路徑被計分板**跟**科技樹畫面
共用，以及確認 104×104 的尺寸慣例。**沒有從那個模組複製任何程式碼、文字或
圖片資料**——它自己的徽章把英文字母直接燒進像素圖裡，這正是它不能拿來當
底圖的原因（見下方「一個繞遠路」）。

### A wrong turn: the mod's own art has English text baked in

The first attempt composited Traditional Chinese labels directly onto
Better Civ Emblems' own PNG files. It looked fine until the label was a
single narrow character (e.g. "庫" for Cumans) — the underlying "Cu" wasn't
fully covered, leaving a stray fragment of the English letter visible
behind the Chinese character. The fix was switching to the game's own
blank crest icons as the base instead, which have no text at all.

第一次嘗試是把繁中縮寫直接疊在 Better Civ Emblems 自己的 PNG 上。看起來還行，
直到縮寫是單一個比較窄的字（例如 Cumans 用「庫」）——底下的「Cu」沒有被完全
蓋住，中文字後面還看得到一小截英文字母的殘影。修法是改用遊戲自己那批完全
空白、沒有燒字的徽章當底圖。

## Font

Labels use **PingFang TC** (蘋方-繁), a macOS system font, at the
Semibold weight. It is **not bundled** with this mod — the build script
reads it directly from the OS
(`/System/Library/AssetsV2/.../PingFang.ttc`, font index 10). Running
`scripts/build.py` on a non-macOS machine will need a different
Traditional-Chinese-capable font substituted at that path.

縮寫文字使用 macOS 系統字型 **PingFang TC（蘋方-繁）**半粗體。這個字型**沒有
被打包**進這個 mod——build script 直接從作業系統讀取
（`/System/Library/AssetsV2/.../PingFang.ttc`，font index 10）。在非
macOS 機器上跑 `scripts/build.py`，需要換成別的繁體中文字型路徑。

## License of this project's own code

The script in [`scripts/build.py`](scripts/build.py) is original work,
released under the MIT License (see repo root [`LICENSE`](../../LICENSE)).
The composited badge PNGs in [`mod/`](mod/) build entirely from official
game assets plus this repo's own font compositing — no third-party mod
data is redistributed.

[`scripts/build.py`](scripts/build.py) 是原創程式碼，採 MIT 授權（見根目錄
[`LICENSE`](../../LICENSE)）。[`mod/`](mod/) 底下合成好的徽章 PNG，素材全部
來自官方遊戲資源，加上本 repo 自己的字型合成——沒有轉散布任何第三方模組的
資料。
