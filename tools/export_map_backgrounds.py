from pathlib import Path
from PIL import Image


ROOT = Path(__file__).resolve().parents[1]
OUT_DIR = ROOT / "assets" / "maps"
GEN_DIR = Path("/Users/leesp/.codex/generated_images/019df0bc-0d1f-7180-beb4-f146aa225dc7")

SOURCES = [
    "ig_0775bc27e578c5c50169f80792b1ec8191b9da94ba0e8fefa0.png",
    "ig_0775bc27e578c5c50169f80822ce1c8191881c14e72bef2ab4.png",
    "ig_0775bc27e578c5c50169f80878c8c881919315ba3e33ba8029.png",
    "ig_0775bc27e578c5c50169f8090b86e8819195c95d897a769e1a.png",
    "ig_0775bc27e578c5c50169f809697fe4819185c0513088632380.png",
]

W, H = 307, 1024


def cover_resize(path):
    im = Image.open(path).convert("RGB")
    iw, ih = im.size
    scale = max(W / iw, H / ih)
    nw, nh = round(iw * scale), round(ih * scale)
    im = im.resize((nw, nh), Image.Resampling.LANCZOS)
    left = (nw - W) // 2
    top = max(0, (nh - H) // 2)
    return im.crop((left, top, left + W, top + H))


def main():
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    for idx, src in enumerate(SOURCES, start=1):
        cover_resize(GEN_DIR / src).save(OUT_DIR / f"chapter{idx}.png", quality=95)


if __name__ == "__main__":
    main()
