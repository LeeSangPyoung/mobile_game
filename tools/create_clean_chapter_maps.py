from pathlib import Path
import math
import random
from PIL import Image, ImageDraw, ImageFont, ImageFilter


ROOT = Path(__file__).resolve().parents[1]
OUT_DIR = ROOT / "assets" / "maps"
W, H = 307, 1024

FONT_BOLD = "/System/Library/Fonts/Supplemental/Arial Bold.ttf"
FONT_KR = "/System/Library/Fonts/Supplemental/AppleGothic.ttf"

CHAPTERS = [
    {
        "title": "1-20 여정",
        "range": (1, 20),
        "sky": ((222, 239, 202), (247, 229, 182)),
        "land": (126, 178, 92),
        "land2": (78, 135, 78),
        "road": (224, 198, 132),
        "road_edge": (139, 104, 59),
        "water": (77, 166, 167),
        "badge": (72, 55, 33),
        "rim": (219, 166, 80),
        "title_box": (29, 58, 36),
    },
    {
        "title": "21-40 여정",
        "range": (21, 40),
        "sky": ((208, 231, 229), (235, 238, 210)),
        "land": (104, 150, 103),
        "land2": (62, 112, 91),
        "road": (215, 205, 170),
        "road_edge": (112, 100, 70),
        "water": (92, 157, 179),
        "badge": (54, 54, 44),
        "rim": (199, 171, 105),
        "title_box": (33, 60, 64),
    },
    {
        "title": "41-60 여정",
        "range": (41, 60),
        "sky": ((235, 198, 129), (244, 226, 170)),
        "land": (178, 118, 57),
        "land2": (129, 83, 47),
        "road": (224, 175, 99),
        "road_edge": (122, 73, 39),
        "water": (84, 137, 122),
        "badge": (83, 50, 29),
        "rim": (225, 165, 75),
        "title_box": (88, 39, 24),
    },
    {
        "title": "61-80 여정",
        "range": (61, 80),
        "sky": ((34, 49, 82), (99, 83, 108)),
        "land": (48, 92, 98),
        "land2": (30, 62, 75),
        "road": (168, 151, 132),
        "road_edge": (86, 68, 77),
        "water": (32, 103, 126),
        "badge": (54, 45, 78),
        "rim": (189, 132, 174),
        "title_box": (59, 42, 82),
    },
    {
        "title": "81-100 여정",
        "range": (81, 100),
        "sky": ((201, 225, 240), (232, 241, 242)),
        "land": (202, 216, 210),
        "land2": (133, 155, 158),
        "road": (230, 226, 211),
        "road_edge": (122, 126, 119),
        "water": (93, 169, 196),
        "badge": (46, 57, 63),
        "rim": (204, 209, 198),
        "title_box": (28, 79, 86),
    },
]

PINS = [
    (50, 94), (63, 88), (36, 84), (52, 78), (34, 72),
    (60, 67), (43, 61), (70, 56), (58, 50), (33, 45),
    (47, 40), (28, 35), (55, 31), (75, 27), (51, 30),
    (35, 25), (22, 21), (43, 17), (58, 14), (50, 11),
]


def font(path, size):
    try:
        return ImageFont.truetype(path, size)
    except OSError:
        return ImageFont.load_default()


def text_center(draw, pos, text, fnt, fill, stroke=0, stroke_fill=(0, 0, 0)):
    box = draw.textbbox((0, 0), text, font=fnt, stroke_width=stroke)
    x = pos[0] - (box[2] - box[0]) / 2
    y = pos[1] - (box[3] - box[1]) / 2 - box[1] * 0.15
    draw.text((x, y), text, font=fnt, fill=fill, stroke_width=stroke, stroke_fill=stroke_fill)


def gradient(top, bottom):
    im = Image.new("RGB", (W, H), top)
    pix = im.load()
    for y in range(H):
        t = y / (H - 1)
        for x in range(W):
            pix[x, y] = tuple(int(top[i] * (1 - t) + bottom[i] * t) for i in range(3))
    return im.convert("RGBA")


def polyline(points, width):
    mask = Image.new("L", (W, H), 0)
    d = ImageDraw.Draw(mask)
    d.line(points, fill=255, width=width, joint="curve")
    for x, y in points:
        r = width // 2
        d.ellipse((x - r, y - r, x + r, y + r), fill=255)
    return mask


def draw_mountains(draw, rng, color, y_base, count):
    for _ in range(count):
        x = rng.randint(-40, W - 20)
        w = rng.randint(75, 150)
        h = rng.randint(70, 160)
        peak = (x + w // 2, y_base - h)
        draw.polygon([(x, y_base), peak, (x + w, y_base)], fill=color)
        snow = tuple(min(255, c + 45) for c in color)
        draw.polygon([(peak[0], peak[1]), (peak[0] - w * 0.15, peak[1] + h * 0.35), (peak[0] + w * 0.18, peak[1] + h * 0.35)], fill=snow)


def draw_tree(draw, x, y, scale, theme, rng):
    trunk = (72, 55, 35)
    leaf = theme["land2"]
    draw.rectangle((x - scale * 0.08, y, x + scale * 0.08, y + scale * 0.42), fill=trunk)
    for i in range(3):
        r = scale * (0.45 - i * 0.08)
        cy = y - scale * (0.18 + i * 0.18)
        tint = tuple(max(0, min(255, c + rng.randint(-12, 14))) for c in leaf)
        draw.ellipse((x - r, cy - r * 0.7, x + r, cy + r * 0.7), fill=tint)


def draw_building(draw, x, y, s, theme):
    wall = (142, 99, 57)
    roof = (39, 83, 89) if theme["title"] != "41-60 여정" else (107, 45, 34)
    dark = (56, 42, 32)
    draw.rectangle((x - s * 0.45, y - s * 0.28, x + s * 0.45, y + s * 0.28), fill=wall, outline=dark)
    draw.polygon([(x - s * 0.6, y - s * 0.28), (x, y - s * 0.65), (x + s * 0.6, y - s * 0.28)], fill=roof, outline=dark)
    draw.rectangle((x - s * 0.12, y - s * 0.02, x + s * 0.12, y + s * 0.28), fill=(70, 45, 31))


def draw_title(draw, title, theme):
    box = (49, 18, W - 49, 74)
    shadow = (box[0] + 3, box[1] + 4, box[2] + 3, box[3] + 4)
    draw.rounded_rectangle(shadow, radius=8, fill=(0, 0, 0, 80))
    draw.rounded_rectangle(box, radius=8, fill=theme["title_box"], outline=(219, 172, 91), width=3)
    draw.rounded_rectangle((box[0] + 5, box[1] + 5, box[2] - 5, box[3] - 5), radius=5, outline=(255, 232, 158), width=1)
    text_center(draw, ((box[0] + box[2]) / 2, (box[1] + box[3]) / 2), title, font(FONT_KR, 28), (255, 237, 182), 1, (33, 25, 19))


def draw_badge(draw, x, y, label, theme):
    r = 18 if label < 100 else 20
    draw.ellipse((x - r + 3, y - r + 4, x + r + 3, y + r + 4), fill=(0, 0, 0, 95))
    draw.ellipse((x - r, y - r, x + r, y + r), fill=theme["badge"], outline=(30, 24, 20), width=3)
    draw.ellipse((x - r + 4, y - r + 4, x + r - 4, y + r - 4), outline=theme["rim"], width=3)
    size = 18 if label < 100 else 15
    text_center(draw, (x, y), str(label), font(FONT_BOLD, size), (255, 241, 202), 1, (42, 29, 20))


def create_chapter(idx, theme):
    rng = random.Random(9000 + idx)
    im = gradient(*theme["sky"])
    draw = ImageDraw.Draw(im, "RGBA")

    draw.rectangle((0, 210, W, H), fill=(*theme["land"], 205))
    draw_mountains(draw, rng, tuple(max(0, c - 18) for c in theme["land2"]), 250, 7)
    draw_mountains(draw, rng, tuple(max(0, c - 2) for c in theme["land2"]), 340, 8)

    river_x = 40 + idx * 8
    river = [(river_x + math.sin(y * 0.017 + idx) * 28, y) for y in range(170, H, 18)]
    draw.line(river, fill=(*theme["water"], 155), width=34, joint="curve")
    draw.line(river, fill=(215, 242, 240, 80), width=8, joint="curve")

    for _ in range(75):
        x = rng.randint(0, W)
        y = rng.randint(145, H)
        s = rng.randint(13, 32)
        draw_tree(draw, x, y, s, theme, rng)

    for _ in range(10):
        x = rng.randint(28, W - 28)
        y = rng.randint(170, H - 35)
        draw_building(draw, x, y, rng.randint(16, 25), theme)

    pts = [(round(W * x / 100), round(H * y / 100)) for x, y in PINS]
    road_edge = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    edge_mask = polyline(pts, 44).filter(ImageFilter.GaussianBlur(1.0))
    road_edge.putalpha(edge_mask)
    edge_fill = Image.new("RGBA", (W, H), (*theme["road_edge"], 210))
    im.alpha_composite(Image.composite(edge_fill, road_edge, edge_mask))

    road_layer = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    road_mask = polyline(pts, 32).filter(ImageFilter.GaussianBlur(0.45))
    road_layer.putalpha(road_mask)
    road_fill = Image.new("RGBA", (W, H), (*theme["road"], 255))
    im.alpha_composite(Image.composite(road_fill, road_layer, road_mask))

    draw = ImageDraw.Draw(im, "RGBA")
    for a, b in zip(pts, pts[1:]):
        steps = max(1, int(math.dist(a, b) / 13))
        for n in range(steps):
            t = n / steps
            x = a[0] * (1 - t) + b[0] * t
            y = a[1] * (1 - t) + b[1] * t
            if n % 2 == 0:
                draw.ellipse((x - 1.7, y - 1.7, x + 1.7, y + 1.7), fill=(82, 63, 43, 115))

    draw_title(draw, theme["title"], theme)

    start, end = theme["range"]
    for n, (x, y) in enumerate(pts, start=start):
        draw_badge(draw, x, y, n, theme)

    return im.convert("RGB")


def main():
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    for old in OUT_DIR.glob("*"):
        if old.is_file():
            old.unlink()

    chapters = []
    for idx, theme in enumerate(CHAPTERS):
        im = create_chapter(idx, theme)
        out = OUT_DIR / f"chapter{idx + 1}.png"
        im.save(out, quality=95)
        chapters.append(im)

    combined = Image.new("RGB", (W * 5, H), (255, 255, 255))
    for idx, im in enumerate(chapters):
        combined.paste(im, (idx * W, 0))
    combined.save(ROOT / "assets" / "map.png", quality=95)


if __name__ == "__main__":
    main()
