from pathlib import Path
from PIL import Image, ImageDraw, ImageFont, ImageFilter


ROOT = Path(__file__).resolve().parents[1]
OUT_DIR = ROOT / "assets" / "maps"
GEN_DIR = Path("/Users/leesp/.codex/generated_images/019df0bc-0d1f-7180-beb4-f146aa225dc7")

SOURCES = [
    "ig_0775bc27e578c5c50169f80792b1ec8191b9da94ba0e8fefa0.png",
    "ig_0775bc27e578c5c50169f80822ce1c8191881c14e72bef2ab4.png",
    "ig_0775bc27e578c5c50169f80878c8c881919315ba3e33ba8029.png",
    "ig_0775bc27e578c5c50169f8090b86e8819195c95d897a769e1a.png",
    "ig_0775bc27e578c5c50169f809697fe4819185c0513088632380.png",
]

W, H = 307, 1024
FONT_BOLD = "/System/Library/Fonts/Supplemental/Arial Bold.ttf"
FONT_KR = "/System/Library/Fonts/Supplemental/AppleGothic.ttf"

THEMES = [
    {"title": "1-20 여정", "start": 1, "title_box": (29, 58, 36), "badge": (70, 53, 33), "rim": (221, 168, 82)},
    {"title": "21-40 여정", "start": 21, "title_box": (31, 58, 65), "badge": (54, 54, 45), "rim": (200, 171, 104)},
    {"title": "41-60 여정", "start": 41, "title_box": (89, 39, 25), "badge": (82, 50, 30), "rim": (226, 165, 74)},
    {"title": "61-80 여정", "start": 61, "title_box": (59, 42, 82), "badge": (55, 45, 79), "rim": (190, 132, 174)},
    {"title": "81-100 여정", "start": 81, "title_box": (28, 78, 86), "badge": (45, 57, 64), "rim": (205, 210, 198)},
]

PINS = [
    (48, 94), (61, 89), (42, 84), (54, 79), (36, 74),
    (49, 69), (63, 64), (46, 59), (58, 54), (40, 49),
    (51, 44), (35, 39), (48, 34), (63, 30), (45, 27),
    (55, 24), (37, 21), (49, 18), (59, 15), (50, 12),
]


def font(path, size):
    try:
        return ImageFont.truetype(path, size)
    except OSError:
        return ImageFont.load_default()


def center_text(draw, xy, text, fnt, fill, stroke_width=0, stroke_fill=(0, 0, 0)):
    box = draw.textbbox((0, 0), text, font=fnt, stroke_width=stroke_width)
    x = xy[0] - (box[2] - box[0]) / 2
    y = xy[1] - (box[3] - box[1]) / 2 - box[1] * 0.18
    draw.text((x, y), text, font=fnt, fill=fill, stroke_width=stroke_width, stroke_fill=stroke_fill)


def cover_resize(im):
    im = im.convert("RGB")
    iw, ih = im.size
    scale = max(W / iw, H / ih)
    nw, nh = round(iw * scale), round(ih * scale)
    im = im.resize((nw, nh), Image.Resampling.LANCZOS)
    left = (nw - W) // 2
    top = max(0, (nh - H) // 2)
    return im.crop((left, top, left + W, top + H)).convert("RGBA")


def draw_title(draw, title, theme):
    box = (43, 18, W - 43, 78)
    draw.rounded_rectangle((box[0] + 4, box[1] + 5, box[2] + 4, box[3] + 5), radius=9, fill=(0, 0, 0, 120))
    draw.rounded_rectangle(box, radius=9, fill=theme["title_box"], outline=(220, 171, 88), width=3)
    draw.rounded_rectangle((box[0] + 5, box[1] + 5, box[2] - 5, box[3] - 5), radius=6, outline=(255, 232, 158), width=1)
    center_text(draw, ((box[0] + box[2]) / 2, (box[1] + box[3]) / 2), title, font(FONT_KR, 27), (255, 237, 184), 1, (35, 26, 19))


def draw_badge(draw, x, y, label, theme):
    r = 18 if label < 100 else 20
    draw.ellipse((x - r + 4, y - r + 5, x + r + 4, y + r + 5), fill=(0, 0, 0, 135))
    draw.ellipse((x - r - 3, y - r - 3, x + r + 3, y + r + 3), fill=(220, 187, 119, 140))
    draw.ellipse((x - r, y - r, x + r, y + r), fill=theme["badge"], outline=(24, 20, 17), width=3)
    draw.ellipse((x - r + 4, y - r + 4, x + r - 4, y + r - 4), outline=theme["rim"], width=3)
    center_text(draw, (x, y), str(label), font(FONT_BOLD, 18 if label < 100 else 15), (255, 242, 205), 1, (43, 30, 20))


def compose(idx):
    bg = cover_resize(Image.open(GEN_DIR / SOURCES[idx]))
    # Slight dark veil at edges/top improves UI readability without hiding art.
    shade = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    sd = ImageDraw.Draw(shade, "RGBA")
    sd.rectangle((0, 0, W, 115), fill=(0, 0, 0, 30))
    sd.rectangle((0, 0, 18, H), fill=(0, 0, 0, 28))
    sd.rectangle((W - 18, 0, W, H), fill=(0, 0, 0, 28))
    shade = shade.filter(ImageFilter.GaussianBlur(8))
    bg.alpha_composite(shade)

    draw = ImageDraw.Draw(bg, "RGBA")
    theme = THEMES[idx]
    draw_title(draw, theme["title"], theme)
    for offset, (px, py) in enumerate(PINS):
        x = round(W * px / 100)
        y = round(H * py / 100)
        draw_badge(draw, x, y, theme["start"] + offset, theme)
    return bg.convert("RGB")


def main():
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    for old in OUT_DIR.glob("*"):
        if old.is_file():
            old.unlink()

    chapters = []
    for idx in range(5):
        im = compose(idx)
        im.save(OUT_DIR / f"chapter{idx + 1}.png", quality=95)
        chapters.append(im)

    combined = Image.new("RGB", (W * 5, H), (255, 255, 255))
    for idx, im in enumerate(chapters):
        combined.paste(im, (idx * W, 0))
    combined.save(ROOT / "assets" / "map.png", quality=95)


if __name__ == "__main__":
    main()
