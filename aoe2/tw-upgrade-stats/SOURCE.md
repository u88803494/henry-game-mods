# Source & License

## Where the numbers come from

The stat values in this mod (HP, attack, reload time, damage bonuses, etc.) are
extracted from **`845_Localization Fix and Enhanced Data Tooltip`** by
**irissakura**, a Simplified Chinese community mod for Age of Empires II: DE.
Its `info.json` describes itself as licensed under the GNU license, free for
personal use, **not for commercial use**.

This project does not redistribute that mod's source file — see
[`.env.example`](.env.example) for how to obtain it yourself.

數值資料來源：**`845_Localization Fix and Enhanced Data Tooltip`**（作者
**irissakura**），是一個簡體中文的社群模組。它的 `info.json` 自述採 GNU 授權、
僅供個人使用、**禁止商業用途**。

本 repo 不收錄該模組的原始檔案，取得方式見 [`.env.example`](.env.example)。

## What this project adds

845 has no Traditional Chinese (`tw/`) resources at all, so none of it takes
effect for Traditional Chinese clients. This project:

- Maps every Simplified Chinese term used by 845 to the **official**
  Traditional Chinese term — by cross-referencing the game's own
  `resources/zh/` and `resources/tw/` string files by matching string ID, and
  by reading `widgetui/stringreference.json`'s scene-editor attribute names —
  never a character-level conversion tool (e.g. no OpenCC)
- Fixes one upstream data bug (`508000` had a duplicated clause in 845's
  source text)
- Verifies every output line: numeric tokens match the source exactly, no
  Simplified character survives, every line starts with the exact official
  Traditional Chinese string

845 完全沒有 `tw/` 資源，對繁中客戶端一個字都不會生效。本專案做的事：

- 把 845 用的每個简中術語對應到**官方**繁中定名——透過遊戲自身
  `resources/zh/` 與 `resources/tw/` 字串檔的相同字串 ID 交叉比對，以及讀取
  `widgetui/stringreference.json` 的場景編輯器屬性名稱，**從不使用字元級的
  簡繁轉換工具**（例如 OpenCC）
- 修正一處上游資料錯誤（845 原始文字 `508000` 重複了一段子句）
- 驗證每一行輸出：數值 token 與來源完全一致、不殘留任何簡體字、每行開頭
  完整等於官方繁中原文

## License of this project's own code

The scripts in [`scripts/`](scripts/) are original work and released under
the MIT License (see repo root [`LICENSE`](../../LICENSE)). The **data**
(the actual translated strings) carries 845's non-commercial restriction,
since it's a derivative of 845's numbers.

`scripts/` 底下的程式碼是原創，採 MIT 授權（見根目錄 `LICENSE`）。**資料**
（實際的翻譯字串）因為衍生自 845 的數值，沿用其非商業限制。
