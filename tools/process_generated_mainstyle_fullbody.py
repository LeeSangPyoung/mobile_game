#!/usr/bin/env python3
from __future__ import annotations

import argparse
import shutil
from pathlib import Path

from PIL import Image


ROOT = Path(__file__).resolve().parents[1]
GENERATED_ROOT = Path.home() / ".codex/generated_images"
WORK_DIR = ROOT / "tmp/generated_mainstyle_fullbody"
RAW_DIR = WORK_DIR / "raw"
CUT_DIR = WORK_DIR / "cutout"
OUT_DIR = ROOT / "assets/generals/generated_fullbody_mainstyle"
CANVAS = (640, 768)


def latest_generated_png() -> Path:
    files = [path for path in GENERATED_ROOT.rglob("*.png") if path.is_file()]
    if not files:
        raise SystemExit(f"no generated pngs under {GENERATED_ROOT}")
    return max(files, key=lambda path: path.stat().st_mtime)


def remove_magenta_key(image: Image.Image) -> Image.Image:
    image = image.convert("RGBA")
    pix = image.load()
    width, height = image.size
    for y in range(height):
        for x in range(width):
            r, g, b, a = pix[x, y]
            is_key = r > 185 and b > 150 and g < 120 and r - g > 75 and b - g > 70
            near_key = r > 145 and b > 120 and g < 155 and r - g > 42 and b - g > 38
            if is_key:
                pix[x, y] = (r, g, b, 0)
            elif near_key:
                pix[x, y] = (r, g, b, 110)
            else:
                pix[x, y] = (r, g, b, 255 if a else 0)
    return image


def normalize_fullbody(image: Image.Image) -> Image.Image:
    image = remove_magenta_key(image)
    bbox = image.getbbox()
    if not bbox:
        raise ValueError("empty alpha after key removal")
    crop = image.crop(bbox)
    crop.thumbnail((600, 736), Image.Resampling.LANCZOS)
    out = Image.new("RGBA", CANVAS, (0, 0, 0, 0))
    x = (CANVAS[0] - crop.width) // 2
    y = max(8, CANVAS[1] - crop.height - 18)
    out.alpha_composite(crop, (x, y))
    return out


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("slug")
    parser.add_argument("--source", type=Path)
    args = parser.parse_args()

    source = args.source or latest_generated_png()
    RAW_DIR.mkdir(parents=True, exist_ok=True)
    CUT_DIR.mkdir(parents=True, exist_ok=True)
    OUT_DIR.mkdir(parents=True, exist_ok=True)

    raw_path = RAW_DIR / f"{args.slug}.png"
    cut_path = CUT_DIR / f"{args.slug}.png"
    out_path = OUT_DIR / f"{args.slug}.png"
    shutil.copy2(source, raw_path)
    output = normalize_fullbody(Image.open(raw_path))
    output.save(cut_path)
    output.save(out_path)
    print(out_path)
    print(raw_path)


if __name__ == "__main__":
    main()
