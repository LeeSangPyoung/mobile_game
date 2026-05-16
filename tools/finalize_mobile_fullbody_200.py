#!/usr/bin/env python3
from __future__ import annotations

import json
from collections import deque
from pathlib import Path

from PIL import Image


ROOT = Path(__file__).resolve().parents[1]
TMP = ROOT / "tmp" / "mobile_generals_200"
RAW = TMP / "raw"
FINAL = ROOT / "assets" / "generals" / "mobile_fullbody"


def remove_chroma_background(image: Image.Image) -> Image.Image:
    im = image.convert("RGBA")
    pix = im.load()
    width, height = im.size
    seen: set[tuple[int, int]] = set()
    q: deque[tuple[int, int]] = deque()

    border = []
    step = max(1, min(width, height) // 80)
    for x in range(0, width, step):
      border.append(pix[x, 0][:3])
      border.append(pix[x, height - 1][:3])
    for y in range(0, height, step):
      border.append(pix[0, y][:3])
      border.append(pix[width - 1, y][:3])
    key = tuple(sorted(channel)[len(channel) // 2] for channel in zip(*border))

    def color_distance(rgb: tuple[int, int, int], other: tuple[int, int, int]) -> int:
        return sum(abs(a - b) for a, b in zip(rgb, other))

    def is_key(x: int, y: int) -> bool:
        r, g, b, a = pix[x, y]
        if a == 0:
            return False
        kr, kg, kb = key
        is_green_key = kg > kr + 35 and kg > kb + 35
        is_magenta_key = kr > kg + 35 and kb > kg + 35
        threshold = 96 if is_green_key or is_magenta_key else 72
        return color_distance((r, g, b), key) <= threshold

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
        pix[x, y] = (pix[x, y][0], pix[x, y][1], pix[x, y][2], 0)
        for nx, ny in ((x + 1, y), (x - 1, y), (x, y + 1), (x, y - 1)):
            if 0 <= nx < width and 0 <= ny < height and (nx, ny) not in seen and is_key(nx, ny):
                seen.add((nx, ny))
                q.append((nx, ny))

    # Remove tiny chroma-key islands trapped between limbs or weapons.
    for y in range(height):
        for x in range(width):
            r, g, b, a = pix[x, y]
            if a > 0 and color_distance((r, g, b), key) <= 42:
                pix[x, y] = (r, g, b, 0)
    return im


def fit_to_canvas(image: Image.Image, size: tuple[int, int] = (640, 768)) -> Image.Image:
    bbox = image.getchannel("A").getbbox()
    if not bbox:
        return Image.new("RGBA", size, (0, 0, 0, 0))
    crop = image.crop(bbox)
    crop.thumbnail((int(size[0] * 0.92), int(size[1] * 0.94)), Image.Resampling.LANCZOS)
    out = Image.new("RGBA", size, (0, 0, 0, 0))
    x = (size[0] - crop.width) // 2
    y = size[1] - crop.height - 16
    out.alpha_composite(crop, (x, max(0, y)))
    return out


def main() -> None:
    manifest = json.loads((TMP / "manifest.json").read_text(encoding="utf-8"))
    FINAL.mkdir(parents=True, exist_ok=True)
    written = 0
    missing = []
    empty_alpha = []

    for item in manifest["items"]:
        slug = item["slug"]
        src = RAW / f"{slug}.png"
        if not src.exists():
            missing.append(slug)
            continue
        dest = FINAL / f"{slug}.png"
        if dest.exists() and dest.stat().st_mtime >= src.stat().st_mtime:
            written += 1
            continue
        image = fit_to_canvas(remove_chroma_background(Image.open(src)))
        if not image.getchannel("A").getbbox():
            empty_alpha.append(slug)
        image.save(dest)
        written += 1

    print(f"written: {written}")
    print(f"missing: {len(missing)}")
    print(f"empty_alpha: {len(empty_alpha)}")
    if missing:
        print("first_missing:", ", ".join(missing[:20]))
    if empty_alpha:
        print("first_empty_alpha:", ", ".join(empty_alpha[:20]))


if __name__ == "__main__":
    main()
