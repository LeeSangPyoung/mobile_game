#!/usr/bin/env python3
from __future__ import annotations

import argparse
import ast
import json
import os
import shutil
import subprocess
from pathlib import Path
from typing import Iterable

from PIL import Image


ROOT = Path(__file__).resolve().parents[1]
ROSTER_JS = ROOT / "assets/generals/roster_200.js"
REF_DIR = ROOT / "assets/generals/new_characters/front_gaze_200_v10_scale_audit"
FINAL_DIR = ROOT / "assets/generals/new_characters/upper_body_200_redraw_v6_above_navel"
WORK_DIR = ROOT / "tmp/halfbody_v6_edit"
STAGED_DIR = WORK_DIR / "staged"
PROMPT_DIR = WORK_DIR / "prompts"
JOB_PATH = WORK_DIR / "jobs.jsonl"
REVIEW_JOB_PATH = WORK_DIR / "review_jobs.jsonl"
IMAGE_CLI = Path.home() / ".codex/skills/.system/imagegen/scripts/image_gen.py"
ENV_PATHS = [
    ROOT / ".env",
    ROOT / ".env.local",
    Path.home() / ".openai_env",
]
AUTH_JSON = Path.home() / ".codex/auth.json"
BASE_TRUE_COUNT = 63
STRICT_REGENERATED_IDS = {
    "kuai_yue",
    "kuai_liang",
    "cai_mao",
    "zhang_yun",
    "zhu_zhi",
    "sun_luban",
    "sun_luyu",
    "daqiao",
    "xiaoqiao",
    "lian_shi",
    "guan_suo",
    "guan_yinping",
    "liu_shan",
    "zhou_cang",
    "fu_shi_ren",
    "zhang_song",
    "sha_moke",
    "yuan_tan",
    "yuan_xi",
    "xu_sheng",
    "ding_feng",
    "han_dang",
    "cheng_pu",
    "zhou_tai",
    "jiang_qin",
    "ling_tong",
    "lu_su",
    "zhang_zhao",
    "zhang_hong",
    "zhu_huan",
    "zhu_ran",
    "bu_zhi",
    "kan_ze",
    "yu_fan",
    "he_qi",
    "pan_zhang",
    "ma_zhong_wu",
    "quan_cong",
    "sun_jian",
}
RECOVERED_NEEDS_REDRAW_IDS = {
    "xu_sheng",
    "ding_feng",
    "han_dang",
    "cheng_pu",
    "zhou_tai",
    "jiang_qin",
    "ling_tong",
    "lu_su",
    "zhang_zhao",
    "zhang_hong",
    "zhu_huan",
    "zhu_ran",
    "bu_zhi",
    "kan_ze",
    "yu_fan",
    "he_qi",
    "pan_zhang",
    "quan_cong",
    "sun_jian",
    "sun_shao",
    "sun_huan",
    "ma_zhong_wu",
    "guan_ping",
    "guan_xing",
    "zhang_bao",
    "liu_feng",
    "ma_su",
    "ma_liang",
    "jiang_wei",
    "wei_yan",
    "fa_zheng",
    "jian_yong",
    "mi_zhu",
    "mi_fang",
    "sun_qian",
    "liao_hua",
    "ma_dai",
    "yan_yan",
    "li_yan",
    "fei_yi",
    "dong_yun",
    "jiang_wan",
    "huang_quan",
    "chen_dao",
    "meng_da",
    "li_hui",
    "huo_jun",
    "zhuge_zhan",
    "zhuge_jin",
    "zhuge_dan",
    "zhang_yi_shu",
    "dong_jue",
    "xin_pi",
    "gongsun_zan",
    "gongsun_du",
    "gongsun_kang",
    "liu_biao",
    "liu_zhang",
    "liu_yao",
    "tao_qian",
    "kong_rong",
    "zhang_lu",
    "zhang_ren",
    "ma_teng",
    "han_sui",
    "dong_cheng",
    "he_jin",
    "zhang_rang",
    "wang_yun",
    "li_jue",
    "guo_si",
    "zhang_ji",
    "zhang_xiu",
    "hua_xiong",
    "li_ru",
    "yuan_shu",
    "liu_xun",
}


def load_roster() -> list[tuple[str, str]]:
    text = ROSTER_JS.read_text(encoding="utf-8")
    prefix = "window.GENERALS_200 ="
    if prefix not in text:
        raise SystemExit(f"could not parse roster: {ROSTER_JS}")
    data = text.split(prefix, 1)[1].strip()
    if data.endswith(";"):
        data = data[:-1]
    return [(str(slug), str(ko)) for slug, ko in ast.literal_eval(data)]


def ref_path(slug: str) -> Path:
    return REF_DIR / f"{slug}_front_gaze_v1.png"


def final_path(slug: str) -> Path:
    return FINAL_DIR / f"{slug}_halfbody_redraw_v6.png"


def staged_path(slug: str) -> Path:
    return STAGED_DIR / f"{slug}_halfbody_redraw_v6.png"


def prompt_for(slug: str, ko: str) -> str:
    return f"""Edit the input image. Use it as the only visual identity reference for {ko} ({slug}).

Create a newly redrawn upper-body portrait for the same Three Kingdoms SD game character.
Preserve the exact character identity, face language, head-to-body proportion, hair/headgear, armor colors, weapon cues, faction palette, heroic SD 3D collectible style, and ornate metal detailing from the input image.

Identity lock: the output must read as the same person as the input full-body character. Keep the same age read, gender read, face shape, eyebrow angle, eye size, nose/mouth scale, cheek shape, beard/moustache logic, hairstyle, crown/helmet silhouette, shoulder armor language, and body build. Do not beautify, infantilize, modernize, simplify into a generic anime doll, or make the face larger/rounder than the reference.

Scale lock: keep the same compact heroic SD game proportions as the input. The head including hair/helmet should feel proportional to the shoulders and chest armor, not an oversized close-up. Pull the camera back enough to show the torso down to immediately below the horizontal waist belt.

This must be a new illustration, not a crop, not a zoom, not a trace, and not the same pose as the input full-body reference.

Framing: vertical game portrait from the top of the head/crown/plume to immediately below the horizontal waist belt. The target is the belt's lower edge. The horizontal waist belt must be fully visible, and the image must end right under it with only a tiny strip of clothing below. Do not crop at the chest, solar plexus, upper abdomen, chest ornament, or above the belt. Show both shoulders, upper arms, elbows when useful, chest armor, robe/armor torso, hand/prop gesture, the horizontal waist belt, and then stop. This is not a head-and-chest close-up.
Keep fans, weapons, hands, sleeves, and props from hiding the belt or crop line. Do not show pelvis, groin/crotch, hips, thighs, knees, legs, boots, feet, floor, or a full weapon.

Pose: change the full-body pose into a fresh half-body pose. Do not copy the straight full-body stance. Turn the shoulders, move at least one arm/hand, and use the weapon or prop only as a partial chest/shoulder gesture when useful. Eyes must look directly at the viewer.

Expression: the expression must be different from the full-body reference while staying in character. Prefer the same face identity with a colder closed-mouth smirk, stern stare, calculating strategist look, or composed heroic expression. Do not reuse the full-body expression. Do not turn older men into cute boys, stern warriors into soft mascots, or elegant women into generic big-eyed princesses.

Background: plain dark warm-brown studio gradient only. Remove fire, sparks, embers, smoke, fog, dust, particles, floor glow, and all environmental effects.

Hard reject constraints: no text, no labels, no poster, no chart, no infographic, no UI, no diagrams, no food, no real people, no extra characters, no unrelated objects, no watermark, no border, no giant head close-up, no head-and-chest-only crop, no baby face, no generic anime face, no changed age, no changed gender, no copied full-body pose, no reused full-body expression, no missing shoulders, no cropped crown/head, no pelvis, no groin/crotch, no hips, no legs, no boots.
"""


def load_env_files() -> None:
    for path in ENV_PATHS:
        if not path.exists():
            continue
        for raw in path.read_text(encoding="utf-8").splitlines():
            line = raw.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, value = line.split("=", 1)
            key = key.strip()
            value = value.strip().strip('"').strip("'")
            if key and key not in os.environ:
                os.environ[key] = value
    if not os.getenv("OPENAI_API_KEY") and AUTH_JSON.exists():
        try:
            data = json.loads(AUTH_JSON.read_text(encoding="utf-8"))
        except Exception:
            data = {}
        for key in ("OPENAI_API_KEY", "openai_api_key", "api_key"):
            value = data.get(key)
            if isinstance(value, str) and value.strip():
                os.environ["OPENAI_API_KEY"] = value.strip()
                break


def roster_index(slug: str) -> int:
    for index, (candidate, _) in enumerate(load_roster(), start=1):
        if candidate == slug:
            return index
    raise SystemExit(f"unknown slug: {slug}")


def iter_items(start_id: str | None, limit: int | None, missing_only: bool) -> Iterable[tuple[int, str, str]]:
    started = start_id is None
    count = 0
    for index, (slug, ko) in enumerate(load_roster(), start=1):
        if not started and slug == start_id:
            started = True
        if not started:
            continue
        if missing_only and final_path(slug).exists():
            continue
        yield index, slug, ko
        count += 1
        if limit is not None and count >= limit:
            break


def needs_strict_redraw(index: int, slug: str) -> bool:
    return index > BASE_TRUE_COUNT and not staged_path(slug).exists()


def iter_review_items(start_id: str | None, limit: int | None, staged_missing_only: bool) -> Iterable[tuple[int, str, str]]:
    started = start_id is None
    count = 0
    for index, (slug, ko) in enumerate(load_roster(), start=1):
        if not needs_strict_redraw(index, slug):
            continue
        if not started and slug == start_id:
            started = True
        if not started:
            continue
        if staged_missing_only and staged_path(slug).exists():
            continue
        yield index, slug, ko
        count += 1
        if limit is not None and count >= limit:
            break


def build_command(slug: str, ko: str, *, dry_run: bool, force: bool) -> list[str]:
    out = staged_path(slug)
    cmd = [
        "python3",
        str(IMAGE_CLI),
        "edit",
        "--image",
        str(ref_path(slug)),
        "--prompt",
        prompt_for(slug, ko),
        "--size",
        "1024x1536",
        "--quality",
        "high",
        "--out",
        str(out),
    ]
    if force:
        cmd.append("--force")
    if dry_run:
        cmd.append("--dry-run")
    return cmd


def require_paths(slug: str) -> None:
    if not IMAGE_CLI.exists():
        raise SystemExit(f"missing image CLI: {IMAGE_CLI}")
    if not ref_path(slug).exists():
        raise SystemExit(f"missing full-body reference: {ref_path(slug)}")


def status() -> None:
    load_env_files()
    roster = load_roster()
    complete = [slug for slug, _ in roster if final_path(slug).exists()]
    staged = [slug for slug, _ in roster if staged_path(slug).exists()]
    review_targets = [(index, slug, ko) for index, slug, ko in iter_review_items(None, None, False)]
    review_staged = [slug for _, slug, _ in review_targets if staged_path(slug).exists()]
    recovered_pending = [slug for _, slug, _ in review_targets if slug in RECOVERED_NEEDS_REDRAW_IDS]
    provisional_pending = [slug for _, slug, _ in review_targets if slug not in RECOVERED_NEEDS_REDRAW_IDS]
    strict_done = [
        slug
        for index, (slug, _) in enumerate(roster, start=1)
        if index > BASE_TRUE_COUNT and staged_path(slug).exists()
    ]
    true_done = min(BASE_TRUE_COUNT, len(roster)) + len(strict_done)
    redraw_remaining = len(review_targets) - len(review_staged)
    print(f"final: {len(complete)}/{len(roster)}")
    print(f"staged: {len(staged)}/{len(roster)}")
    print(f"true progress: {true_done}/{len(roster)}")
    print(f"redraw remaining: {redraw_remaining}")
    print(f"redraw queue: {len(review_targets)} target, {len(review_staged)} staged")
    print(f"breakdown: recovered {len(recovered_pending)}, provisional {len(provisional_pending)}")
    print(f"api_key: {'present' if os.getenv('OPENAI_API_KEY') else 'missing'}")
    for index, slug, ko in iter_items(None, 12, True):
        print(f"missing {index:03d} {slug} {ko}")
    for index, slug, ko in iter_review_items(None, 12, True):
        print(f"review {index:03d} {slug} {ko}")


def write_jobs(start_id: str | None, limit: int | None, missing_only: bool) -> None:
    WORK_DIR.mkdir(parents=True, exist_ok=True)
    PROMPT_DIR.mkdir(parents=True, exist_ok=True)
    rows = []
    for index, slug, ko in iter_items(start_id, limit, missing_only):
        prompt_path = PROMPT_DIR / f"{index:03d}_{slug}.txt"
        prompt_path.write_text(prompt_for(slug, ko), encoding="utf-8")
        rows.append(
            {
                "no": index,
                "id": slug,
                "ko": ko,
                "reference": str(ref_path(slug)),
                "staged": str(staged_path(slug)),
                "final": str(final_path(slug)),
                "prompt": str(prompt_path),
                "command": build_command(slug, ko, dry_run=False, force=False),
            }
        )
    JOB_PATH.write_text("\n".join(json.dumps(row, ensure_ascii=False) for row in rows) + "\n", encoding="utf-8")
    print(f"wrote {len(rows)} jobs: {JOB_PATH}")


def write_review_jobs(start_id: str | None, limit: int | None, staged_missing_only: bool) -> None:
    WORK_DIR.mkdir(parents=True, exist_ok=True)
    PROMPT_DIR.mkdir(parents=True, exist_ok=True)
    rows = []
    for index, slug, ko in iter_review_items(start_id, limit, staged_missing_only):
        prompt_path = PROMPT_DIR / f"{index:03d}_{slug}.txt"
        prompt_path.write_text(prompt_for(slug, ko), encoding="utf-8")
        rows.append(
            {
                "no": index,
                "id": slug,
                "ko": ko,
                "reference": str(ref_path(slug)),
                "staged": str(staged_path(slug)),
                "final": str(final_path(slug)),
                "prompt": str(prompt_path),
                "command": build_command(slug, ko, dry_run=False, force=True),
            }
        )
    REVIEW_JOB_PATH.write_text(
        "\n".join(json.dumps(row, ensure_ascii=False) for row in rows) + "\n",
        encoding="utf-8",
    )
    print(f"wrote {len(rows)} review jobs: {REVIEW_JOB_PATH}")


def run_one(slug: str, *, dry_run: bool, force: bool) -> None:
    load_env_files()
    roster = dict(load_roster())
    if slug not in roster:
        raise SystemExit(f"unknown slug: {slug}")
    require_paths(slug)
    STAGED_DIR.mkdir(parents=True, exist_ok=True)
    if not dry_run and not os.getenv("OPENAI_API_KEY"):
        raise SystemExit("OPENAI_API_KEY is not set. Export it before running real edit jobs.")
    cmd = build_command(slug, roster[slug], dry_run=dry_run, force=force)
    subprocess.run(cmd, check=True)


def next_missing(start_id: str | None = None) -> tuple[int, str, str]:
    for item in iter_items(start_id, 1, True):
        return item
    raise SystemExit("no missing characters")


def next_review(start_id: str | None = None) -> tuple[int, str, str]:
    for item in iter_review_items(start_id, 1, True):
        return item
    raise SystemExit("no review characters without staged output")


def run_next(start_id: str | None, *, dry_run: bool, force: bool) -> None:
    index, slug, ko = next_missing(start_id)
    print(f"next {index:03d} {slug} {ko}")
    run_one(slug, dry_run=dry_run, force=force)


def run_review_next(start_id: str | None, *, dry_run: bool, force: bool) -> None:
    index, slug, ko = next_review(start_id)
    print(f"review next {index:03d} {slug} {ko}")
    run_one(slug, dry_run=dry_run, force=force)


def normalize_for_final(src: Path, dst: Path) -> None:
    image = Image.open(src).convert("RGB")
    width, height = image.size
    # Final crop target: top-of-head to immediately below the horizontal waist belt.
    # A 4:5 crop kept pelvis/groin content, which violates the asset spec.
    target_height = min(height, max(1, round(width * 0.86)))
    image = image.crop((0, 0, width, target_height))
    dst.parent.mkdir(parents=True, exist_ok=True)
    image.save(dst)


def publish(slug: str, *, force: bool, no_normalize: bool) -> None:
    src = staged_path(slug)
    dst = final_path(slug)
    if not src.exists():
        raise SystemExit(f"missing staged image: {src}")
    if dst.exists() and not force:
        raise SystemExit(f"final already exists: {dst} (use --force to overwrite)")
    if no_normalize:
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src, dst)
    else:
        normalize_for_final(src, dst)
    print(f"published {slug}: {dst}")


def main() -> None:
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers(dest="command", required=True)

    sub.add_parser("status")

    jobs = sub.add_parser("write-jobs")
    jobs.add_argument("--start-id")
    jobs.add_argument("--limit", type=int)
    jobs.add_argument("--all", action="store_true", help="include already completed items")

    review_jobs = sub.add_parser("write-review-jobs")
    review_jobs.add_argument("--start-id")
    review_jobs.add_argument("--limit", type=int)
    review_jobs.add_argument("--all", action="store_true", help="include already staged review items")

    run = sub.add_parser("run")
    run.add_argument("slug")
    run.add_argument("--dry-run", action="store_true")
    run.add_argument("--force", action="store_true")

    run_next_parser = sub.add_parser("run-next")
    run_next_parser.add_argument("--start-id")
    run_next_parser.add_argument("--dry-run", action="store_true")
    run_next_parser.add_argument("--force", action="store_true")

    run_review_next_parser = sub.add_parser("run-review-next")
    run_review_next_parser.add_argument("--start-id")
    run_review_next_parser.add_argument("--dry-run", action="store_true")
    run_review_next_parser.add_argument("--force", action="store_true")

    pub = sub.add_parser("publish")
    pub.add_argument("slug")
    pub.add_argument("--force", action="store_true")
    pub.add_argument("--no-normalize", action="store_true")

    args = parser.parse_args()
    if args.command == "status":
        status()
    elif args.command == "write-jobs":
        write_jobs(args.start_id, args.limit, missing_only=not args.all)
    elif args.command == "write-review-jobs":
        write_review_jobs(args.start_id, args.limit, staged_missing_only=not args.all)
    elif args.command == "run":
        run_one(args.slug, dry_run=args.dry_run, force=args.force)
    elif args.command == "run-next":
        run_next(args.start_id, dry_run=args.dry_run, force=args.force)
    elif args.command == "run-review-next":
        run_review_next(args.start_id, dry_run=args.dry_run, force=args.force)
    elif args.command == "publish":
        publish(args.slug, force=args.force, no_normalize=args.no_normalize)


if __name__ == "__main__":
    main()
