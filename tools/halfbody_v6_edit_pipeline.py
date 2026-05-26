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
IMAGE_CLI = Path.home() / ".codex/skills/.system/imagegen/scripts/image_gen.py"
ENV_PATHS = [
    ROOT / ".env",
    ROOT / ".env.local",
    Path.home() / ".openai_env",
]
AUTH_JSON = Path.home() / ".codex/auth.json"


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
Preserve the exact character identity, face language, hair/headgear, armor colors, weapon cues, faction palette, cute heroic 3D collectible style, and ornate metal detailing from the input image.

This must be a new illustration, not a crop, not a zoom, not a trace, and not the same pose as the input full-body reference.

Framing: vertical game portrait from the top of the head/crown/plume to the navel line only. Show both shoulders, upper arms, elbows when useful, chest armor, and only the very top of the abdomen. The crop must stop before the waist belt becomes a focal point.
Do not show lower abdomen, waist sash, belt ornaments, hanging tassels below the belt, hips, thighs, knees, legs, boots, feet, floor, or a full weapon.

Pose: change the full-body pose into a fresh half-body pose. Keep the weapon or prop only as a partial shoulder/chest accessory when useful. Eyes must look directly at the viewer.

Expression: vary the full-body expression while staying in character. Prefer a closed-mouth confident smirk, stern stare, or composed heroic expression instead of copying the exact full-body face.

Background: plain dark warm-brown studio gradient only. Remove fire, sparks, embers, smoke, fog, dust, particles, floor glow, and all environmental effects.

Hard reject constraints: no text, no labels, no poster, no chart, no infographic, no UI, no diagrams, no food, no real people, no extra characters, no unrelated objects, no watermark, no border.
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
    print(f"final: {len(complete)}/{len(roster)}")
    print(f"staged: {len(staged)}/{len(roster)}")
    print(f"api_key: {'present' if os.getenv('OPENAI_API_KEY') else 'missing'}")
    for index, slug, ko in iter_items(None, 12, True):
        print(f"missing {index:03d} {slug} {ko}")


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


def run_next(start_id: str | None, *, dry_run: bool, force: bool) -> None:
    index, slug, ko = next_missing(start_id)
    print(f"next {index:03d} {slug} {ko}")
    run_one(slug, dry_run=dry_run, force=force)


def normalize_for_final(src: Path, dst: Path) -> None:
    image = Image.open(src).convert("RGB")
    width, height = image.size
    target_height = min(height, max(1, round(width * 1.25)))
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

    run = sub.add_parser("run")
    run.add_argument("slug")
    run.add_argument("--dry-run", action="store_true")
    run.add_argument("--force", action="store_true")

    run_next_parser = sub.add_parser("run-next")
    run_next_parser.add_argument("--start-id")
    run_next_parser.add_argument("--dry-run", action="store_true")
    run_next_parser.add_argument("--force", action="store_true")

    pub = sub.add_parser("publish")
    pub.add_argument("slug")
    pub.add_argument("--force", action="store_true")
    pub.add_argument("--no-normalize", action="store_true")

    args = parser.parse_args()
    if args.command == "status":
        status()
    elif args.command == "write-jobs":
        write_jobs(args.start_id, args.limit, missing_only=not args.all)
    elif args.command == "run":
        run_one(args.slug, dry_run=args.dry_run, force=args.force)
    elif args.command == "run-next":
        run_next(args.start_id, dry_run=args.dry_run, force=args.force)
    elif args.command == "publish":
        publish(args.slug, force=args.force, no_normalize=args.no_normalize)


if __name__ == "__main__":
    main()
