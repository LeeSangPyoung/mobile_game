from __future__ import annotations

import argparse
import shutil
import subprocess
from pathlib import Path

from PIL import Image


ROOT = Path(__file__).resolve().parents[1]
GENERATED_ROOT = Path("/Users/leesp/.codex/generated_images/019e0fdc-2e74-7a22-8d75-b705728679b0")
REMOVE_KEY = Path("/Users/leesp/.codex/skills/.system/imagegen/scripts/remove_chroma_key.py")
KINDS = {
    "busts": (640, 768),
    "faces": (512, 512),
    "battle_faces": (512, 512),
}


def latest_png() -> Path:
    files = [p for p in GENERATED_ROOT.glob("*.png") if p.is_file()]
    if not files:
        raise SystemExit(f"No generated pngs found in {GENERATED_ROOT}")
    return max(files, key=lambda p: p.stat().st_mtime_ns)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("kind", choices=KINDS)
    parser.add_argument("slug")
    args = parser.parse_args()

    src = latest_png()
    raw = ROOT / "tmp" / "new_generals_70" / "raw" / args.kind / f"{args.slug}.png"
    processed = ROOT / "tmp" / "new_generals_70" / "processed" / args.kind / f"{args.slug}.png"
    raw.parent.mkdir(parents=True, exist_ok=True)
    processed.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(src, raw)

    subprocess.run(
        [
            "python3",
            str(REMOVE_KEY),
            "--input",
            str(raw),
            "--out",
            str(processed),
            "--force",
            "--auto-key",
            "border",
            "--soft-matte",
            "--transparent-threshold",
            "12",
            "--opaque-threshold",
            "220",
            "--despill",
        ],
        check=True,
    )

    target_size = KINDS[args.kind]
    im = Image.open(processed).convert("RGBA")
    im.thumbnail(target_size, Image.Resampling.LANCZOS)
    canvas = Image.new("RGBA", target_size, (0, 0, 0, 0))
    canvas.alpha_composite(im, ((target_size[0] - im.width) // 2, (target_size[1] - im.height) // 2))

    for base in [ROOT / "assets" / "generals", ROOT / "app" / "www" / "assets" / "generals"]:
        dst = base / args.kind / f"{args.slug}.png"
        dst.parent.mkdir(parents=True, exist_ok=True)
        canvas.save(dst)

    print(f"saved {args.kind}/{args.slug}.png from {src.name} as {target_size[0]}x{target_size[1]}")


if __name__ == "__main__":
    main()
