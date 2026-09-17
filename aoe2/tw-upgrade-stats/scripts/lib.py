import os, re

def _required_env(name):
    v = os.environ.get(name)
    if not v:
        raise SystemExit(
            f"Missing required environment variable: {name}\n"
            f"Copy .env.example to .env (or export directly) — see scripts/README.md."
        )
    return os.path.expanduser(v)

# Steam install — same path structure for any Mac user, so a sensible default is fine.
GAME_DATA_DIR = os.path.expanduser(os.environ.get(
    "AOE2_GAME_DATA_DIR",
    "~/Library/Application Support/Steam/steamapps/common/AoE2DE/AgeOfEmpires2Data",
))

# The 845 mod's Feral-port path is nested under your SteamID64, which is personal —
# so this one has no default and must be set explicitly.
MOD_845_FILE = _required_env("AOE2_845_SOURCE_FILE")

TW = f"{GAME_DATA_DIR}/resources/tw/strings/key-value/key-value-strings-utf8.txt"
ZH = f"{GAME_DATA_DIR}/resources/zh/strings/key-value/key-value-strings-utf8.txt"
MOD = MOD_845_FILE

def load(p):
    d = {}
    for line in open(p, encoding="utf-8", errors="replace"):
        m = re.match(r'^(\d+)[ \t]+"(.*)"\s*$', line.strip())
        if m: d[m.group(1)] = m.group(2)
    return d

def core_set():
    tw, mod = load(TW), load(MOD)
    has = lambda s: bool(re.search(r'[+\-]?\d', s))
    tag = lambda s: bool(re.search(r'<[A-Za-z/]', s))
    return [k for k in mod if k in tw and not has(tw[k]) and has(mod[k])
            and not tag(tw[k]) and not tag(mod[k])
            and tw[k].startswith(("升級", "研究"))]

def name_map():
    """Official zh↔tw unit/tech name pairs, keyed by matching string IDs. Includes identical pairs."""
    tw, zh = load(TW), load(ZH)
    isname = lambda s: bool(s) and 0 < len(s) <= 16 and not re.search(r'[<>\\\d(){}]', s)
    nm = {}
    for k in zh:
        if k in tw and isname(zh[k]) and isname(tw[k]):
            nm.setdefault(zh[k], set()).add(tw[k])
    return nm
