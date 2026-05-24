#!/usr/bin/env python3
from __future__ import annotations

import json
import re
import time
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
ROSTER_HTML = ROOT / "game_general_halfbody_200_final.html"
OUT_DIR = ROOT / "assets/generals/generated_fullbody_mainstyle"
HTML_OUT = ROOT / "game_general_generated_fullbody_progress.html"


def roster() -> list[dict[str, object]]:
    text = ROSTER_HTML.read_text(encoding="utf-8")
    match = re.search(r"const roster\s*=\s*(\[[\s\S]*?\]);", text)
    if not match:
        raise SystemExit("roster not found")
    return json.loads(match.group(1))


def main() -> None:
    rows = roster()
    version = str(int(time.time()))
    data = json.dumps(rows, ensure_ascii=False)
    done = sum(1 for item in rows if (OUT_DIR / f"{item['id']}.png").exists())
    html = f"""<!doctype html>
<html lang="ko">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>메인풍 전신 생성 진행</title>
<style>
:root{{color-scheme:dark;--bg:#071018;--panel:#101923;--line:#2d4056;--text:#f3efe7;--muted:#aeb9c6;--gold:#d8b15a;--ok:#77d48b;--wait:#768496}}
*{{box-sizing:border-box}}body{{margin:0;background:var(--bg);color:var(--text);font-family:Inter,system-ui,-apple-system,BlinkMacSystemFont,"Segoe UI",sans-serif}}
body::before{{content:"";position:fixed;inset:0;z-index:-1;background:url("assets/main_keyart_reference.png") center top/cover no-repeat;opacity:.14}}
header{{position:sticky;top:0;z-index:3;display:flex;align-items:center;gap:14px;padding:14px 18px;background:rgba(7,16,24,.92);border-bottom:1px solid var(--line);backdrop-filter:blur(12px)}}
h1{{margin:0;font-size:20px}}.stat{{color:var(--muted);font-size:13px}}.search{{margin-left:auto;min-width:220px;width:min(420px,34vw);background:#0b141d;color:var(--text);border:1px solid var(--line);border-radius:8px;padding:9px 11px;font-size:14px}}
main{{padding:18px}}.grid{{display:grid;grid-template-columns:repeat(auto-fill,minmax(220px,1fr));gap:14px}}.card{{overflow:hidden;border:1px solid var(--line);border-radius:8px;background:rgba(16,25,35,.95)}}.stage{{height:292px;display:flex;align-items:flex-end;justify-content:center;background:#09121b}}
.stage img{{width:100%;height:100%;object-fit:contain;object-position:center bottom;display:block}}.empty{{height:100%;display:flex;align-items:center;justify-content:center;color:var(--wait);font-weight:800}}.meta{{padding:12px 13px;background:#131f2b;min-height:94px}}.name{{display:flex;gap:8px;align-items:baseline;font-weight:900;font-size:20px}}.no{{color:var(--gold);font-size:15px;min-width:42px}}code{{display:block;margin-top:9px;color:var(--muted);font:600 12px ui-monospace,SFMono-Regular,Menlo,Consolas,monospace}}small{{display:block;margin-top:7px;color:var(--wait)}}.done small{{color:var(--ok)}}.hidden{{display:none}}
@media(max-width:680px){{header{{align-items:stretch;flex-wrap:wrap}}h1{{width:100%}}.search{{margin-left:0;width:100%}}main{{padding:12px}}.grid{{grid-template-columns:repeat(auto-fill,minmax(160px,1fr));gap:10px}}.stage{{height:224px}}.name{{font-size:18px}}}}
</style>
</head>
<body>
<header><h1>메인풍 전신 생성 진행</h1><div class="stat" id="stat">전신 PNG · {done} / 200</div><input id="search" class="search" type="search" placeholder="이름 또는 ID"></header>
<main><section id="grid" class="grid"></section></main>
<script>
const roster={data};
const version="{version}";
const grid=document.getElementById('grid');
function card(item){{
 const src=`assets/generals/generated_fullbody_mainstyle/${{item.id}}.png?v=${{version}}`;
 const done={json.dumps([item["id"] for item in rows if (OUT_DIR / f"{item['id']}.png").exists()], ensure_ascii=False)}.includes(item.id);
 const el=document.createElement('article');
 el.className='card '+(done?'done':'waiting');
 el.dataset.q=`${{item.no}} ${{item.ko}} ${{item.id}}`.toLowerCase();
 el.innerHTML=`<div class="stage">${{done?`<img loading="lazy" src="${{src}}" alt="${{item.ko}}">`:'<div class="empty">생성 대기</div>'}}</div><div class="meta"><div class="name"><span class="no">${{String(item.no).padStart(3,'0')}}.</span><span>${{item.ko}}</span></div><code>${{item.id}}</code><small>${{done?'fullbody ready':'pending'}}</small></div>`;
 return el;
}}
const cards=roster.map(card);cards.forEach(el=>grid.appendChild(el));
document.getElementById('search').addEventListener('input',e=>{{const q=e.target.value.trim().toLowerCase();cards.forEach(el=>el.classList.toggle('hidden',q&&!el.dataset.q.includes(q)))}})
</script>
</body>
</html>
"""
    HTML_OUT.write_text(html, encoding="utf-8")
    print(HTML_OUT)
    print(f"{done}/200")


if __name__ == "__main__":
    main()
