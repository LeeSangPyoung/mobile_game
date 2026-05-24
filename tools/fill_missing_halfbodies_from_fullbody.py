#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import re
from pathlib import Path

from PIL import Image, ImageDraw, ImageOps


ROOT = Path(__file__).resolve().parents[1]
ROSTER_HTML = ROOT / "game_general_halfbody_200_final.html"
FULLBODY_DIR = ROOT / "assets/generals/busts"
TMP_DIR = ROOT / "tmp/halfbody_200"
SOURCE_DIR = TMP_DIR / "autofill_from_fullbody"
CUT_DIR = TMP_DIR / "cutout"
OUT_DIRS = [
    ROOT / "assets/generals/halfbodies",
    ROOT / "app/www/assets/generals/halfbodies",
]

CANVAS = (640, 768)
TARGET_WIDTH = 560
TARGET_MAX_HEIGHT = 690
TARGET_BOTTOM = 734


def load_roster() -> list[dict[str, object]]:
    text = ROSTER_HTML.read_text(encoding="utf-8")
    match = re.search(r"const roster\s*=\s*(\[[\s\S]*?\]);", text)
    if not match:
        raise SystemExit(f"could not find roster in {ROSTER_HTML}")
    return json.loads(match.group(1))


def alpha_bbox(image: Image.Image) -> tuple[int, int, int, int]:
    bbox = image.getchannel("A").getbbox()
    if not bbox:
        raise ValueError("source image has no visible pixels")
    return bbox


def estimate_focus_x(image: Image.Image, bbox: tuple[int, int, int, int]) -> int:
    left, top, right, bottom = bbox
    height = bottom - top
    band_top = max(0, int(top + height * 0.18))
    band_bottom = min(image.height, int(top + height * 0.60))
    alpha = image.getchannel("A")
    pix = alpha.load()
    xs: list[int] = []
    for y in range(band_top, band_bottom, 4):
        for x in range(left, right, 4):
            if pix[x, y] > 20:
                xs.append(x)
    if not xs:
        return (left + right) // 2
    xs.sort()
    return xs[len(xs) // 2]


def make_halfbody(source: Image.Image, crop_ratio: float = 0.68, width_factor: float = 0.70) -> Image.Image:
    source = source.convert("RGBA")
    left, top, right, bottom = alpha_bbox(source)
    width = right - left
    height = bottom - top
    center_x = estimate_focus_x(source, (left, top, right, bottom))

    crop_width = int(max(360, min(width, width * width_factor)))
    crop_left = max(0, center_x - crop_width // 2)
    crop_right = min(source.width, crop_left + crop_width)
    crop_left = max(0, crop_right - crop_width)
    crop_top = max(0, top - 4)
    crop_bottom = min(source.height, int(top + height * crop_ratio))

    crop = source.crop((crop_left, crop_top, crop_right, crop_bottom))
    crop_bbox = crop.getbbox()
    if not crop_bbox:
        raise ValueError("cropped halfbody has no visible pixels")

    # Preserve the horizontal crop frame so protruding weapons do not shrink the character.
    _, trim_top, _, trim_bottom = crop_bbox
    crop = crop.crop((0, trim_top, crop.width, trim_bottom))
    scaled_height = max(1, round(crop.height * TARGET_WIDTH / crop.width))
    crop = crop.resize((TARGET_WIDTH, scaled_height), Image.Resampling.LANCZOS)
    if crop.height > TARGET_MAX_HEIGHT:
        crop.thumbnail((TARGET_WIDTH, TARGET_MAX_HEIGHT), Image.Resampling.LANCZOS)

    out = Image.new("RGBA", CANVAS, (0, 0, 0, 0))
    x = (CANVAS[0] - crop.width) // 2
    y = max(20, TARGET_BOTTOM - crop.height)
    out.alpha_composite(crop, (x, y))
    return out


def write_contact_sheet(items: list[dict[str, object]], path: Path) -> None:
    columns = 5
    cell_w, cell_h = 190, 260
    rows = (len(items) + columns - 1) // columns
    sheet = Image.new("RGBA", (columns * cell_w, rows * cell_h), (8, 12, 18, 255))
    for index, item in enumerate(items):
        slug = str(item["id"])
        ko = str(item["ko"])
        src = OUT_DIRS[0] / f"{slug}.png"
        image = Image.open(src).convert("RGBA")
        bg = Image.new("RGBA", CANVAS, (18, 25, 35, 255))
        bg.alpha_composite(image)
        thumb = ImageOps.contain(bg, (cell_w, 225))
        tile = Image.new("RGBA", (cell_w, cell_h), (9, 13, 19, 255))
        tile.alpha_composite(thumb, ((cell_w - thumb.width) // 2, 0))
        draw = ImageDraw.Draw(tile)
        draw.text((7, 232), f"{int(item['no']):03d}. {ko}", fill=(235, 235, 235, 255))
        draw.text((7, 246), slug, fill=(170, 182, 196, 255))
        sheet.alpha_composite(tile, ((index % columns) * cell_w, (index // columns) * cell_h))
    path.parent.mkdir(parents=True, exist_ok=True)
    sheet.save(path)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--overwrite", action="store_true", help="regenerate existing halfbody files too")
    parser.add_argument("--no-contact", action="store_true", help="skip QA contact sheets")
    args = parser.parse_args()

    for directory in [SOURCE_DIR, CUT_DIR, *OUT_DIRS]:
        directory.mkdir(parents=True, exist_ok=True)

    roster = load_roster()
    generated: list[dict[str, object]] = []
    skipped = 0

    for item in roster:
        slug = str(item["id"])
        targets = [out_dir / f"{slug}.png" for out_dir in OUT_DIRS]
        if not args.overwrite and all(path.exists() for path in targets):
            skipped += 1
            continue

        source_path = FULLBODY_DIR / f"{slug}.png"
        if not source_path.exists():
            raise SystemExit(f"missing fullbody source: {source_path}")

        out = make_halfbody(Image.open(source_path))
        source_copy = SOURCE_DIR / f"{slug}.png"
        cut_copy = CUT_DIR / f"{slug}.png"
        out.save(source_copy)
        out.save(cut_copy)
        for target in targets:
            out.save(target)
        generated.append(item)

    if generated and not args.no_contact:
        for start in range(0, len(generated), 20):
            chunk = generated[start : start + 20]
            first = int(chunk[0]["no"])
            last = int(chunk[-1]["no"])
            write_contact_sheet(chunk, TMP_DIR / f"halfbody_{first:03d}_{last:03d}_contact.png")

    print(f"generated {len(generated)} halfbodies")
    print(f"skipped {skipped} existing halfbodies")


if __name__ == "__main__":
    main()
