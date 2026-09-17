# TW Upgrade Stats

A mod for *Age of Empires II: Definitive Edition* that adds real numbers to
the official Traditional Chinese client — 579 upgrade buttons, tech
descriptions, and unit cards that previously showed a name and nothing else.

一個《世紀帝國二：決定版》的模組，把數值補進官方繁體中文版——579 條升級按鈕、
科技說明、單位卡，原本只顯示名稱，一個數字都沒有。

## The Problem

Upgrade buttons in the official Traditional Chinese client only show a unit
name, never what the upgrade changes. "Upgrade to Cavalier" tells you
nothing about the stats behind it — no idea if it's worth the 300 gold.

官方繁中版的升級按鈕只顯示單位名稱，完全不說升級後會變怎樣。「升級到裝甲
衝撞車」一個字都不提背後的數值，看不出值不值得點下去。

## What It Does

```
升級到裝甲衝撞車
(生命值 +25, 攻擊力 +1, 近戰護甲 +1/遠程護甲 +10, 駐紮容量 +1,
 爆炸寬度 +1.5, 對建築傷害(攻城) +10, 對攻城武器傷害 +10, 衝撞車護甲 +1)
```

That's a real output line — the game's own official phrasing, followed by
the actual numbers. 579 lines total, split across four categories:

這是一條真實輸出——遊戲官方原本的說法，接上實際數值。共 579 條，分四類：

| | Count 條數 | |
|---|---|---|
| Upgrade button short strings 升級按鈕短字串 | 140 | Shown in the tech tree / build menu |
| Upgrade tooltip cards 升級提示卡 | 140 | What actually renders in the hover tooltip |
| Unit/building cards 單位／建築卡 | 294 | Training time, movement speed, damage bonuses |
| Manually written 人工補充 | 5 | Cards with no stat-icon line to anchor on |

## Engineering Notes

The interesting part of this project isn't the mod itself — it's the data
problem underneath it.

這個專案有趣的地方不在模組本身，而在底下那個資料問題。

### No character-level conversion

The numbers come from a Simplified Chinese community mod
([see `SOURCE.md`](SOURCE.md)). The naive approach — running its text
through OpenCC — produces "Traditional characters writing Simplified
terminology," which reads worse than having no translation at all. Instead,
every term is mapped through the game's **own** official data: matching
string IDs across `resources/zh/` and `resources/tw/` string files, and the
scene editor's attribute name table (`widgetui/stringreference.json`). The
result is a 7,326-entry name table with a traceable source for every entry —
zero characters translated by guesswork.

數值來自一個簡體中文的社群模組（見 `SOURCE.md`）。直覺的做法是丟進 OpenCC
轉換，但那樣產出的是「繁體字寫的简中術語」，比完全沒翻譯更糟。這裡改成把每
個術語對應到遊戲**自己**的官方資料：比對 `resources/zh/` 與 `resources/tw/`
字串檔的相同字串 ID，加上場景編輯器的屬性名稱表
（`widgetui/stringreference.json`）。結果是一份 7,326 筆的名稱對照表，每一
筆都能追出處——沒有一個字是憑感覺翻的。

### The official data disagrees with itself

While building that name table, I found the official Traditional Chinese
client isn't internally consistent. String ID `5160` — the unit's actual
name, shown in the tech tree — is "火艨艟" (Huo Meng Chong). String ID
`26160` — the unit's own tooltip card — calls it "火攻箭船" instead. Both
IDs exist in the same official language file. The fix: always source names
from the `5xxx` unit-name series, never from the descriptive card text.

建這份名稱表時，發現官方繁中版本自己就不一致：字串 ID `5160`——單位真正的
名稱，科技樹顯示的就是這個——叫「火艨艟」；字串 ID `26160`——同一個單位自己
的說明卡——卻叫「火攻箭船」。兩個 ID 都在同一份官方語言檔裡。修法：名稱一律
取 `5xxx` 系列的單位名稱，不取說明卡的描述文字。

### A wrong turn, caught by the person actually using it

Early on, I translated string ID `8xxx` — a short string that exists in the
game's data but isn't what the upgrade tooltip actually renders. The tooltip
reads from `28xxx` instead. The mod validated cleanly and installed without
error; it simply changed a string nobody would ever see. It only surfaced
because the person testing it — not me — kept reporting "I don't see any
change," across three separate reinstalls, until a screenshot made the
mismatch obvious. The fix was straightforward once found; the interesting
part is that no amount of internal validation would have caught it — only
someone actually looking at the running game could.

早期我翻譯的是字串 ID `8xxx`——遊戲資料裡確實存在的短字串，但升級提示框實際
渲染的不是它，是 `28xxx`。模組驗證全過、安裝也沒有任何錯誤——它只是改了一個
沒有人會看到的字串。這件事會浮現，是因為實際測試的人（不是我）連續三次重裝
都回報「沒看到變化」，直到一張截圖把落差攤開來才發現。找到之後修正很直接；
有意思的是，光靠內部驗證永遠抓不到這個——只有真的去看運作中的遊戲才行。

### Verification

Every build run checks, over all 579 lines:

- every numeric token matches the source mod exactly (catches dropped
  digits, flipped signs)
- every line starts with the exact official Traditional Chinese string
  (catches accidental rewrites of the base text)
- no character outside the official Traditional Chinese charset survives
  (catches Simplified leakage)

每次建置都對全部 579 行檢查：

- 每個數值 token 與來源模組完全一致（防止掉數字、正負號寫反）
- 每行開頭完整等於官方繁中原文（防止不小心改到不該動的文字）
- 不殘留任何官方繁中字集以外的字元（防止简體漏網）

## Source & License

See [`SOURCE.md`](SOURCE.md) — data is derived from a non-commercial GPL
mod and carries the same restriction; the scripts here are MIT-licensed.

見 [`SOURCE.md`](SOURCE.md)——資料衍生自非商業性質的 GPL 模組並沿用相同限
制；這裡的程式碼採 MIT 授權。

## Reproducing

```bash
cp .env.example .env        # fill in your 845 mod path — see SOURCE.md
cd scripts
python3 build.py            # 140 short strings + 140 tooltip cards
python3 cards.py            # 294 unit/building cards
python3 extra.py            # 5 manually written cards
python3 merge.py            # merges everything, prints verification results
```

The final output lands at
[`mod/resources/tw/strings/key-value/key-value-modded-strings-utf8.txt`](mod/resources/tw/strings/key-value/key-value-modded-strings-utf8.txt) —
drop the `mod/` folder into your `mods/local/` directory and enable it from
the in-game Mods screen.

最終輸出在
[`mod/resources/tw/strings/key-value/key-value-modded-strings-utf8.txt`](mod/resources/tw/strings/key-value/key-value-modded-strings-utf8.txt)——
把 `mod/` 資料夾丟進你的 `mods/local/` 目錄，在遊戲內的 Mods 畫面勾選即可。
