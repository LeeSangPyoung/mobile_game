from __future__ import annotations

import json
from collections import defaultdict
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def load_manifest(path: Path, group: str, asset_dir: str) -> list[dict[str, str]]:
    items = json.loads(path.read_text(encoding="utf-8"))
    for item in items:
        item["group"] = group
        item["asset_dir"] = asset_dir
    return items


def main() -> None:
    items = []
    items.extend(load_manifest(ROOT / "assets" / "generals" / "busts_extra_70_colorfit" / "manifest.json", "추가 70", "busts_extra_70_colorfit"))
    items.extend(load_manifest(ROOT / "assets" / "generals" / "busts_extra_100_colorfit" / "manifest.json", "추가 100", "busts_extra_100_colorfit"))

    by_base: dict[str, list[dict[str, str]]] = defaultdict(list)
    for item in items:
        by_base[item["base"]].append(item)

    sections = []
    for base, derived in sorted(by_base.items(), key=lambda kv: (-len(kv[1]), kv[0])):
        cards = "\n".join(
            f"""
            <section class="card">
              <div class="name">{item['ko']} <small>{item['group']}</small></div>
              <div class="art"><img src="assets/generals/{item['asset_dir']}/{item['slug']}.png?v=audit-20260511" alt="{item['ko']}"></div>
              <div class="meta">{item['slug']}.png<br>palette: {item['palette']} / emblem: {item['emblem']}</div>
            </section>
            """
            for item in derived
        )
        sections.append(
            f"""
            <section class="base">
              <header>
                <h2>{base}.png</h2>
                <span>{len(derived)} derived</span>
              </header>
              <div class="compare">
                <section class="original">
                  <div class="name">원본 베이스</div>
                  <div class="art"><img src="assets/generals/busts/{base}.png?v=audit-20260511" alt="{base}"></div>
                  <div class="meta">busts/{base}.png</div>
                </section>
                <div class="derived">{cards}</div>
              </div>
            </section>
            """
        )

    html = f"""<!DOCTYPE html>
<html lang="ko">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>장수 후보 source base 감사</title>
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
  .sub {{ margin: 0 0 22px; color: #c5a86b; font-size: 15px; line-height: 1.45; }}
  .base {{
    margin-bottom: 24px;
    border: 1px solid #79551f;
    border-radius: 8px;
    overflow: hidden;
    background: #120c07;
  }}
  header {{
    display: flex;
    justify-content: space-between;
    align-items: baseline;
    gap: 12px;
    padding: 12px 14px;
    border-bottom: 1px solid #664719;
    background: #24190f;
  }}
  h2 {{ margin: 0; font-size: 20px; }}
  header span {{ color: #8fd48a; font-weight: 800; }}
  .compare {{
    display: grid;
    grid-template-columns: 260px 1fr;
    gap: 14px;
    padding: 14px;
  }}
  .original, .card {{
    border: 1px solid #4d3616;
    border-radius: 8px;
    overflow: hidden;
    background: linear-gradient(180deg, #24190f, #110b07);
  }}
  .derived {{
    display: grid;
    grid-template-columns: repeat(auto-fill, minmax(220px, 1fr));
    gap: 12px;
  }}
  .name {{
    padding: 9px 10px;
    border-bottom: 1px solid #3d2a12;
    color: #ffe188;
    font-weight: 800;
  }}
  .name small {{ float: right; color: #8fd48a; font-size: 12px; }}
  .art {{
    height: 280px;
    display: flex;
    align-items: flex-end;
    justify-content: center;
    padding: 10px;
    background:
      linear-gradient(90deg, rgba(255,255,255,0.035) 1px, transparent 1px),
      linear-gradient(rgba(255,255,255,0.035) 1px, transparent 1px),
      radial-gradient(circle at 50% 18%, rgba(255,212,91,0.16), transparent 44%),
      #21170e;
    background-size: 28px 28px, 28px 28px, 100% 100%, 100% 100%;
  }}
  img {{
    max-width: 100%;
    max-height: 100%;
    object-fit: contain;
    filter: drop-shadow(0 14px 16px rgba(0,0,0,0.62));
  }}
  .meta {{
    min-height: 44px;
    padding: 8px 10px;
    border-top: 1px solid #3d2a12;
    color: #c5a86b;
    font-size: 12px;
    line-height: 1.35;
    word-break: break-all;
  }}
  @media (max-width: 800px) {{
    body {{ padding: 18px; }}
    .compare {{ grid-template-columns: 1fr; }}
    .derived {{ grid-template-columns: repeat(auto-fill, minmax(170px, 1fr)); }}
    .art {{ height: 240px; }}
  }}
</style>
</head>
<body>
<h1>장수 후보 source base 감사</h1>
<p class="sub">추가 70명 + 추가 100명이 어떤 원본 전신에서 파생됐는지 숨기지 않고 보여주는 검수 페이지입니다. 같은 source base에 많이 몰린 후보는 신규 캐릭터가 아니라 변형 후보로 봐야 합니다.</p>
{''.join(sections)}
</body>
</html>
"""
    (ROOT / "generals_source_clone_audit.html").write_text(html, encoding="utf-8")
    print(ROOT / "generals_source_clone_audit.html")


if __name__ == "__main__":
    main()
