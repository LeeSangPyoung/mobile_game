from __future__ import annotations

import json
import math
import re
from pathlib import Path
import colorsys

from PIL import Image, ImageDraw, ImageFont


ROOT = Path(__file__).resolve().parents[1]
SRC_DIR = ROOT / "assets" / "generals" / "busts_extra_70"
OUT_DIR = ROOT / "assets" / "generals" / "busts_extra_70_colorfit"
TMP_DIR = ROOT / "tmp" / "extra_generals_70_stylelocked"
OUT_DIR.mkdir(parents=True, exist_ok=True)
TMP_DIR.mkdir(parents=True, exist_ok=True)


def clamp(v: float) -> int:
    return max(0, min(255, int(round(v))))


def fit_pixel(r: int, g: int, b: int) -> tuple[int, int, int]:
    mx = max(r, g, b)
    h, s, v = colorsys.rgb_to_hsv(r / 255, g / 255, b / 255)
    hue = h * 360
    is_red = r > 95 and r > g * 1.15 and r > b * 1.12
    is_blue = b > 65 and b > r * 1.05 and b > g * 0.88
    lum = 0.299 * r + 0.587 * g + 0.114 * b
    is_skin = (
        (12 <= hue <= 42 and 0.18 <= s <= 0.78 and 0.28 <= v <= 0.96 and r > g > b and lum > 78)
        or (r > 120 and 58 < g < 190 and 28 < b < 150 and r > g * 1.03 and g > b * 1.05 and lum > 78)
    )
    if is_skin:
        return r, g, b
    is_gold = r > 105 and g > 70 and b < 105 and r > b * 1.25 and g > b * 1.12
    is_white = r > 145 and g > 145 and b > 140 and abs(r - g) < 45

    # Gentle global lift: the first batch was a little darker/browner than the
    # reference busts. Keep it modest so the render still looks native.
    nr = r * 1.035 + 3
    ng = g * 1.050 + 4
    nb = b * 1.010 + 1

    # Restore gold trim pop. The source set has very bright, clean gold edges.
    if is_gold:
        nr = nr * 1.12 + 9
        ng = ng * 1.13 + 8
        ng = max(ng, nr * 0.76)
        nb = nb * 0.95

    # Keep crimson faction colors assertive; only clean the hue very slightly.
    if is_red:
        ng = ng * 0.985
        nb = nb * 0.995

    # Keep the Wei-style blues more vivid; several variants lost blue energy.
    if is_blue:
        ng = ng * 1.015
        nb = nb * 1.045 + 2

    # White/silver armor in the original set is clean and bright.
    if is_white:
        nr = nr * 1.025 + 3
        ng = ng * 1.025 + 3
        nb = nb * 1.030 + 4

    # The gallery looked too brown even after average matching. Push non-gold,
    # non-skin warm midtones back toward the source set's black/blue armor feel.
    if 22 <= hue <= 58 and 0.20 <= s <= 0.72 and 0.17 <= v <= 0.62 and not (is_gold or is_skin or is_red or is_white):
        nr = nr * 0.84
        ng = ng * 0.91
        nb = nb * 1.10 + 4

    # Re-anchor neutral armor shadows. This fixes the "newer/too clean" look
    # without dulling gold, red cloth, skin, or white armor.
    if not (is_gold or is_red or is_blue or is_skin or is_white):
        if mx < 82:
            nr *= 0.86
            ng *= 0.88
            nb *= 0.96
        elif mx < 118:
            nr *= 0.93
            ng *= 0.95
            nb *= 1.02

    return clamp(nr), clamp(ng), clamp(nb)


def colorfit(img: Image.Image) -> Image.Image:
    out = img.convert("RGBA").copy()
    px = out.load()
    for y in range(out.height):
        for x in range(out.width):
            r, g, b, a = px[x, y]
            if a < 8:
                continue
            nr, ng, nb = fit_pixel(r, g, b)
            px[x, y] = (nr, ng, nb, a)
    return out


def write_gallery() -> None:
    manifest = json.loads((SRC_DIR / "manifest.json").read_text(encoding="utf-8"))
    rows = "\n".join(f"  ['{m['slug']}', '{m['ko']}', '{m['base']}']," for m in manifest)
    html = (ROOT / "extra_70_busts_gallery.html").read_text(encoding="utf-8")
    html = html.replace("추가 장수 70명 전신 후보", "추가 장수 70명 전신 후보 - 색감 보정 v2")
    html = html.replace("busts_extra_70/", "busts_extra_70_colorfit/")
    html = html.replace("스타일 잠금 후보입니다.", "브라운 중간톤을 낮춘 스타일 잠금 후보입니다.")
    html = re.sub(r"const generals = \\[.*?\\];", f"const generals = [\n{rows}\n];", html, flags=re.S)
    (ROOT / "extra_70_busts_gallery_colorfit.html").write_text(html, encoding="utf-8")


def alpha_bbox(img: Image.Image) -> tuple[int, int, int, int]:
    return img.getchannel("A").getbbox() or (0, 0, img.width, img.height)


def make_contact_sheet() -> None:
    manifest = json.loads((SRC_DIR / "manifest.json").read_text(encoding="utf-8"))
    card_w, art_h, label_h = 250, 310, 40
    cols = 10
    rows = math.ceil(len(manifest) / cols)
    sheet = Image.new("RGBA", (cols * card_w, rows * (art_h + label_h)), (18, 11, 7, 255))
    draw = ImageDraw.Draw(sheet, "RGBA")
    try:
        font_big = ImageFont.truetype("/System/Library/Fonts/AppleSDGothicNeo.ttc", 20)
        font_small = ImageFont.truetype("/System/Library/Fonts/AppleSDGothicNeo.ttc", 13)
    except OSError:
        font_big = ImageFont.load_default()
        font_small = ImageFont.load_default()

    for idx, item in enumerate(manifest):
        col = idx % cols
        row = idx // cols
        x0 = col * card_w
        y0 = row * (art_h + label_h)
        bg = Image.new("RGBA", (card_w, art_h), (31, 21, 12, 255))
        d = ImageDraw.Draw(bg, "RGBA")
        for gx in range(0, card_w, 28):
            d.line((gx, 0, gx, art_h), fill=(255, 255, 255, 12), width=1)
        for gy in range(0, art_h, 28):
            d.line((0, gy, card_w, gy), fill=(255, 255, 255, 12), width=1)
        img = Image.open(OUT_DIR / f"{item['slug']}.png").convert("RGBA")
        crop = img.crop(alpha_bbox(img))
        crop.thumbnail((card_w - 18, art_h - 12), Image.Resampling.LANCZOS)
        bg.alpha_composite(crop, ((card_w - crop.width) // 2, art_h - crop.height - 4))
        sheet.alpha_composite(bg, (x0, y0))
        draw.rectangle((x0, y0 + art_h, x0 + card_w, y0 + art_h + label_h), fill=(18, 10, 6, 255))
        draw.text((x0 + 10, y0 + art_h + 8), item["ko"], fill=(255, 226, 116, 255), font=font_big)
        draw.text((x0 + 72, y0 + art_h + 13), f"{item['slug']}.png", fill=(174, 139, 78, 255), font=font_small)
        draw.rectangle((x0, y0, x0 + card_w, y0 + art_h + label_h), outline=(128, 86, 23, 255), width=1)
    sheet.save(TMP_DIR / "extra_70_contact_sheet_colorfit.png")


def main() -> None:
    for src in sorted(SRC_DIR.glob("*.png")):
        if src.name == "manifest.json":
            continue
        colorfit(Image.open(src)).save(OUT_DIR / src.name)
    (OUT_DIR / "manifest.json").write_text((SRC_DIR / "manifest.json").read_text(encoding="utf-8"), encoding="utf-8")
    write_gallery()
    make_contact_sheet()
    print(OUT_DIR)
    print(ROOT / "extra_70_busts_gallery_colorfit.html")
    print(TMP_DIR / "extra_70_contact_sheet_colorfit.png")


if __name__ == "__main__":
    main()
