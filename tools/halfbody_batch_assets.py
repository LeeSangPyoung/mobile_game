#!/usr/bin/env python3
from __future__ import annotations

import argparse
import ast
import shutil
from pathlib import Path

from PIL import Image, ImageDraw


ROOT = Path(__file__).resolve().parents[1]
GEN_DIR = Path.home() / ".codex/generated_images/019e6c2b-46e0-7b40-a2e4-9030a8ce8cf6"
REF_DIR = ROOT / "assets/generals/new_characters/front_gaze_200_v10_scale_audit"
STAGED_DIR = ROOT / "tmp/halfbody_v6_edit/staged"
SAMPLES_DIR = ROOT / "tmp/halfbody_v6_edit/samples"
ROSTER_JS = ROOT / "assets/generals/roster_200.js"


def load_roster() -> dict[str, str]:
    text = ROSTER_JS.read_text(encoding="utf-8")
    data = text.split("window.GENERALS_200 =", 1)[1].strip()
    if data.endswith(";"):
        data = data[:-1]
    return {str(slug): str(ko) for slug, ko in ast.literal_eval(data)}


def batch_dir(name: str) -> Path:
    out = SAMPLES_DIR / name
    out.mkdir(parents=True, exist_ok=True)
    return out


def save_latest(name: str, slug: str) -> None:
    out = batch_dir(name)
    latest = max(GEN_DIR.glob("*.png"), key=lambda p: p.stat().st_mtime)
    raw = out / f"{slug}_raw.png"
    raw.write_bytes(latest.read_bytes())
    print(raw, Image.open(raw).size)


def make_candidates(name: str, slugs: list[str], bottoms: list[int]) -> None:
    out = batch_dir(name)
    rows = []
    for slug in slugs:
        image = Image.open(out / f"{slug}_raw.png").convert("RGB")
        cards = []
        for bottom in bottoms:
            crop = image.crop((0, 0, image.width, min(bottom, image.height)))
            crop_path = out / f"{slug}_crop_{bottom}.png"
            crop.save(crop_path)
            thumb = crop.copy()
            thumb.thumbnail((140, 205), Image.Resampling.LANCZOS)
            card = Image.new("RGB", (155, 240), (18, 18, 18))
            card.paste(thumb, ((155 - thumb.width) // 2, 10))
            ImageDraw.Draw(card).text((5, 218), f"{slug} {bottom}", fill=(255, 230, 120))
            cards.append(card)
        row = Image.new("RGB", (155 * len(cards), 240), (8, 8, 8))
        for index, card in enumerate(cards):
            row.paste(card, (index * 155, 0))
        rows.append(row)
    sheet = Image.new("RGB", (155 * len(bottoms), 240 * len(rows)), (8, 8, 8))
    for index, row in enumerate(rows):
        sheet.paste(row, (0, index * 240))
    sheet_path = out / f"{name}_crop_candidates.jpg"
    sheet.save(sheet_path, quality=92)
    print(sheet_path)


def stage(name: str, choices: list[str]) -> None:
    out = batch_dir(name)
    roster = load_roster()
    STAGED_DIR.mkdir(parents=True, exist_ok=True)
    items: list[tuple[str, str, int]] = []
    for choice in choices:
        slug, raw_bottom = choice.split(":", 1)
        items.append((slug, roster.get(slug, slug), int(raw_bottom)))
    for slug, ko, bottom in items:
        src = out / f"{slug}_crop_{bottom}.png"
        final = out / f"{slug}.png"
        shutil.copy2(src, final)
        shutil.copy2(final, STAGED_DIR / f"{slug}_halfbody_redraw_v6.png")
        print(slug, ko, bottom, Image.open(final).size)

    preview_cards = []
    for slug, ko, _ in items:
        image = Image.open(out / f"{slug}.png").convert("RGB")
        thumb = image.copy()
        thumb.thumbnail((230, 320), Image.Resampling.LANCZOS)
        card = Image.new("RGB", (250, 370), (18, 18, 18))
        card.paste(thumb, ((250 - thumb.width) // 2, 14))
        ImageDraw.Draw(card).text((8, 340), f"{ko} {slug}", fill=(255, 230, 120))
        preview_cards.append(card)
    cols = 5
    rows = (len(preview_cards) + cols - 1) // cols
    preview = Image.new("RGB", (cols * 250, rows * 370), (10, 10, 10))
    for index, card in enumerate(preview_cards):
        preview.paste(card, ((index % cols) * 250, (index // cols) * 370))
    preview_path = out / f"{name}_final_preview.jpg"
    preview.save(preview_path, quality=92)

    compare_rows = []
    for slug, ko, bottom in items:
        ref = Image.open(REF_DIR / f"{slug}_front_gaze_v1.png").convert("RGB")
        new = Image.open(out / f"{slug}.png").convert("RGB")
        ref_thumb = ref.copy()
        new_thumb = new.copy()
        ref_thumb.thumbnail((260, 380), Image.Resampling.LANCZOS)
        new_thumb.thumbnail((260, 380), Image.Resampling.LANCZOS)
        row = Image.new("RGB", (600, 430), (16, 16, 16))
        row.paste(ref_thumb, ((280 - ref_thumb.width) // 2, 32))
        row.paste(new_thumb, (320 + (260 - new_thumb.width) // 2, 32))
        draw = ImageDraw.Draw(row)
        draw.text((10, 10), f"{ko} {slug} reference", fill=(220, 220, 220))
        draw.text((320, 10), f"strict belt-under {bottom}", fill=(255, 230, 120))
        compare_rows.append(row)
    compare = Image.new("RGB", (600, 430 * len(compare_rows)), (10, 10, 10))
    for index, row in enumerate(compare_rows):
        compare.paste(row, (0, index * 430))
    compare_path = out / f"{name}_compare.jpg"
    compare.save(compare_path, quality=92)
    print("preview", preview_path)
    print("compare", compare_path)


def main() -> None:
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers(dest="command", required=True)
    save = sub.add_parser("save-latest")
    save.add_argument("batch")
    save.add_argument("slug")
    candidates = sub.add_parser("candidates")
    candidates.add_argument("batch")
    candidates.add_argument("slugs", nargs="+")
    candidates.add_argument("--bottoms", default="900,960,1020,1080,1140,1200,1260")
    stage_parser = sub.add_parser("stage")
    stage_parser.add_argument("batch")
    stage_parser.add_argument("choices", nargs="+")
    args = parser.parse_args()
    if args.command == "save-latest":
        save_latest(args.batch, args.slug)
    elif args.command == "candidates":
        make_candidates(args.batch, args.slugs, [int(value) for value in args.bottoms.split(",")])
    elif args.command == "stage":
        stage(args.batch, args.choices)


if __name__ == "__main__":
    main()
