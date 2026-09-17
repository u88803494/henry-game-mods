# -*- coding: utf-8 -*-
"""單位／建築說明卡：移除繁中原版的 <GREY> 升級行，追加 845 的數值段。"""
import lib, re, json
from build import TABLE, MAXLEN       # 沿用同一套術語表
import cardprose

# 併入卡片專屬詞彙（不覆蓋既有詞條）
for a, b in cardprose.CARD_PROSE:
    TABLE.setdefault(a, b)
_MAX = max(MAXLEN, max(len(a) for a, _ in cardprose.CARD_PROSE))

def translate(s):
    out, i, n = [], 0, len(s)
    while i < n:
        for L in range(min(_MAX, n - i), 0, -1):
            seg = s[i:i+L]
            if seg in TABLE:
                out.append(TABLE[seg]); i += L; break
        else:
            out.append(s[i]); i += 1
    return "".join(out)

tw, mod = lib.load(lib.TW), lib.load(lib.MOD)
core = set(lib.core_set())

ICON = re.compile(r'<(hp|attack|armor|piercearmor|range|garrison)>')
GREY = re.compile(r'\\n?<GREY>.*?<DEFAULT>', re.S)

def stats_of(s):
    """取 845 卡片中圖示行之後的數值段"""
    parts = s.split("\\n")
    idx = next((i for i, l in enumerate(parts) if ICON.search(l)), None)
    if idx is None: return None
    rest = [p.strip() for p in parts[idx+1:] if p.strip()]
    return rest or None

cands = [k for k in mod if k in tw and k not in core
         and re.search(r'<b>', tw[k]) and stats_of(mod[k])]

out, skipped = {}, []
for k in cands:
    st = stats_of(mod[k])
    base = GREY.sub("", tw[k])                    # 砍掉灰字升級行
    if ICON.search(base) is None:                 # 繁中無圖示行者跳過，避免結構不明
        skipped.append(k); continue
    out[k] = base + "\\n" + "\\n".join(translate(x) for x in st)

json.dump(out, open("cards.json", "w"), ensure_ascii=False, indent=1)
print(f"產出說明卡 {len(out)} 張（跳過 {len(skipped)} 張：繁中無圖示行）")
if skipped: print("  跳過:", skipped[:10])
