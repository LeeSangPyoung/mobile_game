from __future__ import annotations

import json
import ast
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
ROSTER_JS = ROOT / "assets" / "generals" / "roster_200.js"
OUT_DIR = ROOT / "tmp" / "extra_generals_170"
RAW_DIR = OUT_DIR / "raw"
CURRENT_IDS = {
    "cao_cao",
    "cao_xing",
    "dian_wei",
    "dong_zhuo",
    "gan_ning",
    "guan_yu",
    "guo_jia",
    "huang_gai",
    "huang_zhong",
    "liu_bei",
    "lu_bu",
    "lu_xun",
    "ma_chao",
    "meng_huo",
    "pang_tong",
    "sima_yi",
    "sun_ce",
    "sun_quan",
    "taishi_ci",
    "wen_chou",
    "xiahou_dun",
    "xu_chu",
    "xu_huang",
    "yan_liang",
    "yuan_shao",
    "zhang_fei",
    "zhang_liao",
    "zhao_yun",
    "zhou_yu",
    "zhuge_liang",
}


def load_roster() -> list[tuple[str, str]]:
    text = ROSTER_JS.read_text(encoding="utf-8")
    start = text.index("[")
    end = text.rindex("]") + 1
    data = ast.literal_eval(text[start:end])
    return [(row[0], row[1]) for row in data]


def prompt(kind: str, slug: str, korean_name: str) -> str:
    common = (
        "Create one original Three Kingdoms mobile game character asset. "
        f"Character: {korean_name} ({slug}), from Romance of the Three Kingdoms. "
        "Use the same polished stylized 3D cartoon art direction as the existing project: "
        "chunky heroic proportions, glossy gold and lacquered armor trim, clean readable silhouette, "
        "dramatic but friendly mobile RPG look. "
        "The background must be a perfectly flat solid #00ff00 chroma-key green with no shadow, "
        "no gradient, no floor, no texture, no checkerboard, no text, no watermark. "
        "Do not use green in the character design. Center the subject with generous padding."
    )
    if kind == "busts":
        return (
            common
            + " Asset type: full-body standing general cutout. Show the entire character from head to boots, "
            "weapon or prop allowed only if historically appropriate and kept inside the frame."
        )
    if kind == "faces":
        return (
            common
            + " Asset type: upper-body portrait. Show head, neck, shoulders, and upper chest. "
            "Make the face clear and distinct, calm or heroic expression."
        )
    if kind == "battle_faces":
        return (
            common
            + " Asset type: battle face icon. Large close-up for combat UI: show entire head, full chin or beard, "
            "full neck, and only a small amount of collar or upper shoulder. No torso, no arms, no weapons. "
            "Use a fierce battle shout or intense command expression."
        )
    raise ValueError(kind)


def main() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    for kind in ("busts", "faces", "battle_faces"):
        (RAW_DIR / kind).mkdir(parents=True, exist_ok=True)

    roster = load_roster()
    extras = [(slug, name) for slug, name in roster if slug not in CURRENT_IDS]
    if len(extras) != 170:
        raise SystemExit(f"Expected 170 extras, got {len(extras)}")

    jobs_path = OUT_DIR / "jobs.jsonl"
    jobs_by_kind_paths = {
        "busts": OUT_DIR / "jobs_busts_170.jsonl",
        "faces": OUT_DIR / "jobs_faces_170.jsonl",
        "battle_faces": OUT_DIR / "jobs_battle_faces_170.jsonl",
    }
    manifest_path = OUT_DIR / "manifest.json"
    jobs = []
    with jobs_path.open("w", encoding="utf-8") as f:
        for slug, korean_name in extras:
            for kind in ("busts", "faces", "battle_faces"):
                job = {
                    "prompt": prompt(kind, slug, korean_name),
                    "use_case": "stylized-concept",
                    "size": "1024x1024",
                    "quality": "medium",
                    "output_format": "png",
                    "out": f"{slug}.png",
                    "metadata": {"id": slug, "name": korean_name, "kind": kind},
                }
                jobs.append(job)
                f.write(json.dumps(job, ensure_ascii=False) + "\n")
    for kind, path in jobs_by_kind_paths.items():
        with path.open("w", encoding="utf-8") as f:
            for job in jobs:
                if job["metadata"]["kind"] == kind:
                    f.write(json.dumps(job, ensure_ascii=False) + "\n")

    manifest = {
        "count_generals": len(extras),
        "count_jobs": len(jobs),
        "jobs": [
            {
                "id": slug,
                "name": korean_name,
                "outputs": {
                    kind: str(RAW_DIR / kind / f"{slug}.png")
                    for kind in ("busts", "faces", "battle_faces")
                },
            }
            for slug, korean_name in extras
        ],
    }
    manifest_path.write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    print(f"generals: {len(extras)}")
    print(f"jobs: {len(jobs)}")
    print(f"jobs_path: {jobs_path}")
    for kind, path in jobs_by_kind_paths.items():
        print(f"jobs_{kind}_path: {path}")
    print(f"manifest_path: {manifest_path}")


if __name__ == "__main__":
    main()
