#!/usr/bin/env python3
from __future__ import annotations

import json
import re
import time
from pathlib import Path

from PIL import Image, ImageChops, ImageDraw, ImageEnhance, ImageFilter, ImageFont, ImageOps


ROOT = Path(__file__).resolve().parents[1]
ROSTER_HTML = ROOT / "game_general_halfbody_200_final.html"
SOURCE_DIR = ROOT / "assets/generals/busts"
FULLBODY_DIR = ROOT / "assets/generals/mainstyle_fullbody"
HALFBODY_DIR = ROOT / "assets/generals/mainstyle_halfbody"
WORK_DIR = ROOT / "tmp/mainstyle_400"
HTML_OUT = ROOT / "game_general_mainstyle_400_gallery.html"
CANVAS = (640, 768)


def load_roster() -> list[dict[str, object]]:
    text = ROSTER_HTML.read_text(encoding="utf-8")
    match = re.search(r"const roster\s*=\s*(\[[\s\S]*?\]);", text)
    if not match:
        raise SystemExit(f"could not find roster in {ROSTER_HTML}")
    roster = json.loads(match.group(1))
    if len(roster) != 200:
        raise SystemExit(f"expected 200 roster entries, got {len(roster)}")
    return roster


def load_font(size: int) -> ImageFont.ImageFont:
    candidates = [
        Path("/System/Library/Fonts/AppleSDGothicNeo.ttc"),
        Path("/System/Library/Fonts/Supplemental/AppleGothic.ttf"),
        Path("/Library/Fonts/Arial Unicode.ttf"),
    ]
    for path in candidates:
        if path.exists():
            try:
                return ImageFont.truetype(str(path), size)
            except OSError:
                pass
    return ImageFont.load_default()


def alpha_bbox(image: Image.Image) -> tuple[int, int, int, int]:
    bbox = image.convert("RGBA").getbbox()
    if not bbox:
        raise ValueError("empty transparent source")
    return bbox


def fit_on_canvas(subject: Image.Image, max_w: int, max_h: int, bottom: int) -> Image.Image:
    subject = subject.convert("RGBA")
    crop = subject.crop(alpha_bbox(subject))
    crop.thumbnail((max_w, max_h), Image.Resampling.LANCZOS)
    out = Image.new("RGBA", CANVAS, (0, 0, 0, 0))
    x = (CANVAS[0] - crop.width) // 2
    y = max(8, bottom - crop.height)
    out.alpha_composite(crop, (x, y))
    return out


def fit_on_canvas_top(subject: Image.Image, max_w: int, max_h: int, top: int) -> Image.Image:
    subject = subject.convert("RGBA")
    crop = subject.crop(alpha_bbox(subject))
    crop.thumbnail((max_w, max_h), Image.Resampling.LANCZOS)
    out = Image.new("RGBA", CANVAS, (0, 0, 0, 0))
    x = (CANVAS[0] - crop.width) // 2
    y = min(max(8, top), CANVAS[1] - crop.height - 8)
    out.alpha_composite(crop, (x, y))
    return out


def add_style_finish(image: Image.Image) -> Image.Image:
    image = image.convert("RGBA")
    alpha = image.getchannel("A")

    rgb = image.convert("RGB")
    rgb = ImageEnhance.Color(rgb).enhance(1.15)
    rgb = ImageEnhance.Contrast(rgb).enhance(1.12)
    rgb = ImageEnhance.Sharpness(rgb).enhance(1.18)
    rgb = ImageEnhance.Brightness(rgb).enhance(1.02)
    subject = Image.merge("RGBA", (*rgb.split(), alpha))

    shadow_mask = alpha.filter(ImageFilter.GaussianBlur(12))
    shadow = Image.new("RGBA", CANVAS, (0, 0, 0, 0))
    shadow_color = Image.new("RGBA", CANVAS, (11, 8, 5, 82))
    shadow.alpha_composite(Image.composite(shadow_color, shadow, shadow_mask), (10, 14))

    wide_glow_mask = alpha.filter(ImageFilter.MaxFilter(11)).filter(ImageFilter.GaussianBlur(6))
    warm_glow = Image.new("RGBA", CANVAS, (255, 126, 37, 0))
    warm_glow.putalpha(ImageEnhance.Brightness(wide_glow_mask).enhance(0.11))

    edge_mask = ImageChops.subtract(alpha.filter(ImageFilter.MaxFilter(7)), alpha)
    edge_mask = edge_mask.filter(ImageFilter.GaussianBlur(0.6))
    gold_edge = Image.new("RGBA", CANVAS, (245, 174, 66, 0))
    gold_edge.putalpha(ImageEnhance.Brightness(edge_mask).enhance(0.55))

    # Warm key-art rim from the upper right, matching the firelit main screen.
    rim_src = Image.new("L", CANVAS, 0)
    rim_draw = ImageDraw.Draw(rim_src)
    for x in range(CANVAS[0]):
        strength = int(120 * (x / CANVAS[0]) ** 1.8)
        rim_draw.line((x, 0, x, CANVAS[1]), fill=strength)
    rim_mask = ImageChops.multiply(alpha.filter(ImageFilter.FIND_EDGES).filter(ImageFilter.GaussianBlur(1.0)), rim_src)
    rim = Image.new("RGBA", CANVAS, (255, 195, 95, 0))
    rim.putalpha(ImageEnhance.Brightness(rim_mask).enhance(0.85))

    out = Image.new("RGBA", CANVAS, (0, 0, 0, 0))
    out.alpha_composite(shadow)
    out.alpha_composite(warm_glow)
    out.alpha_composite(gold_edge)
    out.alpha_composite(subject)
    out.alpha_composite(rim)
    return out


def make_fullbody(source: Image.Image) -> Image.Image:
    fitted = fit_on_canvas(source, max_w=622, max_h=714, bottom=746)
    return add_style_finish(fitted)


def make_halfbody(fullbody: Image.Image) -> Image.Image:
    bbox = alpha_bbox(fullbody)
    left, top, right, bottom = bbox
    height = bottom - top
    crop_bottom = min(bottom, int(top + height * 0.64))
    center_x = (left + right) // 2
    crop_half_w = 235
    pad_top = 10
    crop_box = (
        max(0, center_x - crop_half_w),
        max(0, top - pad_top),
        min(CANVAS[0], center_x + crop_half_w),
        max(top + 1, crop_bottom),
    )
    crop = fullbody.crop(crop_box)
    fitted = fit_on_canvas_top(crop, max_w=640, max_h=724, top=42)
    return add_style_finish(fitted)


def build_images(roster: list[dict[str, object]]) -> None:
    FULLBODY_DIR.mkdir(parents=True, exist_ok=True)
    HALFBODY_DIR.mkdir(parents=True, exist_ok=True)
    for item in roster:
        slug = str(item["id"])
        source_path = SOURCE_DIR / f"{slug}.png"
        if not source_path.exists():
            raise SystemExit(f"missing source: {source_path}")
        source = Image.open(source_path).convert("RGBA")
        fullbody = make_fullbody(source)
        halfbody = make_halfbody(fullbody)
        fullbody.save(FULLBODY_DIR / f"{slug}.png")
        halfbody.save(HALFBODY_DIR / f"{slug}.png")


def write_contact_sheet(roster: list[dict[str, object]], image_dir: Path, out_path: Path, title: str) -> None:
    columns = 10
    cell_w, cell_h = 154, 218
    top_h = 28
    rows = (len(roster) + columns - 1) // columns
    sheet = Image.new("RGBA", (columns * cell_w, top_h + rows * cell_h), (7, 11, 17, 255))
    draw = ImageDraw.Draw(sheet)
    title_font = load_font(17)
    name_font = load_font(11)
    slug_font = load_font(9)
    draw.text((10, 5), title, fill=(239, 230, 205, 255), font=title_font)

    for index, item in enumerate(roster):
        slug = str(item["id"])
        image = Image.open(image_dir / f"{slug}.png").convert("RGBA")
        bg = Image.new("RGBA", CANVAS, (15, 21, 30, 255))
        bg.alpha_composite(image)
        thumb = ImageOps.contain(bg, (cell_w, 178))
        tile = Image.new("RGBA", (cell_w, cell_h), (9, 14, 21, 255))
        tile.alpha_composite(thumb, ((cell_w - thumb.width) // 2, 0))
        td = ImageDraw.Draw(tile)
        td.text((5, 183), f"{int(item['no']):03d}. {item['ko']}", fill=(236, 235, 226, 255), font=name_font)
        td.text((5, 198), slug, fill=(158, 169, 183, 255), font=slug_font)
        x = (index % columns) * cell_w
        y = top_h + (index // columns) * cell_h
        sheet.alpha_composite(tile, (x, y))

    out_path.parent.mkdir(parents=True, exist_ok=True)
    sheet.save(out_path)


def write_html(roster: list[dict[str, object]]) -> None:
    version = str(int(time.time()))
    roster_js = json.dumps(roster, ensure_ascii=False)
    html = f"""<!doctype html>
<html lang="ko">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>삼국지 장수 메인풍 400</title>
<style>
:root {{ color-scheme:dark; --bg:#070a0d; --panel:#111820; --panel2:#151f2b; --line:#314052; --text:#f3eee4; --muted:#aeb8c5; --gold:#dfb864; --red:#b44637; }}
* {{ box-sizing:border-box; }}
body {{ margin:0; background:#070a0d; color:var(--text); font-family:Inter,ui-sans-serif,system-ui,-apple-system,BlinkMacSystemFont,"Segoe UI",sans-serif; }}
body::before {{ content:""; position:fixed; inset:0; z-index:-2; background:url("assets/main_keyart_reference.png") center top/cover no-repeat; opacity:.18; filter:saturate(1.05) contrast(1.08); }}
body::after {{ content:""; position:fixed; inset:0; z-index:-1; background:linear-gradient(180deg,rgba(7,10,13,.62),#070a0d 52%,#070a0d); }}
header {{ position:sticky; top:0; z-index:5; display:flex; align-items:center; gap:14px; padding:14px 18px; background:rgba(7,10,13,.9); border-bottom:1px solid rgba(223,184,100,.3); backdrop-filter:blur(12px); }}
h1 {{ margin:0; font-size:20px; letter-spacing:0; white-space:nowrap; }}
.stat {{ color:var(--muted); font-size:13px; white-space:nowrap; }}
.search {{ margin-left:auto; min-width:220px; width:min(420px,34vw); background:#0d141c; color:var(--text); border:1px solid var(--line); border-radius:8px; padding:9px 11px; font-size:14px; outline:none; }}
main {{ padding:18px; }}
.grid {{ display:grid; grid-template-columns:repeat(auto-fill,minmax(320px,1fr)); gap:14px; }}
.card {{ overflow:hidden; border:1px solid rgba(223,184,100,.25); border-radius:8px; background:linear-gradient(180deg,rgba(21,31,43,.95),rgba(13,19,27,.96)); box-shadow:0 12px 32px rgba(0,0,0,.28); }}
.showcase {{ display:grid; grid-template-columns:1fr 1fr; gap:1px; background:rgba(223,184,100,.18); }}
.stage {{ position:relative; height:340px; display:flex; align-items:flex-end; justify-content:center; overflow:hidden; background:#111820; }}
.stage::before {{ content:""; position:absolute; inset:0; background:url("assets/main_keyart_reference.png") center/cover no-repeat; opacity:.26; filter:contrast(1.15) saturate(1.1); }}
.stage::after {{ content:""; position:absolute; inset:0; background:radial-gradient(circle at 64% 22%,rgba(255,171,70,.24),transparent 31%),linear-gradient(180deg,rgba(4,7,10,.25),rgba(4,7,10,.8)); }}
.stage img {{ position:relative; z-index:1; width:100%; height:100%; object-fit:contain; object-position:center bottom; display:block; }}
.badge {{ position:absolute; left:8px; top:8px; z-index:2; padding:4px 7px; border:1px solid rgba(223,184,100,.35); border-radius:6px; background:rgba(7,10,13,.74); color:#f3d189; font-size:12px; font-weight:800; }}
.meta {{ display:flex; align-items:center; gap:10px; padding:12px 13px 13px; background:rgba(13,19,27,.98); min-height:72px; }}
.no {{ color:var(--gold); font-weight:900; font-size:15px; min-width:42px; }}
.name {{ font-size:20px; font-weight:900; line-height:1.15; }}
code {{ display:block; margin-top:5px; color:var(--muted); font:600 12px ui-monospace,SFMono-Regular,Menlo,Consolas,monospace; white-space:nowrap; overflow:hidden; text-overflow:ellipsis; }}
.hidden {{ display:none; }}
@media(max-width:720px) {{ header {{ align-items:stretch; flex-wrap:wrap; }} h1 {{ width:100%; }} .search {{ margin-left:0; width:100%; }} main {{ padding:12px; }} .grid {{ grid-template-columns:1fr; gap:12px; }} .stage {{ height:300px; }} .name {{ font-size:18px; }} }}
</style>
</head>
<body>
<header>
  <h1>삼국지 장수 메인풍 400</h1>
  <div class="stat" id="stat">전신 200 · 반신 200</div>
  <input id="search" class="search" type="search" placeholder="이름 또는 ID" autocomplete="off">
</header>
<main><section id="grid" class="grid"></section></main>
<script>
const roster = {roster_js};
const version = "{version}";
const grid = document.getElementById('grid');
function card(item) {{
  const el = document.createElement('article');
  el.className = 'card';
  el.dataset.q = `${{item.no}} ${{item.ko}} ${{item.id}}`.toLowerCase();
  const no = String(item.no).padStart(3, '0');
  el.innerHTML = `
    <div class="showcase">
      <div class="stage"><span class="badge">전신</span><img loading="lazy" src="assets/generals/mainstyle_fullbody/${{item.id}}.png?v=${{version}}" alt="${{item.ko}} 전신"></div>
      <div class="stage"><span class="badge">반신</span><img loading="lazy" src="assets/generals/mainstyle_halfbody/${{item.id}}.png?v=${{version}}" alt="${{item.ko}} 반신"></div>
    </div>
    <div class="meta">
      <div class="no">${{no}}.</div>
      <div><div class="name">${{item.ko}}</div><code>${{item.id}}</code></div>
    </div>`;
  return el;
}}
const cards = roster.map(card);
cards.forEach(el => grid.appendChild(el));
document.getElementById('search').addEventListener('input', e => {{
  const q = e.target.value.trim().toLowerCase();
  cards.forEach(el => el.classList.toggle('hidden', q && !el.dataset.q.includes(q)));
}});
</script>
</body>
</html>
"""
    HTML_OUT.write_text(html, encoding="utf-8")


def main() -> None:
    roster = load_roster()
    build_images(roster)
    WORK_DIR.mkdir(parents=True, exist_ok=True)
    write_contact_sheet(roster, FULLBODY_DIR, WORK_DIR / "mainstyle_fullbody_contact.png", "mainstyle fullbody 200")
    write_contact_sheet(roster, HALFBODY_DIR, WORK_DIR / "mainstyle_halfbody_contact.png", "mainstyle halfbody 200")
    write_html(roster)
    print(f"fullbody: {len(list(FULLBODY_DIR.glob('*.png')))}")
    print(f"halfbody: {len(list(HALFBODY_DIR.glob('*.png')))}")
    print(HTML_OUT)
    print(WORK_DIR / "mainstyle_fullbody_contact.png")
    print(WORK_DIR / "mainstyle_halfbody_contact.png")


if __name__ == "__main__":
    main()
