# -*- coding: utf-8 -*-
import json, lib, re, collections, prose, cardprose
res   = json.load(open("result.json"))   # 140 短字串 + 140 升級卡
cards = json.load(open("cards.json"))    # 294 單位/建築卡
extra = json.load(open("extra.json"))    # 5 張人工補充
tw, mod = lib.load(lib.TW), lib.load(lib.MOD)
core = set(lib.core_set())

dup = (set(res) & set(cards)) | (set(res) & set(extra)) | (set(cards) & set(extra))
assert not dup, f"key 重複: {dup}"
all_ = {**res, **cards, **extra}
json.dump(all_, open("final.json", "w"), ensure_ascii=False, indent=1)

cs = set()
for v in tw.values(): cs |= set(v)
fails = []
def chk(c, l, d=""):
    print(f"  {'✅' if c else '❌'}  {l}" + ("" if c or not d else f"\n        {d}"))
    if not c: fails.append(l)

print(f"=== 合併後 {len(all_)} 條 ===")
print(f"    升級短字串 140 / 升級卡 140 / 單位建築卡 {len(cards)} / 人工補充 {len(extra)}\n")
chk(len(all_) == 140+140+len(cards)+len(extra), "總數正確且無 key 重複")
chk(all(v.startswith(tw[k]) or k in cards or k in extra for k, v in all_.items()),
    "140 條升級相關項目開頭等於繁中原版")
chk(all(all_[k].startswith(re.sub(r'\\n?<GREY>.*?<DEFAULT>', '', tw[k])) for k in cards),
    "單位卡開頭等於繁中原版（移除灰字後）")
chk(all(all_[k].startswith(tw[k]) for k in extra), "人工補充卡開頭等於繁中原版")

b = collections.Counter()
for v in all_.values():
    for ch in v:
        if '一' <= ch <= '鿿' and ch not in cs: b[ch] += 1
chk(not b, "全檔無官方字集以外的 CJK 字元", str(dict(b)))

miss = [x for a, x in prose.PROSE + cardprose.CARD_PROSE
        if [c for c in x if '一' <= c <= '鿿' and c not in cs]]
chk(not miss, f"詞彙表 {len(prose.PROSE)+len(cardprose.CARD_PROSE)} 項用字均為官方既有", str(miss))

# 數值完整性（僅對 140 條升級，卡片為改寫故不比對）
nb = []
f = lambda s: re.findall(r'\d+(?:\.\d+)?', s)
for k in core:
    src = f(mod[k])
    for t, base in ((all_[k], tw[k]), (all_[str(int(k)+20000)], tw[str(int(k)+20000)])):
        o, p = f(t), f(base)
        if o[:len(p)] == p: o = o[len(p):]
        if src != o: nb.append(k)
chk(not nb, "140 條升級的數值與來源一致", str(sorted(set(nb))[:5]))
chk(not [k for k, v in all_.items() if "火攻箭船" in v and "火攻箭船" not in tw[k]],
    "未引入說明卡專有名稱變體")
chk(not [k for k in cards if "<GREY>" in all_[k]], "單位卡的灰字行已全數移除")
print("\n" + ("✅ 全部通過" if not fails else f"❌ {fails}"))
