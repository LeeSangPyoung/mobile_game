#!/usr/bin/env python3
from __future__ import annotations

import shutil
import sys
from pathlib import Path

from PIL import Image


ROOT = Path(__file__).resolve().parents[1]
GEN_DIR = Path("/Users/leesp/.codex/generated_images/019e3696-2f37-77a1-86e6-9cc70a6119a3")
RAW_DIR = ROOT / "tmp/halfbody_200/raw"
CUT_DIR = ROOT / "tmp/halfbody_200/cutout"
OUT_DIRS = [
    ROOT / "assets/generals/halfbodies",
    ROOT / "app/www/assets/generals/halfbodies",
]


def main() -> None:
    if len(sys.argv) != 2:
        raise SystemExit("usage: process_latest_halfbody.py <slug>")
    slug = sys.argv[1]
    latest = max(GEN_DIR.glob("*.png"), key=lambda path: path.stat().st_mtime)

    RAW_DIR.mkdir(parents=True, exist_ok=True)
    CUT_DIR.mkdir(parents=True, exist_ok=True)
    for out_dir in OUT_DIRS:
        out_dir.mkdir(parents=True, exist_ok=True)

    raw_path = RAW_DIR / f"{slug}.png"
    cut_path = CUT_DIR / f"{slug}.png"
    shutil.copy2(latest, raw_path)

    image = remove_magenta_key(Image.open(raw_path).convert("RGBA"))
    image.save(cut_path)
    bbox = image.getbbox()
    if not bbox:
        raise SystemExit(f"empty alpha: {slug}")
    crop = image.crop(bbox)
    crop.thumbnail((560, 690), Image.Resampling.LANCZOS)

    out = Image.new("RGBA", (640, 768), (0, 0, 0, 0))
    x = (640 - crop.width) // 2
    y = max(20, 768 - crop.height - 34)
    out.alpha_composite(crop, (x, y))

    for out_dir in OUT_DIRS:
        out.save(out_dir / f"{slug}.png")

    print(f"saved {slug} {out.getbbox()} from {latest.name}")


def remove_magenta_key(image: Image.Image) -> Image.Image:
    pix = image.load()
    width, height = image.size
    for y in range(height):
        for x in range(width):
            r, g, b, a = pix[x, y]
            is_key = r > 185 and b > 145 and g < 115 and r - g > 85 and b - g > 75
            near_key = r > 150 and b > 120 and g < 145 and r - g > 55 and b - g > 45
            if is_key:
                pix[x, y] = (r, g, b, 0)
            elif near_key:
                # Preserve original RGB to avoid the face/armor color damage that despill caused.
                pix[x, y] = (r, g, b, 180)
            else:
                pix[x, y] = (r, g, b, 255)
    return image


if __name__ == "__main__":
    main()
