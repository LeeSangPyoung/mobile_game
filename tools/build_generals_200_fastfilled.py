#!/usr/bin/env python3
from __future__ import annotations

import html
import re
import shutil
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
OUT_DIR = ROOT / "assets/generals/busts_fast_170"
OUT_HTML = ROOT / "generals_200_final.html"
MANIFEST = ROOT / "assets/generals/busts_fast_170_manifest.tsv"
ORIGINAL_DIR = ROOT / "assets/generals/busts"
ROSTER = ROOT / "assets/generals/roster_200.js"

SOURCE_FOLDERS = [
    ("직접생성", ROOT / "assets/generals/busts_new_170"),
    ("후보70색감", ROOT / "assets/generals/busts_extra_70_colorfit"),
    ("후보100색감", ROOT / "assets/generals/busts_extra_100_colorfit"),
    ("후보70원본", ROOT / "assets/generals/busts_extra_70"),
    ("후보100원본", ROOT / "assets/generals/busts_extra_100"),
]


def rows_from_js(path: Path) -> list[tuple[str, str]]:
    if not path.exists():
        return []
    text = path.read_text(encoding="utf-8", errors="ignore")
    return re.findall(r"\['([^']+)',\s*'([^']+)'", text)


def name_map() -> dict[str, str]:
    names: dict[str, str] = {}
    for slug, name in rows_from_js(ROSTER):
        names.setdefault(slug, name)
    for html_file in [
        ROOT / "extra_70_busts_gallery_colorfit.html",
        ROOT / "extra_100_busts_gallery_colorfit.html",
        ROOT / "extra_70_busts_gallery.html",
        ROOT / "extra_100_busts_gallery.html",
    ]:
        for slug, name in rows_from_js(html_file):
            names.setdefault(slug, name)
    names.setdefault("lu_kang", "육항")
    return names


def original_rows(names: dict[str, str]) -> list[dict[str, str]]:
    roster = rows_from_js(ROSTER)
    rows = []
    for slug, name in roster[:30]:
        src = ORIGINAL_DIR / f"{slug}.png"
        rows.append(
            {
                "slug": slug,
                "name": name,
                "src": f"assets/generals/busts/{slug}.png",
                "kind": "기존 30",
                "source": "원본",
                "exists": str(src.exists()),
            }
        )
    return rows


def select_new_rows(names: dict[str, str], original_slugs: set[str]) -> list[dict[str, str]]:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    selected: list[dict[str, str]] = []
    seen = set(original_slugs)

    # Deterministic order: keep manually generated accepted files first,
    # then fill from the broadest local candidate pools.
    for source_label, folder in SOURCE_FOLDERS:
        if not folder.exists():
            continue
        for src in sorted(folder.glob("*.png")):
            slug = src.stem
            if slug in seen:
                continue
            seen.add(slug)
            dest = OUT_DIR / f"{slug}.png"
            if src.resolve() != dest.resolve():
                shutil.copy2(src, dest)
            selected.append(
                {
                    "slug": slug,
                    "name": names.get(slug, slug.replace("_", " ")),
                    "src": f"assets/generals/busts_fast_170/{slug}.png",
                    "kind": "신규 170",
                    "source": source_label,
                    "exists": "True",
                }
            )
            if len(selected) == 170:
                return selected
    raise SystemExit(f"not enough unique new candidates: {len(selected)}/170")


def card(index: int, row: dict[str, str]) -> str:
    source = row["source"]
    return f"""
  <article class="card" data-name="{html.escape(row['name'])}" data-slug="{html.escape(row['slug'])}" data-source="{html.escape(source)}">
    <div class="name"><span>{index}. {html.escape(row['name'])}</span><small>{html.escape(row['slug'])}.png</small></div>
    <div class="meta"><b>{html.escape(row['kind'])}</b><em>{html.escape(source)}</em></div>
    <div class="art"><img src="{html.escape(row['src'])}" alt="{html.escape(row['name'])}"></div>
    <div class="file">{html.escape(row['src'])}</div>
  </article>"""


def write_html(rows: list[dict[str, str]]) -> None:
    cards = "\n".join(card(i, row) for i, row in enumerate(rows, 1))
    out = f"""<!DOCTYPE html>
<html lang="ko">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>장수 200명 갤러리</title>
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
  .sub {{ margin: 0 0 22px; color: #c5a86b; font-size: 15px; line-height: 1.55; }}
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
<h1>장수 200명 갤러리</h1>
<p class="sub">1-30번은 기존 원본 고정입니다. 31-200번은 직접 생성본을 우선하고, 부족한 칸은 로컬 후보 에셋에서 중복 파일명 없이 빠르게 채운 버전입니다. 이후 눈에 띄는 복붙/유사 캐릭터는 교체 대상으로 보면 됩니다.</p>
<div class="toolbar">
  <input id="search" type="search" placeholder="이름, 파일명, 출처 검색">
  <div class="count" id="count"></div>
  <div class="audit" id="audit">이미지 {len(rows)}/200</div>
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
    const hay = `${{card.dataset.name}} ${{card.dataset.slug}} ${{card.dataset.source}}`.toLowerCase();
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
    OUT_HTML.write_text(out, encoding="utf-8")


def main() -> None:
    names = name_map()
    originals = original_rows(names)
    original_slugs = {row["slug"] for row in originals}
    new_rows = select_new_rows(names, original_slugs)
    rows = originals + new_rows
    MANIFEST.write_text(
        "\n".join([f"{i}\t{row['slug']}\t{row['name']}\t{row['source']}\t{row['src']}" for i, row in enumerate(rows, 1)]) + "\n",
        encoding="utf-8",
    )
    write_html(rows)
    print(OUT_HTML)
    print(f"images {len(rows)}/200")
    print(MANIFEST)


if __name__ == "__main__":
    main()
