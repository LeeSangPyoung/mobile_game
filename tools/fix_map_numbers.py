from pathlib import Path
from PIL import Image, ImageDraw, ImageFont, ImageFilter


ROOT = Path(__file__).resolve().parents[1]
ASSETS = ROOT / "assets"
CHAPTER_DIR = ASSETS / "maps"
SOURCE_MAP = ASSETS / "map.png.bak"
OUTPUT_SIZE = (307, 1024)

# Separator columns in assets/map.png.bak are full-height white strips. These
# bounds crop only the illustrated chapter panels, then normalize to app size.
CHAPTER_BOUNDS = [
    (0, 0, 291, 1024),
    (295, 0, 592, 1024),
    (596, 0, 896, 1024),
    (900, 0, 1195, 1024),
    (1198, 0, 1536, 1024),
]

FONT_BOLD = "/System/Library/Fonts/Supplemental/Arial Bold.ttf"
FONT_KR = "/System/Library/Fonts/Supplemental/AppleGothic.ttf"

PIN_POSITIONS = [
    (48, 95), (68, 90), (60, 84), (36, 79), (24, 74),
    (38, 69), (60, 64), (76, 59), (58, 54), (32, 49),
    (22, 44), (38, 39), (58, 34), (76, 29), (60, 24),
    (32, 20), (22, 16), (42, 13), (58, 10), (50, 7),
]

THEMES = [
    {"badge": (77, 60, 36), "rim": (211, 166, 94), "title": (33, 55, 37), "title_rim": (178, 132, 75), "road": (214, 190, 128)},
    {"badge": (58, 56, 43), "rim": (196, 164, 102), "title": (31, 55, 61), "title_rim": (130, 150, 145), "road": (198, 190, 158)},
    {"badge": (78, 49, 32), "rim": (222, 169, 86), "title": (84, 37, 25), "title_rim": (167, 91, 61), "road": (209, 170, 106)},
    {"badge": (55, 48, 75), "rim": (180, 135, 152), "title": (57, 40, 76), "title_rim": (150, 91, 124), "road": (167, 150, 132)},
    {"badge": (54, 61, 70), "rim": (197, 201, 197), "title": (27, 76, 83), "title_rim": (117, 173, 177), "road": (222, 222, 212)},
]


def load_font(path, size):
    try:
        return ImageFont.truetype(path, size)
    except OSError:
        return ImageFont.load_default()


def centered_text(draw, xy, text, font, fill, stroke_width=0, stroke_fill=None):
    bbox = draw.textbbox((0, 0), text, font=font, stroke_width=stroke_width)
    x = xy[0] - (bbox[2] - bbox[0]) / 2
    y = xy[1] - (bbox[3] - bbox[1]) / 2 - bbox[1] / 2
    draw.text((x, y), text, font=font, fill=fill, stroke_width=stroke_width, stroke_fill=stroke_fill)


def rounded_box(draw, box, radius, fill, outline, width=2):
    draw.rounded_rectangle(box, radius=radius, fill=fill, outline=outline, width=width)
    inset = width + 2
    inner = (box[0] + inset, box[1] + inset, box[2] - inset, box[3] - inset)
    draw.rounded_rectangle(inner, radius=max(1, radius - inset), outline=(255, 231, 162), width=1)


def draw_badge(base, cx, cy, label, theme, scale=1.0):
    size = int(round(34 * scale))
    if len(label) >= 3:
        size = int(round(40 * scale))
    radius = size // 2

    overlay = Image.new("RGBA", base.size, (0, 0, 0, 0))
    od = ImageDraw.Draw(overlay)
    shadow_box = (cx - radius + 2, cy - radius + 3, cx + radius + 2, cy + radius + 3)
    od.ellipse(shadow_box, fill=(0, 0, 0, 120))
    overlay = overlay.filter(ImageFilter.GaussianBlur(max(1, int(1.2 * scale))))
    base.alpha_composite(overlay)

    draw = ImageDraw.Draw(base)
    box = (cx - radius, cy - radius, cx + radius, cy + radius)
    draw.ellipse(box, fill=theme["badge"], outline=(43, 31, 24), width=max(2, int(2 * scale)))
    inset = max(3, int(3 * scale))
    draw.ellipse(
        (box[0] + inset, box[1] + inset, box[2] - inset, box[3] - inset),
        outline=theme["rim"],
        width=max(2, int(2 * scale)),
    )
    font_size = int(round((18 if len(label) <= 2 else 15) * scale))
    font = load_font(FONT_BOLD, font_size)
    centered_text(draw, (cx, cy - int(1 * scale)), label, font, (255, 243, 204), 1, (42, 28, 20))


def draw_title(base, chapter_idx, theme, scale=1.0):
    draw = ImageDraw.Draw(base)
    w, _ = base.size
    title = f"{chapter_idx * 20 + 1}-{(chapter_idx + 1) * 20} 여정"
    if chapter_idx == 0:
        title = "1-20 여정"

    box_w = int(round(176 * scale))
    box_h = int(round(44 * scale))
    x1 = int(w / 2 - box_w / 2)
    y1 = int(round(15 * scale))
    box = (x1, y1, x1 + box_w, y1 + box_h)
    rounded_box(draw, box, int(round(9 * scale)), theme["title"], theme["title_rim"], max(2, int(2 * scale)))
    font = load_font(FONT_KR, int(round(23 * scale)))
    centered_text(draw, (w / 2, y1 + box_h / 2 - int(1 * scale)), title, font, (255, 241, 190), 1, (28, 22, 18))


def draw_clean_route(base, theme, scale=1.0):
    w, h = base.size
    pts = [(int(round(w * x / 100)), int(round(h * y / 100))) for x, y in PIN_POSITIONS]
    route = Image.new("RGBA", base.size, (0, 0, 0, 0))
    rd = ImageDraw.Draw(route)
    road = (*theme["road"], 248)
    edge = (89, 62, 38, 128)
    rd.line(pts, fill=edge, width=int(round(122 * scale)), joint="curve")
    rd.line(pts, fill=road, width=int(round(108 * scale)), joint="curve")
    for x, y in pts:
        r = int(round(58 * scale))
        rd.ellipse((x - r, y - r, x + r, y + r), fill=road, outline=edge, width=max(1, int(2 * scale)))
    route = route.filter(ImageFilter.GaussianBlur(max(1, int(round(0.45 * scale)))))
    base.alpha_composite(route)


def cover_old_label_candidates(base, theme, scale=1.0):
    w, h = base.size
    src = base.convert("RGB")
    pix = src.load()
    mask = [[False] * w for _ in range(h)]
    for y in range(int(70 * scale), h):
        for x in range(w):
            r, g, b = pix[x, y]
            mask[y][x] = r < 112 and g < 96 and b < 82

    seen = [[False] * w for _ in range(h)]
    patches = []
    for y in range(int(70 * scale), h):
        for x in range(w):
            if not mask[y][x] or seen[y][x]:
                continue
            stack = [(x, y)]
            seen[y][x] = True
            xs, ys = [], []
            while stack:
                x1, y1 = stack.pop()
                xs.append(x1)
                ys.append(y1)
                for nx in (x1 - 1, x1, x1 + 1):
                    for ny in (y1 - 1, y1, y1 + 1):
                        if 0 <= nx < w and int(70 * scale) <= ny < h and mask[ny][nx] and not seen[ny][nx]:
                            seen[ny][nx] = True
                            stack.append((nx, ny))
            area = len(xs)
            bw = max(xs) - min(xs) + 1
            bh = max(ys) - min(ys) + 1
            ratio = bw / bh
            if 95 * scale < area < 2300 * scale and 11 * scale < bw < 58 * scale and 11 * scale < bh < 58 * scale and 0.5 < ratio < 1.9:
                patches.append((sum(xs) / area, sum(ys) / area, bw, bh))

    patch = Image.new("RGBA", base.size, (0, 0, 0, 0))
    pd = ImageDraw.Draw(patch)
    fill = (*theme["road"], 245)
    for cx, cy, bw, bh in patches:
        r = int(round(max(22 * scale, bw * 0.9, bh * 0.9)))
        pd.ellipse((cx - r, cy - r, cx + r, cy + r), fill=fill)
    patch = patch.filter(ImageFilter.GaussianBlur(max(1, int(round(0.65 * scale)))))
    base.alpha_composite(patch)


def fix_chapter_image(src, chapter_idx, dst=None):
    im = Image.open(src).convert("RGBA")
    theme = THEMES[chapter_idx]
    w, h = im.size
    scale = w / 307

    cover_old_label_candidates(im, theme, scale)
    draw_clean_route(im, theme, scale)
    draw_title(im, chapter_idx, theme, scale)

    if chapter_idx == 4:
        draw = ImageDraw.Draw(im)
        # Hide the stray "800" above the final node.
        draw.rounded_rectangle(
            (int(w * 0.38), int(h * 0.061), int(w * 0.61), int(h * 0.102)),
            radius=int(10 * scale),
            fill=(222, 232, 231, 190),
        )

    start = chapter_idx * 20 + 1
    for local, (px, py) in enumerate(PIN_POSITIONS):
        label = str(start + local)
        cx = int(round(w * px / 100))
        cy = int(round(h * py / 100))
        draw_badge(im, cx, cy, label, theme, scale)

    out = dst or src
    im.convert("RGB").save(out, quality=95)


def fix_combined_map():
    src = ASSETS / "map.png"
    im = Image.open(src).convert("RGBA")
    w, h = im.size
    for chapter_idx in range(5):
        x0 = int(round(w * chapter_idx / 5))
        x1 = int(round(w * (chapter_idx + 1) / 5))
        crop = im.crop((x0, 0, x1, h))
        tmp = ROOT / f".map_chapter_{chapter_idx + 1}.png"
        crop.convert("RGB").save(tmp)
        fix_chapter_image(tmp, chapter_idx, tmp)
        fixed = Image.open(tmp).convert("RGBA")
        im.alpha_composite(fixed, (x0, 0))
        tmp.unlink()
    im.convert("RGB").save(src, quality=95)


def recrop_chapters_from_source():
    CHAPTER_DIR.mkdir(parents=True, exist_ok=True)
    for path in CHAPTER_DIR.iterdir():
        if path.is_file():
            path.unlink()

    source = Image.open(SOURCE_MAP).convert("RGB")
    for chapter_idx, bounds in enumerate(CHAPTER_BOUNDS):
        crop = source.crop(bounds)
        if crop.size != OUTPUT_SIZE:
            crop = crop.resize(OUTPUT_SIZE, Image.Resampling.LANCZOS)
        out = CHAPTER_DIR / f"chapter{chapter_idx + 1}.png"
        crop.save(out, quality=95)
        fix_chapter_image(out, chapter_idx)


def main():
    recrop_chapters_from_source()


if __name__ == "__main__":
    main()
