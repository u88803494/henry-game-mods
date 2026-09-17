# -*- coding: utf-8 -*-
"""單次左至右最長匹配翻譯。譯過的區段即鎖住，短詞不會破壞長詞。"""
import lib, glossary, prose, re, json

tw, mod = lib.load(lib.TW), lib.load(lib.MOD)
core, nm = lib.core_set(), lib.name_map()

# 官方名稱表：排除單字與已知雜訊（文明名會插進單位名）
CIV_NOISE = {"土耳其","西班牙","葡萄牙","義大利","意大利","波斯","高棉","緬甸","马来","馬來",
             "印度","日本","中国","中國","法国","法國","英国","英國","德国","德國"}
auto_names = [(k, list(v)[0]) for k, v in nm.items()
              if len(v) == 1 and len(k) >= 2 and k not in CIV_NOISE]

TABLE = {}
def add(pairs):
    for p in pairs:
        a, b = p[0], p[1]
        TABLE.setdefault(a, b)          # 先登錄者優先
add([(a, b) for a, b, _ in glossary.TERMS])          # 1. 屬性／傷害類別（官方定名）
add([(a, b) for a, b, _ in glossary.NAMES_MANUAL])   # 2. 人工確認的單位名
add(auto_names)                                       # 3. 官方名稱表
add(prose.PROSE)                                      # 4. 一般詞彙

# 「攻击」當統計值時作「攻擊力」，當動詞時作「攻擊」
TABLE["攻击 +"] = "攻擊力 +"
TABLE["攻击 -"] = "攻擊力 -"
TABLE["攻击"]   = "攻擊"

MAXLEN = max(len(k) for k in TABLE)

def translate(s):
    out, i, n = [], 0, len(s)
    while i < n:
        for L in range(min(MAXLEN, n - i), 0, -1):
            seg = s[i:i+L]
            if seg in TABLE:
                out.append(TABLE[seg]); i += L; break
        else:
            out.append(s[i]); i += 1
    return "".join(out)

def split_tail(s):
    d = 0
    for i, c in enumerate(s):
        if c == '(':
            if d == 0 and i > 0 and s[i-1] == ' ': return s[:i-1], s[i:]
            d += 1
        elif c == ')': d -= 1
    return s, None

def one_group(t):
    if not t or not t.startswith('(') or not t.endswith(')'): return False
    d = 0
    for i, c in enumerate(t):
        if c == '(': d += 1
        elif c == ')':
            d -= 1
            if d == 0 and i != len(t) - 1: return False
    return True

def blocks(s):
    out, d, buf, name = [], 0, "", ""
    for c in s:
        if c == '(':
            if d == 0: name = buf.strip(" 、和")
            d += 1; buf = "" if d == 1 else buf + c
        elif c == ')':
            d -= 1
            if d == 0: out.append((name, buf)); buf = ""
            else: buf += c
        else: buf += c
    return out

stats, manual_keys = {}, []
for k in core:
    prefix, tail = split_tail(mod[k])
    if tail and one_group(tail) and not re.search(r'[（(]', prefix):
        stats[k] = translate(tail[1:-1])          # 去掉外層括號
    else:
        manual_keys.append(k)

# 3 條人工
for key, names in (("8034", ["弩砲戰船", "火戰船", "重型武裝商船"]),
                   ("8035", ["重型弩砲戰船", "重型火戰船", "克拉克帆船"])):
    bs = blocks(mod[key]); assert len(bs) == 3
    stats[key] = "; ".join(f"{n} {translate(b)}" for n, (_, b) in zip(names, bs))
stats["8495"] = translate(blocks(mod["8495"])[-1][1])

# 來源缺陷修正（唯一一處偏離模組原文）：
# 845 模組 508000 原文誤植「攻击目标攻击目标后」，重複一次；去除重複。
_k = "508000"
assert stats[_k].count("攻擊目標攻擊目標") == 1
stats[_k] = stats[_k].replace("攻擊目標攻擊目標", "攻擊目標", 1)
assert len(stats) == 140, len(stats)

# 8xxx 短字串（科技樹等處）與 28xxx 說明卡（升級按鈕提示實際顯示的就是這個）
result = {}
for k, st in stats.items():
    result[k] = tw[k] + " (" + st + ")"
    card = str(int(k) + 20000)
    assert card in tw, card
    result[card] = tw[card] + "\\n" + st + "。"

assert len(result) == 280, len(result)
json.dump(result, open("result.json", "w"), ensure_ascii=False, indent=1)
json.dump(stats, open("stats.json", "w"), ensure_ascii=False, indent=1)
print(f"完成：140 條短字串 + 140 張說明卡 = {len(result)} 條"
      f"（自動 {140-len(manual_keys)}，人工 {len(manual_keys)}：{manual_keys}）")
