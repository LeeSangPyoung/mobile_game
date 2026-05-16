#!/usr/bin/env python3
from __future__ import annotations

import html
import re
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
ROSTER = ROOT / "assets/generals/roster_200.js"
OUT = ROOT / "generals_200_final.html"
ORIGINAL_DIR = "assets/generals/busts"
NEW_DIR = "assets/generals/busts_new_170"


def read_roster() -> list[tuple[str, str]]:
    text = ROSTER.read_text(encoding="utf-8")
    rows = re.findall(r"\['([^']+)',\s*'([^']+)'\]", text)
    if len(rows) < 30:
        raise SystemExit("roster_200.js must contain at least 30 generals")
    return rows


def make_final_roster() -> list[tuple[str, str, str]]:
    roster = read_roster()
    originals = [(slug, name, "기존 30") for slug, name in roster[:30]]

    seen = {slug for slug, _, _ in originals}
    new_rows: list[tuple[str, str, str]] = []

    # Lu Kang was the first accepted new-direction sample and is not in the old roster.
    priority = [("lu_kang", "육항")]
    for slug, name in priority + roster[30:]:
        if slug in seen:
            continue
        seen.add(slug)
        new_rows.append((slug, name, "신규 170"))
        if len(new_rows) == 170:
            break

    if len(new_rows) != 170:
        raise SystemExit(f"need 170 new rows, got {len(new_rows)}")

    return originals + new_rows


def card(index: int, slug: str, name: str, group: str) -> str:
    if index <= 30:
        src = f"{ORIGINAL_DIR}/{slug}.png"
        status = "원본 고정"
        missing = not (ROOT / src).exists()
    else:
        src = f"{NEW_DIR}/{slug}.png"
        status = "완료" if (ROOT / src).exists() else "렌더 필요"
        missing = not (ROOT / src).exists()

    cls = "card missing" if missing else "card"
    img = (
        f'<img src="{html.escape(src)}" alt="{html.escape(name)}">'
        if not missing
        else '<div class="empty">렌더 필요</div>'
    )
    return f"""
  <article class="{cls}" data-name="{html.escape(name)}" data-slug="{html.escape(slug)}" data-status="{status}">
    <div class="name"><span>{index}. {html.escape(name)}</span><small>{html.escape(slug)}.png</small></div>
    <div class="meta"><b>{html.escape(group)}</b><em>{html.escape(status)}</em></div>
    <div class="art">{img}</div>
    <div class="file">{html.escape(src)}</div>
  </article>"""


def main() -> None:
    rows = make_final_roster()
    done = 0
    for index, (slug, _, _) in enumerate(rows, 1):
        src = ROOT / (f"{ORIGINAL_DIR}/{slug}.png" if index <= 30 else f"{NEW_DIR}/{slug}.png")
        done += int(src.exists())

    cards = "\n".join(card(i, slug, name, group) for i, (slug, name, group) in enumerate(rows, 1))
    out = f"""<!DOCTYPE html>
<html lang="ko">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>장수 200명 최종 갤러리</title>
<style>
  * {{ box-sizing: border-box; }}
  body {{
    margin: 0;
    padding: 28px;
    background: #17110b;
    color: #f7d56e;
    font-family: -apple-system, BlinkMacSystemFont, "Apple SD Gothic Neo", sans-serif;
  }}
  h1 {{ margin: 0 0 8px; font-size: 30px; }}
  .sub {{ margin: 0 0 22px; color: #c5a86b; font-size: 15px; }}
  .toolbar {{
    position: sticky;
    top: 0;
    z-index: 2;
    display: flex;
    gap: 12px;
    align-items: center;
    padding: 12px 0 16px;
    background: linear-gradient(180deg, #17110b 70%, rgba(23,17,11,0));
  }}
  input {{
    width: min(420px, 100%);
    height: 42px;
    padding: 0 14px;
    border: 1px solid #7b5724;
    border-radius: 8px;
    background: #24190f;
    color: #ffe188;
    font-size: 15px;
    outline: none;
  }}
  .count {{ color: #a98a50; font-size: 15px; font-weight: 800; white-space: nowrap; }}
  .audit {{ margin-left: auto; color: #8fd48a; font-size: 15px; font-weight: 900; white-space: nowrap; }}
  .grid {{
    display: grid;
    grid-template-columns: repeat(auto-fill, minmax(250px, 1fr));
    gap: 18px;
  }}
  .card {{
    min-width: 0;
    border: 1px solid #79551f;
    border-radius: 8px;
    overflow: hidden;
    background: linear-gradient(180deg, #24190f, #110b07);
  }}
  .missing {{ opacity: 0.72; }}
  .name {{
    display: flex;
    justify-content: space-between;
    gap: 10px;
    align-items: baseline;
    padding: 12px 14px 8px;
    color: #ffe188;
    font-size: 19px;
    font-weight: 900;
  }}
  .name small {{
    min-width: 0;
    color: #a98a50;
    font-size: 12px;
    font-weight: 800;
    text-align: right;
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
  }}
  .meta {{
    display: flex;
    justify-content: space-between;
    gap: 10px;
    padding: 0 14px 11px;
    border-bottom: 1px solid #664719;
    color: #82c875;
    font-size: 12px;
    font-weight: 900;
  }}
  .meta em {{ color: #d2b36b; font-style: normal; }}
  .missing .meta em {{ color: #ff9a7a; }}
  .art {{
    height: 370px;
    display: flex;
    align-items: flex-end;
    justify-content: center;
    padding: 14px;
    background:
      linear-gradient(90deg, rgba(255,255,255,0.035) 1px, transparent 1px),
      linear-gradient(rgba(255,255,255,0.035) 1px, transparent 1px),
      radial-gradient(circle at 50% 18%, rgba(255,212,91,0.16), transparent 44%),
      #21170e;
    background-size: 30px 30px, 30px 30px, 100% 100%, 100% 100%;
  }}
  img {{
    display: block;
    max-width: 100%;
    max-height: 100%;
    object-fit: contain;
    filter: drop-shadow(0 14px 16px rgba(0,0,0,0.62));
  }}
  .empty {{
    align-self: center;
    color: #ff9a7a;
    font-size: 15px;
    font-weight: 900;
  }}
  .file {{
    padding: 9px 12px 11px;
    border-top: 1px solid #3d2a12;
    color: #f7d56e;
    font-size: 12px;
    word-break: break-all;
  }}
  @media (max-width: 720px) {{
    body {{ padding: 18px; }}
    h1 {{ font-size: 24px; }}
    .toolbar {{ align-items: flex-start; flex-direction: column; }}
    .audit {{ margin-left: 0; }}
    .grid {{ grid-template-columns: repeat(auto-fill, minmax(175px, 1fr)); }}
    .art {{ height: 275px; }}
  }}
</style>
</head>
<body>
<h1>장수 200명 최종 갤러리</h1>
<p class="sub">1-30번은 기존 원본 고정, 31-200번은 새로 만든 장수만 들어가는 자리입니다. 복사/색변환 후보 폴더는 사용하지 않습니다.</p>
<div class="toolbar">
  <input id="search" type="search" placeholder="이름 또는 파일명 검색">
  <div class="count" id="count"></div>
  <div class="audit" id="audit">이미지 {done}/200</div>
</div>
<main class="grid" id="grid">
{cards}
</main>
<script>
const cards = [...document.querySelectorAll('.card')];
const search = document.getElementById('search');
const count = document.getElementById('count');
function update() {{
  const q = search.value.trim().toLowerCase();
  let visible = 0;
  for (const card of cards) {{
    const hay = `${{card.dataset.name}} ${{card.dataset.slug}} ${{card.dataset.status}}`.toLowerCase();
    const show = !q || hay.includes(q);
    card.style.display = show ? '' : 'none';
    if (show) visible++;
  }}
  count.textContent = `${{visible}} / ${{cards.length}}`;
}}
search.addEventListener('input', update);
update();
</script>
</body>
</html>
"""
    OUT.write_text(out, encoding="utf-8")
    print(OUT)
    print(f"images {done}/200")


if __name__ == "__main__":
    main()
