from __future__ import annotations

import json
from pathlib import Path
from collections import deque

from PIL import Image


ROOT = Path(__file__).resolve().parents[1]
TMP = ROOT / "tmp" / "real_generals_170"
RAW = TMP / "raw" / "busts"
FINAL = ROOT / "assets" / "generals" / "busts_real_170"


def remove_green_background(image: Image.Image) -> Image.Image:
    im = image.convert("RGBA")
    pix = im.load()
    width, height = im.size
    seen: set[tuple[int, int]] = set()
    q: deque[tuple[int, int]] = deque()

    def is_key(x: int, y: int) -> bool:
        r, g, b, a = pix[x, y]
        return a > 0 and g >= 145 and r <= 125 and b <= 135 and g >= r + 42 and g >= b + 42

    for x in range(width):
        for y in (0, height - 1):
            if is_key(x, y):
                seen.add((x, y))
                q.append((x, y))
    for y in range(height):
        for x in (0, width - 1):
            if is_key(x, y) and (x, y) not in seen:
                seen.add((x, y))
                q.append((x, y))

    while q:
        x, y = q.popleft()
        pix[x, y] = (*pix[x, y][:3], 0)
        for nx, ny in ((x + 1, y), (x - 1, y), (x, y + 1), (x, y - 1)):
            if 0 <= nx < width and 0 <= ny < height and (nx, ny) not in seen and is_key(nx, ny):
                seen.add((nx, ny))
                q.append((nx, ny))
    return im


def fit_to_canvas(image: Image.Image, size: tuple[int, int] = (640, 768)) -> Image.Image:
    bbox = image.getchannel("A").getbbox()
    if not bbox:
        return Image.new("RGBA", size, (0, 0, 0, 0))
    crop = image.crop(bbox)
    max_w, max_h = int(size[0] * 0.92), int(size[1] * 0.94)
    crop.thumbnail((max_w, max_h), Image.Resampling.LANCZOS)
    out = Image.new("RGBA", size, (0, 0, 0, 0))
    x = (size[0] - crop.width) // 2
    y = size[1] - crop.height - 16
    out.alpha_composite(crop, (x, max(0, y)))
    return out


def main() -> None:
    manifest = json.loads((TMP / "manifest.json").read_text(encoding="utf-8"))
    FINAL.mkdir(parents=True, exist_ok=True)
    missing = []
    written = 0
    bad_alpha = []
    for item in manifest["items"]:
        slug = item["slug"]
        src = RAW / f"{slug}.png"
        if not src.exists():
            missing.append(str(src))
            continue
        image = fit_to_canvas(remove_green_background(Image.open(src)))
        if not image.getchannel("A").getbbox():
            bad_alpha.append(slug)
        image.save(FINAL / f"{slug}.png")
        written += 1
    print(f"written: {written}")
    print(f"missing: {len(missing)}")
    print(f"bad_alpha: {len(bad_alpha)}")
    if missing:
        print("first_missing:")
        for path in missing[:12]:
            print(path)
    if bad_alpha:
        print("first_bad_alpha:")
        for slug in bad_alpha[:12]:
            print(slug)


if __name__ == "__main__":
    main()
