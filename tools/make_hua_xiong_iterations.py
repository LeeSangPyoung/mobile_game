from pathlib import Path

from PIL import Image, ImageDraw, ImageFont


ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "tmp" / "hua_xiong_iterations"
OUT.mkdir(parents=True, exist_ok=True)


def load(name: str) -> Image.Image:
    return Image.open(ROOT / "assets" / "generals" / "busts" / f"{name}.png").convert("RGBA")


def recolor_hue(img: Image.Image, source: str, target_rgb: tuple[int, int, int], strength: float = 0.86) -> Image.Image:
    rgba = img.convert("RGBA")
    px = rgba.load()
    for y in range(rgba.height):
        for x in range(rgba.width):
            r, g, b, a = px[x, y]
            if a < 8:
                continue

            if source == "blue":
                hit = b > 70 and b > r * 1.12 and b > g * 0.92
            elif source == "red":
                hit = r > 85 and r > g * 1.18 and r > b * 1.16
            else:
                hit = False

            if not hit:
                continue

            lum = max(0.18, min(1.25, (0.299 * r + 0.587 * g + 0.114 * b) / 150))
            tr, tg, tb = target_rgb
            nr = int(r * (1 - strength) + min(255, tr * lum) * strength)
            ng = int(g * (1 - strength) + min(255, tg * lum) * strength)
            nb = int(b * (1 - strength) + min(255, tb * lum) * strength)
            px[x, y] = (nr, ng, nb, a)
    return rgba


def add_plain_badge(img: Image.Image, center: tuple[int, int], radius: int = 36) -> Image.Image:
    out = img.copy()
    draw = ImageDraw.Draw(out, "RGBA")
    cx, cy = center
    box = (cx - radius, cy - radius, cx + radius, cy + radius)
    draw.ellipse(box, fill=(61, 49, 37, 255), outline=(238, 183, 63, 255), width=7)
    draw.ellipse((cx - radius + 10, cy - radius + 10, cx + radius - 10, cy + radius - 10), outline=(175, 119, 31, 255), width=4)
    flame = [
        (cx, cy - 22),
        (cx + 12, cy - 5),
        (cx + 4, cy - 5),
        (cx + 17, cy + 18),
        (cx, cy + 8),
        (cx - 15, cy + 20),
        (cx - 5, cy - 4),
        (cx - 15, cy - 4),
    ]
    draw.polygon(flame, fill=(225, 164, 42, 255))
    draw.line(flame + [flame[0]], fill=(255, 219, 91, 255), width=2)
    return out


def candidate_from_xu_huang() -> Image.Image:
    img = load("xu_huang")
    img = recolor_hue(img, "blue", (117, 32, 27), 0.78)
    img = add_plain_badge(img, (332, 276), 37)
    return img


def candidate_from_yan_liang() -> Image.Image:
    img = load("yan_liang")
    img = recolor_hue(img, "red", (105, 28, 25), 0.45)
    img = add_plain_badge(img, (319, 265), 36)
    return img


def candidate_from_xu_chu() -> Image.Image:
    img = load("xu_chu")
    img = recolor_hue(img, "blue", (115, 34, 27), 0.52)
    img = add_plain_badge(img, (321, 282), 38)
    return img


def grid_bg(size: tuple[int, int]) -> Image.Image:
    w, h = size
    bg = Image.new("RGBA", size, (28, 19, 11, 255))
    draw = ImageDraw.Draw(bg, "RGBA")
    for x in range(0, w, 48):
        draw.line((x, 0, x, h), fill=(255, 255, 255, 16), width=1)
    for y in range(0, h, 48):
        draw.line((0, y, w, y), fill=(255, 255, 255, 16), width=1)
    return bg


def make_compare(candidates: list[tuple[str, Image.Image]]) -> None:
    refs = [("xiahou_dun", load("xiahou_dun")), ("xu_chu", load("xu_chu")), ("xu_huang", load("xu_huang"))]
    items = refs + candidates
    card_w, card_h = 360, 500
    label_h = 38
    sheet = Image.new("RGBA", (card_w * len(items), card_h + label_h), (19, 12, 7, 255))
    draw = ImageDraw.Draw(sheet, "RGBA")
    try:
        font = ImageFont.truetype("/System/Library/Fonts/AppleSDGothicNeo.ttc", 20)
    except OSError:
        font = ImageFont.load_default()

    for i, (label, img) in enumerate(items):
        x0 = i * card_w
        card = grid_bg((card_w, card_h))
        bbox = img.getchannel("A").getbbox()
        crop = img.crop(bbox) if bbox else img
        crop.thumbnail((card_w - 34, card_h - 24), Image.Resampling.LANCZOS)
        card.alpha_composite(crop, ((card_w - crop.width) // 2, card_h - crop.height - 8))
        sheet.alpha_composite(card, (x0, 0))
        draw.rectangle((x0, card_h, x0 + card_w, card_h + label_h), fill=(18, 10, 6, 255))
        draw.text((x0 + 14, card_h + 8), label, fill=(255, 222, 112, 255), font=font)
        draw.line((x0, 0, x0, card_h + label_h), fill=(137, 94, 29, 255), width=2)

    sheet.save(OUT / "hua_xiong_compare_sheet.png")


def main() -> None:
    candidates = [
        ("candidate_xu_huang_base", candidate_from_xu_huang()),
        ("candidate_yan_liang_base", candidate_from_yan_liang()),
        ("candidate_xu_chu_base", candidate_from_xu_chu()),
    ]
    for label, img in candidates:
        img.save(OUT / f"{label}.png")
    make_compare(candidates)


if __name__ == "__main__":
    main()
