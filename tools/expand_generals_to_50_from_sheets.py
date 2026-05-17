from __future__ import annotations

import csv
import re
import shutil
from pathlib import Path

from PIL import Image


ROOT = Path(__file__).resolve().parents[1]
ASSETS = ROOT / "assets" / "generals"
WWW_ASSETS = ROOT / "app" / "www" / "assets" / "generals"
GALLERY = ROOT / "generals_200_gallery.html"

TARGET_SIZE = {
    "busts": (640, 768),
    "faces": (512, 512),
    "battle_faces": (512, 512),
}

BASE_IDS = [
    "liu_bei",
    "guan_yu",
    "zhang_fei",
    "zhao_yun",
    "lu_bu",
    "xiahou_dun",
    "cao_cao",
    "cao_xing",
    "taishi_ci",
    "zhuge_liang",
    "huang_zhong",
    "huang_gai",
    "yan_liang",
    "dong_zhuo",
    "sima_yi",
    "gan_ning",
    "yuan_shao",
    "sun_quan",
    "zhou_yu",
    "ma_chao",
    "sun_ce",
    "lu_xun",
    "pang_tong",
    "guo_jia",
    "dian_wei",
    "xu_chu",
    "zhang_liao",
    "xu_huang",
    "wen_chou",
    "meng_huo",
]

EXTRA_IDS = [
    "hua_xiong",
    "gao_shun",
    "chen_gong",
    "li_ru",
    "li_jue",
    "guo_si",
    "zhang_ji",
    "zhang_xiu",
    "jia_xu",
    "xun_yu",
    "xun_you",
    "cheng_yu",
    "cao_ren",
    "cao_hong",
    "cao_pi",
    "cao_zhang",
    "cao_zhi",
    "cao_ang",
    "cao_chun",
    "cao_rui",
]


def load_names() -> dict[str, str]:
    text = GALLERY.read_text(encoding="utf-8")
    rows = re.findall(r"\{slug: '([^']+)', ko: '([^']+)'", text)
    return {slug: name for slug, name in rows}


def alpha_bbox(image: Image.Image) -> tuple[int, int, int, int]:
    bbox = image.getchannel("A").getbbox()
    if not bbox:
        raise ValueError("empty transparent crop")
    return bbox


def fit_on_canvas(image: Image.Image, size: tuple[int, int], pad: int = 10) -> Image.Image:
    image = image.convert("RGBA")
    cropped = image.crop(alpha_bbox(image))
    max_w, max_h = size[0] - pad * 2, size[1] - pad * 2
    cropped.thumbnail((max_w, max_h), Image.Resampling.LANCZOS)
    canvas = Image.new("RGBA", size, (0, 0, 0, 0))
    canvas.alpha_composite(cropped, ((size[0] - cropped.width) // 2, (size[1] - cropped.height) // 2))
    return canvas


def crop_slot(sheet: Image.Image, row: str, slot: int) -> Image.Image:
    # Sheets are ten characters wide: portrait row above, body row below.
    step = sheet.width / 10
    # Keep horizontal bounds strict; neighboring characters occasionally overlap.
    left = int(slot * step)
    right = int((slot + 1) * step)
    if row == "top":
        top, bottom = 85, 425
    else:
        top, bottom = 405, 765
    return sheet.crop((left, top, right, bottom))


def make_battle_face(face: Image.Image) -> Image.Image:
    face = face.convert("RGBA")
    left, top, right, bottom = alpha_bbox(face)
    w, h = right - left, bottom - top
    cx = (left + right) / 2
    cy = top + h * 0.47
    side = max(w, h) * 0.78
    crop = face.crop((
        int(max(0, cx - side / 2)),
        int(max(0, cy - side / 2)),
        int(min(face.width, cx + side / 2)),
        int(min(face.height, cy + side / 2)),
    ))
    return fit_on_canvas(crop, TARGET_SIZE["battle_faces"], pad=0)


def save_asset(kind: str, slug: str, image: Image.Image) -> None:
    for base in (ASSETS, WWW_ASSETS):
        out = base / kind / f"{slug}.png"
        out.parent.mkdir(parents=True, exist_ok=True)
        image.save(out)


def ensure_existing_battle_faces(ids: list[str]) -> None:
    for slug in ids:
        src = ASSETS / "faces" / f"{slug}.png"
        if not src.exists():
            src = ASSETS / "busts" / f"{slug}.png"
        if not src.exists():
            continue
        battle = make_battle_face(Image.open(src))
        save_asset("battle_faces", slug, battle)


def write_manifest(ids: list[str], names: dict[str, str]) -> None:
    for base in (ASSETS, WWW_ASSETS):
        base.mkdir(parents=True, exist_ok=True)
        path = base / "manifest.csv"
        with path.open("w", encoding="utf-8", newline="") as f:
            writer = csv.writer(f)
            writer.writerow(["slug", "korean", "face", "bust", "battle_face"])
            for slug in ids:
                writer.writerow([
                    slug,
                    names.get(slug, slug),
                    f"faces/{slug}.png",
                    f"busts/{slug}.png",
                    f"battle_faces/{slug}.png",
                ])


def main() -> None:
    names = load_names()
    sheets = [
        Image.open(ASSETS / "three_kingdoms_generals_sheet_02.png").convert("RGBA"),
        Image.open(ASSETS / "three_kingdoms_generals_sheet_03.png").convert("RGBA"),
    ]

    for index, slug in enumerate(EXTRA_IDS):
        sheet = sheets[index // 10]
        slot = index % 10
        bust = fit_on_canvas(crop_slot(sheet, "bottom", slot), TARGET_SIZE["busts"], pad=8)
        face = fit_on_canvas(crop_slot(sheet, "top", slot), TARGET_SIZE["faces"], pad=4)
        battle = make_battle_face(face)
        save_asset("busts", slug, bust)
        save_asset("faces", slug, face)
        save_asset("battle_faces", slug, battle)

    # One pre-existing body had no face file in this checkout.
    li_dian_bust = ASSETS / "busts" / "li_dian.png"
    if li_dian_bust.exists():
        face = fit_on_canvas(Image.open(li_dian_bust), TARGET_SIZE["faces"], pad=0)
        save_asset("faces", "li_dian", face)

    all_ids = BASE_IDS + EXTRA_IDS
    ensure_existing_battle_faces(all_ids)
    write_manifest(all_ids, names)

    for kind in ("busts", "faces", "battle_faces"):
        count = sum(1 for slug in all_ids if (ASSETS / kind / f"{slug}.png").exists())
        print(f"{kind}: {count}/{len(all_ids)}")

    # Keep app/www in sync for files that existed before this script was added.
    for rel in ("roster_200.js",):
        src = ASSETS / rel
        if src.exists():
            dst = WWW_ASSETS / rel
            dst.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(src, dst)


if __name__ == "__main__":
    main()
