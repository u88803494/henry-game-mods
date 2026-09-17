# Age of Empires II: Definitive Edition

## Mods

- [`tw-upgrade-stats/`](tw-upgrade-stats/) — adds real numbers to the
  official Traditional Chinese client's upgrade buttons and unit cards.
  為官方繁體中文版的升級按鈕與單位卡補上實際數值。

## Installing

Each mod's own README has full details, but in general: local mods for this
game live in a per-account folder scanned only at game startup:

```
~/Library/Application Support/Feral Interactive/Age Of Empires II/VFS/User/
  Games/Age of Empires 2 DE/<your SteamID64>/mods/local/
```

Drop a mod's folder in there, restart the game once, then enable it from
the in-game Mods screen. **Do not hand-edit `mod-status.json`** in that
same directory — the game rewrites it wholesale on exit, so any manual
change is silently lost.

每個模組自己的 README 有完整細節，但一般來說：這款遊戲的本機模組放在依帳號
區分的資料夾，**只在遊戲啟動時掃描一次**（見上方路徑）。把模組資料夾丟進去、
重開一次遊戲、在遊戲內的 Mods 畫面勾選即可。**不要手動編輯同目錄下的
`mod-status.json`**——遊戲結束時會整份覆寫，任何手動修改都會被默默蓋掉。
