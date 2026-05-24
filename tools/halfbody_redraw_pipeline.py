#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import re
import shutil
from pathlib import Path

from PIL import Image, ImageDraw, ImageOps


ROOT = Path(__file__).resolve().parents[1]
ROSTER_HTML = ROOT / "game_general_halfbody_200_final.html"
FULLBODY_DIR = ROOT / "assets/generals/busts"
WORK_DIR = ROOT / "tmp/halfbody_200_redraw"
RAW_DIR = WORK_DIR / "raw"
CUT_DIR = WORK_DIR / "cutout"
PROMPT_DIR = WORK_DIR / "prompts"
OUT_DIRS = [
    ROOT / "assets/generals/halfbodies",
    ROOT / "app/www/assets/generals/halfbodies",
]
GENERATED_ROOT = Path.home() / ".codex/generated_images"


FEMALE = {
    "real_xin_xianying",
    "real_lady_zhurong",
}
SCHOLAR_HINTS = {
    "zhuge_liang",
    "pang_tong",
    "guo_jia",
    "sima_yi",
    "zhou_yu",
    "lu_xun",
    "real_jia_xu",
    "real_xun_yu",
    "real_xun_you",
    "real_cheng_yu",
    "real_lu_su",
    "real_fa_zheng",
    "real_chen_gong",
    "real_zhang_zhao",
    "real_zhang_hong",
    "real_wang_lang",
    "real_xin_pi",
    "real_yu_fan",
    "real_lu_kai",
    "real_jiang_wan",
    "real_qiao_zhou",
    "real_wang_fu",
    "real_mi_zhu",
    "real_yi_ji",
    "real_tao_qian",
    "real_kong_rong",
    "real_wang_yun",
    "real_lu_zhi",
}
HEAVY_HINTS = {
    "zhang_fei",
    "dian_wei",
    "xu_chu",
    "wen_chou",
    "yan_liang",
    "meng_huo",
    "real_hua_xiong",
    "real_pang_de",
    "real_wang_shuang",
    "real_zhou_tai",
    "real_pan_zhang",
    "real_he_jin",
    "real_yan_baihu",
}

EXPRESSIONS = [
    "gentle confident smile",
    "stern angry glare with clenched jaw",
    "big hearty laugh",
    "quiet sad eyes with a restrained mouth",
    "surprised alert expression with raised brows",
    "cool heroic half-smile",
    "calm serious strategist expression",
    "playful teasing grin",
    "fierce battle-ready scowl",
    "warm reassuring smile",
]

POSES = [
    "shoulders angled left, head tilted right, high collar flaring on one side",
    "shoulders angled right, chin slightly lifted, cloak collar framing the face",
    "one shoulder raised as if leaning into a portrait pose, head slightly lowered",
    "square shoulders with the head turned in three-quarter angle, armor plates asymmetrical",
    "dramatic cloak collar sweeping behind one shoulder, head tilted with confidence",
    "compact heroic bust pose with one shoulder closer to camera, crown centered",
    "subtle twist through the upper chest, face turned back toward the viewer",
    "formal noble portrait posture, shoulders calm but not straight-on",
    "dynamic chest portrait with armor silhouette slanting diagonally",
    "quiet introspective pose with chin tucked slightly and shoulders offset",
]


def load_roster() -> list[dict[str, object]]:
    text = ROSTER_HTML.read_text(encoding="utf-8")
    match = re.search(r"const roster\s*=\s*(\[[\s\S]*?\]);", text)
    if not match:
        raise SystemExit(f"could not find roster in {ROSTER_HTML}")
    return json.loads(match.group(1))


def role_line(slug: str) -> str:
    if slug in FEMALE:
        return "Role read: female general, strong heroine presence, elegant but battle-ready."
    if slug in SCHOLAR_HINTS:
        return "Role read: strategist or court commander, composed expression, robe armor and command prop are welcome."
    if slug in HEAVY_HINTS:
        return "Role read: heavy warrior, broad upper body, powerful shoulders, stern battle presence."
    return "Role read: field commander, confident martial bearing, readable armor silhouette."


def prompt_for(item: dict[str, object]) -> str:
    slug = str(item["id"])
    ko = str(item["ko"])
    no = int(item["no"])
    expression = EXPRESSIONS[(no - 1) % len(EXPRESSIONS)]
    pose = POSES[(no - 1) % len(POSES)]
    return f"""Use case: stylized-concept
Asset type: production mobile game head-to-chest character portrait source on chroma-key background.
Primary request: Create ONE newly drawn head-to-chest portrait for the Three Kingdoms general {ko} ({slug}).
Reference requirement: use the provided full-body character image ONLY as the identity, costume, color, and design reference. Preserve the same character identity, face shape, hair, helmet/crown, armor language, faction colors, weapon/prop cues, and overall mobile game style from that reference. This portrait must clearly be the matching pair for that exact full-body asset, but it must not copy the full-body pose or look like a cropped full-body image.
{role_line(slug)}
Strict shot range: head to upper chest only. Show crown/head, face, neck, robe collar, shoulders, and upper chest armor. Do not show abdomen, stomach, waist, belt, belt ornament, hips, legs, boots, full weapon, or full torso.
Gaze rule: the pupils must look directly at the viewer / camera. Direct eye contact is required. Face angle, head tilt, and shoulders can vary, but the eyes must not look left, right, up, or down.
Expression plan for this character: {expression}.
Pose plan for this character: {pose}. Make this pose different from the full-body reference.
Art direction: polished casual mobile RPG SD character illustration, same universe as the full-body set. Large expressive head, compact heroic proportions, rounded chunky armor forms, clean eyes, crisp face, premium game asset finish. Add only 10% subtle Roblox-inspired friendliness: slightly rounder cheeks, clean simple facial planes, approachable toy-like charm, but not a blocky Roblox avatar.
Composition: tight head-to-upper-chest portrait, centered, face large in frame, shoulders visible, crop ends high at upper chest. Leave generous padding around hair/crown, shoulder armor, and collar. Card-portrait friendly silhouette.
Pose rule: make a fresh portrait illustration, not a crop of the full-body. Avoid repeating the full-body stance. Vary shoulders, head angle, collar/cloak silhouette, and expression across the set.
Backdrop: perfectly flat solid #ff00ff chroma-key background only. The background must be one uniform color with no shadows, gradients, floor, texture, reflections, or lighting variation.
Hard reject constraints: no text, no labels, no watermark, no frame, no UI, no environmental background, no cast shadow, no cropped crown/head, no cropped shoulders, no magenta anywhere on the character, no photorealism, no tall realistic proportions, no thin anime body, no excessive armor noise, no changing the character into a different person, no full-body crop feeling, no copied pose, no gaze away from viewer.
Quality target: clean face, strong match to the reference full-body, consistent 200-character set style, readable at small mobile size."""


def latest_generated_png() -> Path:
    files = [p for p in GENERATED_ROOT.rglob("*.png") if p.is_file()]
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
            is_key = r > 185 and b > 155 and g < 120 and r - g > 75 and b - g > 70
            near_key = r > 150 and b > 125 and g < 150 and r - g > 45 and b - g > 40
            if is_key:
                pix[x, y] = (r, g, b, 0)
            elif near_key:
                pix[x, y] = (r, g, b, 128)
            else:
                pix[x, y] = (r, g, b, 255 if a else 0)
    return image


def normalize_halfbody(image: Image.Image) -> Image.Image:
    image = remove_magenta_key(image)
    bbox = image.getbbox()
    if not bbox:
        raise ValueError("empty alpha after chroma-key removal")
    left, top, right, bottom = bbox
    crop_bottom = min(bottom, int(top + (bottom - top) * 0.70))
    crop = image.crop((left, top, right, crop_bottom))
    crop_bbox = crop.getbbox()
    if crop_bbox:
        crop = crop.crop(crop_bbox)
    crop.thumbnail((560, 690), Image.Resampling.LANCZOS)
    out = Image.new("RGBA", (640, 768), (0, 0, 0, 0))
    x = (640 - crop.width) // 2
    y = max(20, 734 - crop.height)
    out.alpha_composite(crop, (x, y))
    return out


def write_prompt_files() -> None:
    PROMPT_DIR.mkdir(parents=True, exist_ok=True)
    jobs = []
    for item in load_roster():
        slug = str(item["id"])
        source = FULLBODY_DIR / f"{slug}.png"
        if not source.exists():
            raise SystemExit(f"missing full-body reference: {source}")
        prompt = prompt_for(item)
        prompt_path = PROMPT_DIR / f"{int(item['no']):03d}_{slug}.txt"
        prompt_path.write_text(prompt, encoding="utf-8")
        jobs.append(
            {
                "no": item["no"],
                "id": slug,
                "ko": item["ko"],
                "reference": str(source),
                "prompt": str(prompt_path),
                "output": str(OUT_DIRS[0] / f"{slug}.png"),
            }
        )
    (WORK_DIR / "jobs.json").write_text(json.dumps(jobs, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"wrote {len(jobs)} prompts to {PROMPT_DIR}")
    print(WORK_DIR / "jobs.json")


def process_image(slug: str, source: Path | None) -> None:
    RAW_DIR.mkdir(parents=True, exist_ok=True)
    CUT_DIR.mkdir(parents=True, exist_ok=True)
    for out_dir in OUT_DIRS:
        out_dir.mkdir(parents=True, exist_ok=True)

    latest = source or latest_generated_png()
    raw_path = RAW_DIR / f"{slug}.png"
    cut_path = CUT_DIR / f"{slug}.png"
    shutil.copy2(latest, raw_path)
    out = normalize_halfbody(Image.open(raw_path))
    out.save(cut_path)
    for out_dir in OUT_DIRS:
        out.save(out_dir / f"{slug}.png")
    print(f"saved {slug} from {latest}")


def status() -> None:
    roster = load_roster()
    for out_dir in OUT_DIRS:
        present = sum(1 for item in roster if (out_dir / f"{item['id']}.png").exists())
        print(f"{out_dir}: {present}/{len(roster)}")


def contact_sheet() -> None:
    roster = [item for item in load_roster() if (OUT_DIRS[0] / f"{item['id']}.png").exists()]
    if not roster:
        print("no generated halfbodies yet")
        return
    columns = 5
    cell_w, cell_h = 190, 260
    rows = (len(roster) + columns - 1) // columns
    sheet = Image.new("RGBA", (columns * cell_w, rows * cell_h), (8, 12, 18, 255))
    for index, item in enumerate(roster):
        slug = str(item["id"])
        image = Image.open(OUT_DIRS[0] / f"{slug}.png").convert("RGBA")
        bg = Image.new("RGBA", (640, 768), (18, 25, 35, 255))
        bg.alpha_composite(image)
        thumb = ImageOps.contain(bg, (cell_w, 225))
        tile = Image.new("RGBA", (cell_w, cell_h), (9, 13, 19, 255))
        tile.alpha_composite(thumb, ((cell_w - thumb.width) // 2, 0))
        draw = ImageDraw.Draw(tile)
        draw.text((7, 232), f"{int(item['no']):03d}. {item['ko']}", fill=(235, 235, 235, 255))
        draw.text((7, 246), slug, fill=(170, 182, 196, 255))
        sheet.alpha_composite(tile, ((index % columns) * cell_w, (index // columns) * cell_h))
    out_path = WORK_DIR / "redraw_contact_current.png"
    out_path.parent.mkdir(parents=True, exist_ok=True)
    sheet.save(out_path)
    print(out_path)


def main() -> None:
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("write-prompts")
    process = sub.add_parser("process")
    process.add_argument("slug")
    process.add_argument("--source", type=Path)
    sub.add_parser("status")
    sub.add_parser("contact-sheet")
    args = parser.parse_args()

    if args.command == "write-prompts":
        write_prompt_files()
    elif args.command == "process":
        process_image(args.slug, args.source)
    elif args.command == "status":
        status()
    elif args.command == "contact-sheet":
        contact_sheet()


if __name__ == "__main__":
    main()
