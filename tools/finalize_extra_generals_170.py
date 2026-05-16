from __future__ import annotations

import shutil
from collections import deque
from pathlib import Path

from PIL import Image


ROOT = Path(__file__).resolve().parents[1]
TMP = ROOT / "tmp" / "extra_generals_170"
RAW = TMP / "raw"
ASSETS = ROOT / "assets" / "generals"
APP_ASSETS = ROOT / "app" / "www" / "assets" / "generals"
KINDS = ("busts", "faces", "battle_faces")


def load_extra_ids() -> list[str]:
    manifest = TMP / "manifest.json"
    import json

    data = json.loads(manifest.read_text(encoding="utf-8"))
    return [item["id"] for item in data["jobs"]]


def remove_green_background(image: Image.Image) -> Image.Image:
    im = image.convert("RGBA")
    pix = im.load()
    width, height = im.size
    seen: set[tuple[int, int]] = set()
    q: deque[tuple[int, int]] = deque()

    def is_key(x: int, y: int) -> bool:
        r, g, b, a = pix[x, y]
        return a > 0 and g >= 150 and r <= 110 and b <= 130 and g >= r + 45 and g >= b + 45

    for x in range(width):
        for y in (0, height - 1):
            if is_key(x, y) and (x, y) not in seen:
                seen.add((x, y))
                q.append((x, y))
    for y in range(height):
        for x in (0, width - 1):
            if is_key(x, y) and (x, y) not in seen:
                seen.add((x, y))
                q.append((x, y))

    while q:
        x, y = q.popleft()
        r, g, b, _ = pix[x, y]
        pix[x, y] = (r, g, b, 0)
        for nx, ny in ((x + 1, y), (x - 1, y), (x, y + 1), (x, y - 1)):
            if 0 <= nx < width and 0 <= ny < height and (nx, ny) not in seen and is_key(nx, ny):
                seen.add((nx, ny))
                q.append((nx, ny))
    return im


def main() -> None:
    ids = load_extra_ids()
    missing: list[str] = []
    written = 0
    backup = ASSETS / "_backup_before_extra_170_finalize_20260510"
    backup.mkdir(exist_ok=True)

    for kind in KINDS:
        (ASSETS / kind).mkdir(parents=True, exist_ok=True)
        (APP_ASSETS / kind).mkdir(parents=True, exist_ok=True)
        for slug in ids:
            src = RAW / kind / f"{slug}.png"
            if not src.exists():
                missing.append(str(src))
                continue

            dst = ASSETS / kind / f"{slug}.png"
            app_dst = APP_ASSETS / kind / f"{slug}.png"
            if dst.exists():
                shutil.copy2(dst, backup / f"{kind}_{slug}.png")

            image = remove_green_background(Image.open(src))
            image = image.resize((512, 512), Image.Resampling.LANCZOS)
            image.save(dst)
            image.save(app_dst)
            written += 1

    print(f"written: {written}")
    print(f"missing: {len(missing)}")
    if missing:
        print("first_missing:")
        for path in missing[:12]:
            print(path)


if __name__ == "__main__":
    main()
