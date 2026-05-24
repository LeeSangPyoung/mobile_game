#!/usr/bin/env python3
from __future__ import annotations

import json
import re
import time
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
ROSTER = ROOT / "assets/generals/roster_200.js"
SOURCE_DIR = ROOT / "assets/generals/new_characters/front_gaze_200_v9_height_balance"
OUT_DIR = ROOT / "assets/generals/new_characters/upper_body_200_redraw_v1"
WORK_DIR = ROOT / "tmp/upper_body_200_redraw_v1"
PROMPT_DIR = WORK_DIR / "prompts"
JOBS_JSON = WORK_DIR / "jobs.json"
HTML_OUT = ROOT / "new_generals_upper_body_200_redraw_v1.html"


def load_roster() -> list[dict[str, object]]:
    text = ROSTER.read_text(encoding="utf-8")
    pairs = re.findall(r"\['([^']+)'\s*,\s*'([^']+)'\]", text)
    if len(pairs) != 200:
        raise SystemExit(f"expected 200 roster entries, got {len(pairs)}")
    return [{"no": i + 1, "id": slug, "ko": ko} for i, (slug, ko) in enumerate(pairs)]


def prompt_for(item: dict[str, object]) -> str:
    ko = str(item["ko"])
    slug = str(item["id"])
    no = int(item["no"])
    pose = [
        "shoulders angled about 20 degrees to viewer's right, one hand near the lower chest adjusting an armor clasp",
        "shoulders angled about 20 degrees to viewer's left, one hand lightly gathering the cloak near the chest",
        "nearly square shoulders with a restrained command gesture near the lower chest",
        "one shoulder closer to camera, cape collar flaring asymmetrically, hands mostly out of frame",
        "formal ruler portrait posture, one small prop or weapon hilt only as a background hint",
    ][(no - 1) % 5]
    expression = [
        "calm commander authority",
        "controlled confident half-smile",
        "serious but composed battlefield focus",
        "wise strategic gaze",
        "proud noble dignity",
    ][(no - 1) % 5]

    return f"""Create a NEWLY DRAWN upper-body portrait for {ko} ({slug}) using the provided full-body reference image only for identity, costume, colors, armor language, face/hair/helmet cues, and role.

This must be a fresh illustration, not a crop, not a zoom, not a reframe of the reference.

Match the approved art style: premium semi-realistic SD Three Kingdoms strategy-game figurine, mature compact warlord, moderately oversized head, angular adult commander face, compact stocky torso, broad armored shoulders, ornate high-detail 3D armor materials. It is not baby chibi and not realistic adult.

Framing: vertical 2:3 upper-body portrait from slightly above the crown/helmet/hair to below the chest armor / upper rib area. Show head, neck, shoulders, full chest armor, and a little below the chest. Do not show waist, belt, hips, legs, feet, or full-body view.

New pose: {pose}. The pose must be different from the full-body reference. Do not repeat the reference stance or weapon-holding pose.

Gaze and expression: eyes look directly forward at the viewer. Expression is {expression}, different from the reference while still mature and commanding.

Rendering/background: dark smoky ember-lit studio background matching the v9 full-body set, warm orange halo behind head and shoulders, subtle sparks, glossy lacquer armor, aged gold details, crisp silhouette, polished high-detail 3D game render.

Strict avoid: crop of original image, same pose, waist/belt/legs/feet, baby chibi, toddler cheeks, realistic adult proportions, side gaze, text, watermark, UI frame, extra characters."""


def write_jobs(roster: list[dict[str, object]]) -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    PROMPT_DIR.mkdir(parents=True, exist_ok=True)
    jobs = []
    for item in roster:
        slug = str(item["id"])
        source = SOURCE_DIR / f"{slug}_front_gaze_v1.png"
        prompt = prompt_for(item)
        prompt_path = PROMPT_DIR / f"{int(item['no']):03d}_{slug}.txt"
        prompt_path.write_text(prompt, encoding="utf-8")
        jobs.append(
            {
                "no": item["no"],
                "id": slug,
                "ko": item["ko"],
                "source": str(source),
                "prompt": str(prompt_path),
                "output": str(OUT_DIR / f"{slug}_upper_body_redraw_v1.png"),
                "done": (OUT_DIR / f"{slug}_upper_body_redraw_v1.png").exists(),
            }
        )
    JOBS_JSON.write_text(json.dumps(jobs, ensure_ascii=False, indent=2), encoding="utf-8")


def write_html(roster: list[dict[str, object]]) -> None:
    version = str(int(time.time()))
    roster_js = json.dumps(roster, ensure_ascii=False)
    html = f"""<!doctype html>
<html lang="ko">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>상반신 신규 작화 200명 v1</title>
<style>
* {{ box-sizing:border-box; }}
:root {{ color-scheme:dark; --bg:#130f0b; --panel:#211913; --line:rgba(244,223,184,.18); --gold:#ffd36a; --text:#f4dfb8; --muted:#bfa986; --bad:#ff766d; --ok:#8fe08f; }}
body {{ margin:0; background:var(--bg); color:var(--text); font-family:-apple-system,BlinkMacSystemFont,"Apple SD Gothic Neo","Noto Sans KR",sans-serif; }}
header {{ position:sticky; top:0; z-index:5; display:flex; align-items:center; gap:14px; padding:16px 20px 13px; background:rgba(20,16,12,.95); border-bottom:1px solid var(--line); backdrop-filter:blur(10px); }}
h1 {{ margin:0; font-size:22px; font-weight:850; white-space:nowrap; }}
.note {{ color:#cbb894; font-size:13px; line-height:1.45; }}
.stat {{ margin-left:auto; color:var(--gold); font-size:13px; font-weight:800; white-space:nowrap; }}
main {{ padding:18px 20px 24px; }}
.grid {{ display:grid; grid-template-columns:repeat(auto-fill,minmax(310px,1fr)); gap:16px; }}
article {{ overflow:hidden; border:1px solid rgba(244,223,184,.17); border-radius:8px; background:var(--panel); box-shadow:0 10px 22px rgba(0,0,0,.22); }}
.pair {{ display:grid; grid-template-columns:1fr 1fr; gap:1px; background:rgba(244,223,184,.16); }}
.art {{ position:relative; aspect-ratio:4/5; background:#0f0c09; overflow:hidden; }}
.art img {{ display:block; width:100%; height:100%; object-fit:cover; }}
.missing {{ height:100%; display:flex; align-items:center; justify-content:center; padding:16px; color:var(--bad); text-align:center; font-size:13px; font-weight:800; background:#120d0a; }}
.badge {{ position:absolute; top:8px; left:8px; z-index:1; padding:3px 7px 4px; border-radius:6px; background:rgba(13,9,6,.74); border:1px solid rgba(255,211,106,.32); color:var(--gold); font-size:11px; font-weight:800; }}
.meta {{ padding:10px 11px 12px; }}
.name {{ display:flex; justify-content:space-between; align-items:baseline; gap:8px; margin:0 0 7px; font-size:15px; font-weight:800; }}
.name small {{ color:#9e8a67; font-size:11px; font-weight:700; }}
.done {{ color:var(--ok); }}
.todo {{ color:var(--bad); }}
a {{ display:block; overflow-wrap:anywhere; color:var(--gold); font-size:11px; line-height:1.35; text-decoration:none; }}
@media(max-width:720px) {{ header {{ flex-wrap:wrap; align-items:stretch; }} h1,.note,.stat {{ width:100%; margin-left:0; white-space:normal; }} main {{ padding:12px; }} .grid {{ grid-template-columns:1fr; }} }}
</style>
</head>
<body>
<header>
  <h1>상반신 신규 작화 200명 v1</h1>
  <div class="note">실제 새로 생성한 이미지 파일만 표시합니다. 잘라낸 상반신은 이 페이지에 넣지 않습니다.</div>
  <div class="stat" id="stat"></div>
</header>
<main><section id="grid" class="grid"></section></main>
<script>
const roster = {roster_js};
const version = "{version}";
const grid = document.getElementById('grid');
let done = 0;
function card(item) {{
  const no = String(item.no).padStart(3, '0');
  const full = `./assets/generals/new_characters/front_gaze_200_v9_height_balance/${{item.id}}_front_gaze_v1.png?v=${{version}}`;
  const redraw = `./assets/generals/new_characters/upper_body_200_redraw_v1/${{item.id}}_upper_body_redraw_v1.png?v=${{version}}`;
  const el = document.createElement('article');
  el.innerHTML = `
    <div class="pair">
      <div class="art"><span class="badge">전신 참조</span><img loading="lazy" src="${{full}}" alt="${{item.ko}} 전신"></div>
      <div class="art"><span class="badge">신규 상반신</span><img loading="lazy" src="${{redraw}}" alt="${{item.ko}} 신규 상반신" onload="this.dataset.ok='1'; window.markDone()" onerror="this.remove(); this.parentElement.insertAdjacentHTML('beforeend','<div class=missing>신규 작화 대기</div>')"></div>
    </div>
    <div class="meta">
      <p class="name"><span>${{item.ko}}</span><small>${{no}} · ${{item.id}}</small></p>
      <a href="${{redraw}}">${{redraw}}</a>
    </div>`;
  return el;
}}
window.markDone = () => {{
  done += 1;
  document.getElementById('stat').textContent = `생성 완료 ${{done}} / ${{roster.length}}`;
}};
document.getElementById('stat').textContent = `생성 완료 0 / ${{roster.length}}`;
roster.map(card).forEach(el => grid.appendChild(el));
</script>
</body>
</html>
"""
    HTML_OUT.write_text(html, encoding="utf-8")


def main() -> None:
    roster = load_roster()
    write_jobs(roster)
    write_html(roster)
    generated = sum(1 for item in roster if (OUT_DIR / f"{item['id']}_upper_body_redraw_v1.png").exists())
    print(f"redraw images present: {generated}/{len(roster)}")
    print(JOBS_JSON)
    print(HTML_OUT)


if __name__ == "__main__":
    main()
