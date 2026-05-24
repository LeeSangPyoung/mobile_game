#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import re
import shutil
from datetime import datetime
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont, ImageOps


ROOT = Path(__file__).resolve().parents[1]
ROSTER_HTML = ROOT / "game_general_halfbody_200_final.html"
IDENTITY_DIR = ROOT / "assets/generals/busts"
STYLE_REF_PRIMARY = ROOT / "assets/main_keyart_reference.png"
STYLE_REF_SINGLE = ROOT / "assets/generals/style_refs/mainstyle_single_general_01.png"
WORK_DIR = ROOT / "tmp/mainstyle_halfbody_200"
RAW_DIR = WORK_DIR / "raw"
CUT_DIR = WORK_DIR / "cutout"
PROMPT_DIR = WORK_DIR / "prompts"
JOBS_JSONL = WORK_DIR / "jobs.jsonl"
MANIFEST_JSON = WORK_DIR / "manifest.json"
GENERATED_ROOT = Path.home() / ".codex/generated_images"
OUT_DIRS = [
    ROOT / "assets/generals/halfbodies",
    ROOT / "app/www/assets/generals/halfbodies",
]


FEMALE = {
    "real_xin_xianying",
    "real_lady_zhurong",
}

STRATEGIST = {
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

HEAVY = {
    "zhang_fei",
    "dian_wei",
    "xu_chu",
    "wen_chou",
    "yan_liang",
    "meng_huo",
    "dong_zhuo",
    "real_hua_xiong",
    "real_pang_de",
    "real_wang_shuang",
    "real_zhou_tai",
    "real_pan_zhang",
    "real_he_jin",
    "real_yan_baihu",
}

CAVALRY = {
    "lu_bu",
    "zhao_yun",
    "ma_chao",
    "zhang_liao",
    "taishi_ci",
    "sun_ce",
    "real_ma_teng",
    "real_ma_dai",
    "real_han_sui",
    "real_xiahou_yuan",
    "real_wen_yang",
}

RULER = {
    "liu_bei",
    "cao_cao",
    "sun_quan",
    "yuan_shao",
    "dong_zhuo",
    "real_sun_jian",
    "real_cao_pi",
    "real_cao_rui",
    "real_yuan_shu",
    "real_gongsun_zan",
    "real_liu_biao",
    "real_liu_zhang",
}

EXPRESSIONS = [
    "stern commander glare with clenched jaw",
    "calm heroic half-smile",
    "fierce battle-ready scowl",
    "wise strategist gaze with quiet confidence",
    "proud noble expression with lifted chin",
    "older veteran intensity with narrowed eyes",
    "warm but commanding smile",
    "cold calculating stare",
]

POSES = [
    "shoulders angled left, head turned back toward camera, high collar framing the jaw",
    "shoulders angled right, chin slightly lifted, cape collar rising behind one shoulder",
    "square heroic shoulders with one gauntlet near the chest armor",
    "three-quarter bust twist with one shoulder closer to camera",
    "formal command portrait posture with asymmetric armor plates",
    "compact forward lean, broad shoulder guards creating a strong triangular silhouette",
    "quiet strategist pose with robe collar and command prop visible near the chest",
    "battlefield challenge pose with weapon haft crossing behind the shoulder",
]


def load_roster() -> list[dict[str, object]]:
    text = ROSTER_HTML.read_text(encoding="utf-8")
    match = re.search(r"const roster\s*=\s*(\[[\s\S]*?\]);", text)
    if not match:
        raise SystemExit(f"could not find roster in {ROSTER_HTML}")
    roster = json.loads(match.group(1))
    if len(roster) != 200:
        raise SystemExit(f"expected 200 roster items, got {len(roster)}")
    return roster


def role_line(slug: str) -> str:
    if slug in FEMALE:
        return "Role read: heroine commander, elegant but battle-ready, strong eyes, ornate hairpiece or crown armor."
    if slug in STRATEGIST:
        return "Role read: strategist or court commander, composed eyes, robe armor, command fan/tablet/scroll cues are welcome."
    if slug in HEAVY:
        return "Role read: heavy warrior, broad shoulders, thick neck, powerful armored mass, fierce battlefield presence."
    if slug in CAVALRY:
        return "Role read: cavalry hero, plumed helmet or flowing hair, energetic cape, long weapon cue near the shoulder."
    if slug in RULER:
        return "Role read: ruler or supreme commander, dignified face, premium crown/helmet, commanding upper-body silhouette."
    return "Role read: field commander, confident martial bearing, readable armor silhouette."


def prompt_for(item: dict[str, object]) -> str:
    slug = str(item["id"])
    ko = str(item["ko"])
    no = int(item["no"])
    expression = EXPRESSIONS[(no - 1) % len(EXPRESSIONS)]
    pose = POSES[(no - 1) % len(POSES)]

    return f"""Use case: stylized-concept
Asset type: production mobile game half-body character cutout on chroma-key background.
Primary request: Redraw ONE original Three Kingdoms general half-body portrait for {ko} ({slug}) in the new main-screen key-art style.
Input images: use the character reference image only for identity, costume, faction color, face/hair/helmet/armor cues, and signature props. Use the main key-art references only for the overall rendering style, material finish, heroic toy proportions, warm battlefield lighting, and ornate commander mood.
{role_line(slug)}
Style lock: match the main screen direction: premium 3D collectible warlord figure, blocky stylized square head, sturdy compact body, thick expressive eyebrows, chunky hands, glossy painted-plastic face, layered lamellar armor, metallic gold trims, engraved dragon/crest ornaments, rich red/green/blue/black faction cloth, smoky orange rim light, heroic commander presence. It should feel like the single-character version of the main battlefield art.
Shot range: half-body / waist-up portrait only. Show full crown or helmet, face, beard/hair, neck, shoulders, upper chest armor, cape collar, and a small upper weapon or command prop cue if useful. Do not show feet, boots, legs, full body, full weapon, or distant scenery.
Identity requirement: preserve the existing character's recognizable identity from the reference image. Keep the same broad color family, role, age read, hair/beard logic, helmet/crown language, armor style, and signature prop cues. Improve the character into the new key-art style rather than inventing a different person.
Gaze rule: direct eye contact with the viewer is required. Face angle may vary, but pupils must not look away.
Expression plan for this character: {expression}.
Pose plan for this character: {pose}. Make this pose different from the reference image.
Composition: single character centered, large readable face, shoulders and armor filling the lower frame, strong silhouette, generous padding around crown, hair, shoulder armor, cape, and prop. Designed for a 640x768 transparent PNG game asset.
Lighting/material: cinematic warm firelight and gold rim highlights on armor, but keep the subject isolated cleanly for UI use. Use detailed metal and cloth materials without becoming noisy at small mobile size.
Backdrop: perfectly flat solid #ff00ff chroma-key background only. The background must be one uniform color with no shadows, gradients, smoke, floor, texture, flags, reflections, or lighting variation.
Hard reject constraints: exactly one character, no extra soldiers, no horse, no environmental background, no text, no labels, no watermark, no frame, no UI, no cast shadow, no cropped head/crown/shoulders, no magenta anywhere on the character, no photorealistic human proportions, no generic anime style, no plain historical painting style, no thin body, no fully cubic Roblox avatar, no copied pose, no gaze away from viewer.
Quality target: crisp eyes, clean face, premium mobile game finish, consistent 200-character set style, strong match to the reference identity, and the same emotional impact as the main screen art."""


def reference_paths() -> list[str]:
    refs = [STYLE_REF_PRIMARY]
    if STYLE_REF_SINGLE.exists():
        refs.append(STYLE_REF_SINGLE)
    return [str(path) for path in refs if path.exists()]


def load_font(size: int) -> ImageFont.ImageFont:
    candidates = [
        Path("/System/Library/Fonts/AppleSDGothicNeo.ttc"),
        Path("/System/Library/Fonts/Supplemental/AppleGothic.ttf"),
        Path("/Library/Fonts/Arial Unicode.ttf"),
    ]
    for path in candidates:
        if not path.exists():
            continue
        try:
            return ImageFont.truetype(str(path), size)
        except OSError:
            continue
    return ImageFont.load_default()


def write_prompt_files() -> None:
    PROMPT_DIR.mkdir(parents=True, exist_ok=True)
    WORK_DIR.mkdir(parents=True, exist_ok=True)
    style_refs = reference_paths()
    jobs = []

    for item in load_roster():
        slug = str(item["id"])
        source = IDENTITY_DIR / f"{slug}.png"
        if not source.exists():
            raise SystemExit(f"missing identity reference: {source}")

        prompt = prompt_for(item)
        prompt_path = PROMPT_DIR / f"{int(item['no']):03d}_{slug}.txt"
        prompt_path.write_text(prompt, encoding="utf-8")

        jobs.append(
            {
                "no": item["no"],
                "id": slug,
                "ko": item["ko"],
                "identity_reference": str(source),
                "style_references": style_refs,
                "prompt": str(prompt_path),
                "raw_output": str(RAW_DIR / f"{slug}.png"),
                "cutout_output": str(CUT_DIR / f"{slug}.png"),
                "final_outputs": [str(out_dir / f"{slug}.png") for out_dir in OUT_DIRS],
            }
        )

    JOBS_JSONL.write_text(
        "\n".join(json.dumps(job, ensure_ascii=False) for job in jobs) + "\n",
        encoding="utf-8",
    )
    MANIFEST_JSON.write_text(
        json.dumps(
            {
                "count": len(jobs),
                "work_dir": str(WORK_DIR),
                "jobs": str(JOBS_JSONL),
                "prompt_dir": str(PROMPT_DIR),
                "raw_dir": str(RAW_DIR),
                "cutout_dir": str(CUT_DIR),
                "style_references": style_refs,
                "output_dirs": [str(path) for path in OUT_DIRS],
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )
    print(f"wrote {len(jobs)} prompts")
    print(JOBS_JSONL)
    print(MANIFEST_JSON)


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
                pix[x, y] = (r, g, b, 150)
            else:
                pix[x, y] = (r, g, b, 255 if a else 0)
    return image


def normalize_halfbody(image: Image.Image) -> Image.Image:
    image = remove_magenta_key(image)
    bbox = image.getbbox()
    if not bbox:
        raise ValueError("empty alpha after chroma-key removal")

    crop = image.crop(bbox)
    crop_bbox = crop.getbbox()
    if crop_bbox:
        crop = crop.crop(crop_bbox)

    crop.thumbnail((600, 730), Image.Resampling.LANCZOS)
    out = Image.new("RGBA", (640, 768), (0, 0, 0, 0))
    x = (640 - crop.width) // 2
    y = max(18, 748 - crop.height)
    out.alpha_composite(crop, (x, y))
    return out


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
    print(f"saved {slug}")
    print(raw_path)
    print(cut_path)


def load_jobs() -> list[dict[str, object]]:
    if not JOBS_JSONL.exists():
        write_prompt_files()
    jobs = []
    for line in JOBS_JSONL.read_text(encoding="utf-8").splitlines():
        if line.strip():
            jobs.append(json.loads(line))
    return jobs


def status() -> None:
    roster = load_roster()
    for out_dir in OUT_DIRS:
        present = sum(1 for item in roster if (out_dir / f"{item['id']}.png").exists())
        print(f"{out_dir}: {present}/{len(roster)}")

    missing = [item for item in roster if not (OUT_DIRS[0] / f"{item['id']}.png").exists()]
    if missing:
        preview = ", ".join(f"{int(item['no']):03d}:{item['id']}" for item in missing[:12])
        more = "" if len(missing) <= 12 else f" ... +{len(missing) - 12}"
        print(f"next missing: {preview}{more}")


def print_next(count: int, include_existing: bool) -> None:
    jobs = load_jobs()
    pending = jobs if include_existing else [job for job in jobs if not Path(str(job["final_outputs"][0])).exists()]
    for job in pending[:count]:
        print(f"{int(job['no']):03d}. {job['ko']} ({job['id']})")
        print(f"identity: {job['identity_reference']}")
        for style_ref in job["style_references"]:
            print(f"style: {style_ref}")
        print(f"prompt: {job['prompt']}")
        print()
    if not pending:
        print("all final outputs exist")


def contact_sheet() -> None:
    roster = [item for item in load_roster() if (OUT_DIRS[0] / f"{item['id']}.png").exists()]
    if not roster:
        print("no generated halfbodies yet")
        return

    columns = 5
    cell_w, cell_h = 190, 260
    rows = (len(roster) + columns - 1) // columns
    sheet = Image.new("RGBA", (columns * cell_w, rows * cell_h), (8, 12, 18, 255))
    name_font = load_font(12)
    slug_font = load_font(11)

    for index, item in enumerate(roster):
        slug = str(item["id"])
        image = Image.open(OUT_DIRS[0] / f"{slug}.png").convert("RGBA")
        bg = Image.new("RGBA", (640, 768), (18, 25, 35, 255))
        bg.alpha_composite(image)
        thumb = ImageOps.contain(bg, (cell_w, 225))
        tile = Image.new("RGBA", (cell_w, cell_h), (9, 13, 19, 255))
        tile.alpha_composite(thumb, ((cell_w - thumb.width) // 2, 0))
        draw = ImageDraw.Draw(tile)
        draw.text((7, 231), f"{int(item['no']):03d}. {item['ko']}", fill=(235, 235, 235, 255), font=name_font)
        draw.text((7, 246), slug, fill=(170, 182, 196, 255), font=slug_font)
        sheet.alpha_composite(tile, ((index % columns) * cell_w, (index // columns) * cell_h))

    out_path = WORK_DIR / "mainstyle_contact_current.png"
    out_path.parent.mkdir(parents=True, exist_ok=True)
    sheet.save(out_path)
    print(out_path)


def backup_existing() -> None:
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_root = ROOT / "asset_backups" / f"halfbodies_before_mainstyle_{stamp}"
    backup_root.mkdir(parents=True, exist_ok=True)

    for out_dir in OUT_DIRS:
        if not out_dir.exists():
            continue
        name = "app_www" if "app/www" in str(out_dir) else "assets"
        dest = backup_root / name
        shutil.copytree(out_dir, dest, dirs_exist_ok=True)
        print(dest)


def main() -> None:
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("write-prompts")
    sub.add_parser("status")
    next_parser = sub.add_parser("next")
    next_parser.add_argument("--count", type=int, default=5)
    next_parser.add_argument("--include-existing", action="store_true")
    process = sub.add_parser("process")
    process.add_argument("slug")
    process.add_argument("--source", type=Path)
    sub.add_parser("contact-sheet")
    sub.add_parser("backup-existing")
    args = parser.parse_args()

    if args.command == "write-prompts":
        write_prompt_files()
    elif args.command == "status":
        status()
    elif args.command == "next":
        print_next(args.count, args.include_existing)
    elif args.command == "process":
        process_image(args.slug, args.source)
    elif args.command == "contact-sheet":
        contact_sheet()
    elif args.command == "backup-existing":
        backup_existing()


if __name__ == "__main__":
    main()
