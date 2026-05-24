#!/usr/bin/env python3
from __future__ import annotations

import json
import re
import time
from pathlib import Path

from PIL import Image, ImageDraw, ImageEnhance, ImageFont, ImageOps


ROOT = Path(__file__).resolve().parents[1]
ROSTER = ROOT / "assets/generals/roster_200.js"
SOURCE_DIR = ROOT / "assets/generals/new_characters/front_gaze_200_v9_height_balance"
OUT_DIR = ROOT / "assets/generals/new_characters/upper_body_200_v1_chest_below"
WORK_DIR = ROOT / "tmp/upper_body_200_v1"
CONTACT_SHEET = WORK_DIR / "upper_body_200_v1_contact_sheet.png"
HTML_OUT = ROOT / "new_generals_upper_body_200_v1.html"

CANVAS = (1024, 1280)


def load_roster() -> list[dict[str, object]]:
    text = ROSTER.read_text(encoding="utf-8")
    pairs = re.findall(r"\['([^']+)'\s*,\s*'([^']+)'\]", text)
    if len(pairs) != 200:
        raise SystemExit(f"expected 200 roster entries, got {len(pairs)}")
    return [{"no": i + 1, "id": slug, "ko": ko} for i, (slug, ko) in enumerate(pairs)]


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


def is_subject_pixel(r: int, g: int, b: int) -> bool:
    hi = max(r, g, b)
    lo = min(r, g, b)
    luma = (r * 30 + g * 59 + b * 11) // 100
    chroma = hi - lo
    return (hi > 78 and chroma > 24) or luma > 124


def detect_head_top(image: Image.Image) -> int:
    small_w = 256
    small_h = round(image.height * small_w / image.width)
    small = image.convert("RGB").resize((small_w, small_h), Image.Resampling.BILINEAR)
    pix = small.load()
    x1 = int(small_w * 0.28)
    x2 = int(small_w * 0.72)
    row_threshold = max(7, int((x2 - x1) * 0.08))
    y_min = int(small_h * 0.06)
    y_max = int(small_h * 0.46)

    rows: list[int] = []
    for y in range(y_min, y_max):
        hits = 0
        for x in range(x1, x2):
            if is_subject_pixel(*pix[x, y]):
                hits += 1
        rows.append(hits)

    for offset in range(0, max(0, len(rows) - 3)):
        if sum(rows[offset : offset + 4]) >= row_threshold * 4:
            top_small = y_min + offset
            top = round(top_small * image.height / small_h)
            if int(image.height * 0.08) <= top <= int(image.height * 0.38):
                return top
            break
    return int(image.height * 0.18)


def detect_center_x(image: Image.Image, y1: int, y2: int) -> int:
    small_w = 256
    small_h = round(image.height * small_w / image.width)
    small = image.convert("RGB").resize((small_w, small_h), Image.Resampling.BILINEAR)
    pix = small.load()

    sy1 = max(0, round(y1 * small_h / image.height))
    sy2 = min(small_h, round(y2 * small_h / image.height))
    sx1 = int(small_w * 0.18)
    sx2 = int(small_w * 0.82)

    total_weight = 0
    weighted_x = 0
    for y in range(sy1, sy2):
        for x in range(sx1, sx2):
            r, g, b = pix[x, y]
            if not is_subject_pixel(r, g, b):
                continue
            hi = max(r, g, b)
            lo = min(r, g, b)
            weight = max(1, hi - lo + hi // 4)
            total_weight += weight
            weighted_x += x * weight

    if not total_weight:
        return image.width // 2
    center_small = weighted_x / total_weight
    center = round(center_small * image.width / small_w)
    return max(int(image.width * 0.34), min(int(image.width * 0.66), center))


def make_upper_body(source: Image.Image) -> Image.Image:
    source = source.convert("RGB")
    width, height = source.size
    head_top = detect_head_top(source)
    crop_top = max(0, int(head_top - height * 0.055))
    crop_h = int(height * 0.54)
    crop_w = int(crop_h * CANVAS[0] / CANVAS[1])
    center_x = detect_center_x(source, crop_top, min(height, crop_top + int(height * 0.34)))

    left = center_x - crop_w // 2
    right = left + crop_w
    if left < 0:
        right -= left
        left = 0
    if right > width:
        left -= right - width
        right = width
    top = crop_top
    bottom = min(height, top + crop_h)
    if bottom - top < crop_h:
        top = max(0, bottom - crop_h)

    crop = source.crop((left, top, right, bottom))
    crop = crop.resize(CANVAS, Image.Resampling.LANCZOS)

    # The source already has the target 3D render style. These tiny adjustments
    # compensate for the tighter crop and keep the HTML grid crisp.
    crop = ImageEnhance.Contrast(crop).enhance(1.04)
    crop = ImageEnhance.Sharpness(crop).enhance(1.08)
    crop = ImageEnhance.Color(crop).enhance(1.03)
    return crop


def build_images(roster: list[dict[str, object]]) -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    for item in roster:
        slug = str(item["id"])
        source_path = SOURCE_DIR / f"{slug}_front_gaze_v1.png"
        if not source_path.exists():
            raise SystemExit(f"missing source image: {source_path}")
        image = Image.open(source_path)
        out = make_upper_body(image)
        out.save(OUT_DIR / f"{slug}_upper_body_v1.png", optimize=True)


def write_contact_sheet(roster: list[dict[str, object]]) -> None:
    WORK_DIR.mkdir(parents=True, exist_ok=True)
    columns = 10
    cell_w, cell_h = 154, 216
    header_h = 34
    rows = (len(roster) + columns - 1) // columns
    sheet = Image.new("RGB", (columns * cell_w, header_h + rows * cell_h), (12, 9, 6))
    draw = ImageDraw.Draw(sheet)
    title_font = load_font(18)
    name_font = load_font(11)
    id_font = load_font(9)
    draw.text((10, 7), "상반신 200 v1 - 머리 위부터 가슴 아래", fill=(245, 224, 185), font=title_font)

    for index, item in enumerate(roster):
        slug = str(item["id"])
        image = Image.open(OUT_DIR / f"{slug}_upper_body_v1.png").convert("RGB")
        thumb = ImageOps.contain(image, (cell_w, 170))
        tile = Image.new("RGB", (cell_w, cell_h), (22, 16, 11))
        tile.paste(thumb, ((cell_w - thumb.width) // 2, 0))
        td = ImageDraw.Draw(tile)
        td.text((6, 176), f"{int(item['no']):03d}. {item['ko']}", fill=(245, 224, 185), font=name_font)
        td.text((6, 193), slug, fill=(170, 145, 104), font=id_font)
        x = (index % columns) * cell_w
        y = header_h + (index // columns) * cell_h
        sheet.paste(tile, (x, y))

    sheet.save(CONTACT_SHEET)


def write_html(roster: list[dict[str, object]]) -> None:
    version = str(int(time.time()))
    roster_js = json.dumps(roster, ensure_ascii=False)
    html = f"""<!doctype html>
<html lang="ko">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>전신 기준 상반신 장수 200명 v1</title>
<style>
* {{ box-sizing: border-box; }}
:root {{ color-scheme: dark; --bg:#130f0b; --panel:#211913; --panel2:#17110d; --line:rgba(244,223,184,.18); --gold:#ffd36a; --text:#f4dfb8; --muted:#bfa986; }}
body {{ margin:0; background:var(--bg); color:var(--text); font-family:-apple-system,BlinkMacSystemFont,"Apple SD Gothic Neo","Noto Sans KR",sans-serif; }}
header {{ position:sticky; top:0; z-index:5; display:flex; align-items:center; gap:14px; padding:16px 20px 13px; background:rgba(20,16,12,.94); border-bottom:1px solid var(--line); backdrop-filter:blur(10px); }}
h1 {{ margin:0; font-size:22px; font-weight:850; letter-spacing:0; white-space:nowrap; }}
.note {{ color:#cbb894; font-size:13px; line-height:1.45; white-space:nowrap; }}
.search {{ margin-left:auto; min-width:220px; width:min(380px,32vw); padding:9px 11px; border:1px solid rgba(244,223,184,.22); border-radius:8px; background:#100c09; color:var(--text); outline:none; font-size:14px; }}
main {{ padding:18px 20px 24px; }}
.grid {{ display:grid; grid-template-columns:repeat(auto-fill,minmax(290px,1fr)); gap:16px; }}
article {{ overflow:hidden; border:1px solid rgba(244,223,184,.17); border-radius:8px; background:var(--panel); box-shadow:0 10px 22px rgba(0,0,0,.22); }}
.pair {{ display:grid; grid-template-columns:1fr 1fr; gap:1px; background:rgba(244,223,184,.16); }}
.art {{ position:relative; aspect-ratio:4/5; background:#0f0c09; overflow:hidden; }}
.art img {{ display:block; width:100%; height:100%; object-fit:cover; }}
.art.full img {{ object-fit:cover; object-position:center 30%; }}
.badge {{ position:absolute; top:8px; left:8px; z-index:1; padding:3px 7px 4px; border-radius:6px; background:rgba(13,9,6,.72); border:1px solid rgba(255,211,106,.32); color:var(--gold); font-size:11px; font-weight:800; }}
.meta {{ padding:10px 11px 12px; }}
.name {{ display:flex; justify-content:space-between; align-items:baseline; gap:8px; margin:0 0 7px; font-size:15px; font-weight:800; }}
.name small {{ color:#9e8a67; font-size:11px; font-weight:700; }}
a {{ display:block; overflow-wrap:anywhere; color:var(--gold); font-size:11px; line-height:1.35; text-decoration:none; }}
a:hover {{ text-decoration:underline; }}
.hidden {{ display:none; }}
@media (max-width:720px) {{
  header {{ flex-wrap:wrap; align-items:stretch; }}
  h1 {{ width:100%; font-size:19px; white-space:normal; }}
  .note {{ width:100%; white-space:normal; }}
  .search {{ margin-left:0; width:100%; }}
  main {{ padding:12px; }}
  .grid {{ grid-template-columns:1fr; gap:12px; }}
}}
</style>
</head>
<body>
<header>
  <h1>전신 기준 상반신 장수 200명 v1</h1>
  <div class="note">v9 전신 원본을 같은 그림체로 머리 위부터 가슴 아래까지 리프레이밍한 검수본입니다.</div>
  <input id="search" class="search" type="search" placeholder="이름 또는 ID 검색" autocomplete="off">
</header>
<main><section id="grid" class="grid"></section></main>
<script>
const roster = {roster_js};
const version = "{version}";
const grid = document.getElementById('grid');
function card(item) {{
  const no = String(item.no).padStart(3, '0');
  const full = `./assets/generals/new_characters/front_gaze_200_v9_height_balance/${{item.id}}_front_gaze_v1.png?v=${{version}}`;
  const upper = `./assets/generals/new_characters/upper_body_200_v1_chest_below/${{item.id}}_upper_body_v1.png?v=${{version}}`;
  const el = document.createElement('article');
  el.dataset.q = `${{item.no}} ${{item.ko}} ${{item.id}}`.toLowerCase();
  el.innerHTML = `
    <div class="pair">
      <div class="art full"><span class="badge">전신</span><img loading="lazy" src="${{full}}" alt="${{item.ko}} 전신"></div>
      <div class="art"><span class="badge">상반신</span><img loading="lazy" src="${{upper}}" alt="${{item.ko}} 상반신"></div>
    </div>
    <div class="meta">
      <p class="name"><span>${{item.ko}}</span><small>${{no}} · ${{item.id}}</small></p>
      <a href="${{upper}}">${{upper}}</a>
    </div>`;
  return el;
}}
const cards = roster.map(card);
cards.forEach(el => grid.appendChild(el));
document.getElementById('search').addEventListener('input', event => {{
  const q = event.target.value.trim().toLowerCase();
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
    write_contact_sheet(roster)
    write_html(roster)
    print(f"wrote {len(roster)} images to {OUT_DIR}")
    print(CONTACT_SHEET)
    print(HTML_OUT)


if __name__ == "__main__":
    main()
