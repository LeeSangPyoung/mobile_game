from pathlib import Path
import shutil

from PIL import Image


ROOT = Path(__file__).resolve().parents[1]
BATTLE_DIR = ROOT / "assets" / "generals" / "battle_faces"
BACKUP_DIR = BATTLE_DIR / "_backup_before_closeup_20260509_232130"

# Per-character framing nudges. Positive y moves the crop lower; negative y moves it higher.
TWEAKS = {
    "cao_cao": (0.78, 0.48, 0.00, 0.00),
    "cao_xing": (0.76, 0.50, 0.03, 0.00),
    "gan_ning": (0.76, 0.50, 0.03, 0.00),
    "lu_xun": (0.76, 0.50, 0.03, 0.00),
    "yuan_shao": (0.78, 0.50, 0.04, 0.00),
    "zhang_liao": (0.76, 0.50, 0.04, 0.00),
    "zhao_yun": (0.76, 0.50, 0.04, 0.00),
    "zhou_yu": (0.76, 0.50, 0.06, 0.00),
    "zhuge_liang": (0.76, 0.50, 0.03, 0.00),
}


def clamp(value, low, high):
    return max(low, min(high, value))


def closeup(path):
    image = Image.open(path).convert("RGBA")
    alpha = image.getchannel("A")
    bbox = alpha.getbbox()
    if bbox is None:
        return False

    left, top, right, bottom = bbox
    width = right - left
    height = bottom - top
    scale, y_ratio, x_nudge, y_nudge = TWEAKS.get(path.stem, (0.76, 0.50, 0.0, 0.00))
    side = int(max(width, height) * scale)
    side = clamp(side, 180, min(image.width, image.height))

    cx = (left + right) / 2 + width * x_nudge
    cy = top + height * y_ratio + height * y_nudge

    crop_left = int(round(cx - side / 2))
    crop_top = int(round(cy - side / 2))
    crop_left = clamp(crop_left, 0, image.width - side)
    crop_top = clamp(crop_top, 0, image.height - side)

    crop = image.crop((crop_left, crop_top, crop_left + side, crop_top + side))
    result = crop.resize((512, 512), Image.Resampling.LANCZOS)
    result.save(path)
    return True


def main():
    BACKUP_DIR.mkdir(exist_ok=True)
    for path in sorted(BATTLE_DIR.glob("*.png")):
        backup = BACKUP_DIR / path.name
        if not backup.exists():
            shutil.copy2(path, backup)
        else:
            shutil.copy2(backup, path)
        closeup(path)
    print(f"rewrote {len(list(BATTLE_DIR.glob('*.png')))} battle face images")
    print(f"backup: {BACKUP_DIR.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
