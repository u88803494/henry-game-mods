# -*- coding: utf-8 -*-
"""Composite a Traditional Chinese abbreviation onto each civ's emblem badge.

Reads the text-free base crest art shipped with the official game install,
overlays a 1-2 character label (white fill, black outline, PingFang TC
Semibold, 80% opacity), and writes the result to mod/widgetui/textures/
menu/civs/. Run from anywhere; paths below are absolute by design since the
source art lives in the Steam install, not this repo.
"""
import glob
import os

from PIL import Image, ImageDraw, ImageFont

GAME_CIVS_DIR = os.path.expanduser(
    "~/Library/Application Support/Steam/steamapps/common/AoE2DE/"
    "AgeOfEmpires2Data/widgetui/textures/menu/civs"
)
FONT_PATH = (
    "/System/Library/AssetsV2/com_apple_MobileAsset_Font8/"
    "86ba2c91f017a3749571a82f2c6d890ac7ffb2fb.asset/AssetData/PingFang.ttc"
)
FONT_INDEX = 10  # PingFang TC Semibold
OUT_DIR = os.path.join(os.path.dirname(__file__), "..", "mod",
                        "widgetui", "textures", "menu", "civs")
BADGE_SIZE = 104
TEXT_ALPHA = 0.80

# civ texture filename -> Traditional Chinese abbreviation.
# Default: the most common single-character reference for the civilization.
# Extended to 2 characters only where two civs would otherwise collide on
# the same leading character (see docs/civ-abbreviation-table.md for the
# full rationale and the disambiguation rule).
CIVS = {
    "britons": "英", "franks": "法", "goths": "哥", "teutons": "德", "japanese": "日",
    "chinese": "中", "byzantines": "拜", "persians": "波斯", "saracens": "薩", "turks": "土",
    "vikings": "維", "mongols": "蒙", "celts": "塞", "spanish": "西", "aztecs": "阿茲",
    "mayans": "馬雅", "huns": "匈", "koreans": "韓", "italians": "義", "indians": "印度",
    "incas": "印加", "magyars": "馬札", "slavs": "斯拉", "portuguese": "葡", "ethiopians": "衣",
    "malians": "馬利", "berbers": "柏", "khmer": "高", "malay": "馬來", "burmese": "緬",
    "vietnamese": "越", "bulgarians": "保", "tatars": "韃", "cumans": "庫", "lithuanians": "立",
    "burgundians": "勃", "sicilians": "西里", "poles": "波蘭", "bohemians": "波希", "dravidians": "達",
    "bengalis": "孟", "gurjaras": "瞿", "romans": "羅", "armenians": "亞", "georgians": "喬",
    "achaemenids": "阿契", "athenians": "雅", "spartans": "斯巴", "shu": "蜀", "wu": "吳",
    "wei": "魏", "jurchens": "金", "khitans": "契", "macedonians": "馬其", "thracians": "色",
}


def render(civfile: str, text: str) -> Image.Image:
    base_path = os.path.join(GAME_CIVS_DIR, f"{civfile}.png")
    base = Image.open(base_path).convert("RGBA")
    assert base.size == (BADGE_SIZE, BADGE_SIZE), (civfile, base.size)

    layer = Image.new("RGBA", (BADGE_SIZE, BADGE_SIZE), (0, 0, 0, 0))
    draw = ImageDraw.Draw(layer)
    fontsize = 44 if len(text) == 1 else 34
    font = ImageFont.truetype(FONT_PATH, fontsize, index=FONT_INDEX)

    bbox = draw.textbbox((0, 0), text, font=font)
    w, h = bbox[2] - bbox[0], bbox[3] - bbox[1]
    x = (BADGE_SIZE - w) / 2 - bbox[0]
    y = (BADGE_SIZE - h) / 2 - bbox[1] - 2

    # black outline: stamp the glyph at every offset inside a radius-3 disc
    for dx in range(-3, 4):
        for dy in range(-3, 4):
            if dx * dx + dy * dy <= 9:
                draw.text((x + dx, y + dy), text, font=font, fill=(0, 0, 0, 255))
    draw.text((x, y), text, font=font, fill=(255, 255, 255, 255))

    r, g, b, a = layer.split()
    a = a.point(lambda p: int(p * TEXT_ALPHA))
    layer = Image.merge("RGBA", (r, g, b, a))

    return Image.alpha_composite(base, layer)


def main():
    os.makedirs(OUT_DIR, exist_ok=True)
    for civfile, label in CIVS.items():
        out = render(civfile, label)
        out.save(os.path.join(OUT_DIR, f"{civfile}.png"))
    print(f"wrote {len(CIVS)} badges to {os.path.abspath(OUT_DIR)}")


if __name__ == "__main__":
    main()
