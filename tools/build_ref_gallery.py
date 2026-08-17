#!/usr/bin/env python3
"""장수 레퍼런스 갤러리 HTML 생성.

일기토용 포즈를 발주하려면 장수마다 (1) 레퍼런스 이미지 (2) 프롬프트 가 필요하다.
파일 경로를 일일이 찾는 대신, 브라우저에서 골라 받고 복사할 수 있게 한 페이지로 묶는다.

  python3 tools/build_ref_gallery.py          → duel_refs.html
"""
import json
import os
import re

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
REF_DIR = os.path.join(ROOT, 'asset_img', 'refs')

# 발주 프롬프트 — 조운·화웅에서 실제로 통한 형식.
# {NAME}/{WEAPON} 만 장수별로 갈아 끼운다.
PROMPT_0 = """The attached image is my character reference: {NAME}, a Three Kingdoms general.
Study it carefully — same face, same helmet, same armor pattern and colors,
same cape, same weapon. Chibi proportions, ornate detailed armor,
painterly game art style.

CAMERA — this is the single most important rule, more important than
anything else below:
Every pose is a SIDE VIEW, like a 2D fighting game sprite (Street Fighter,
King of Fighters, Samurai Shodown). The character's shoulders are
PERPENDICULAR to the camera. We see the PROFILE of the face — one eye, one
ear, the nose in silhouette. One arm is nearer the camera and partly covers
the torso. The chest does NOT face the viewer. The feet point to the right.

The attached reference is a FRONT-FACING portrait. Use it ONLY for the
character's identity — face, armor pattern, colors, cape, weapon design.
Do NOT copy its camera angle and do NOT copy its standing pose.

Draw this SAME character in 4 poses on ONE image, numbered 1 to 4:

1  IDLE — a side-on combat stance, knees bent, weight settled, body turned
   so the shoulder points at the opponent. The weapon is held ACROSS the
   body, angled and ready to strike — not planted upright, not resting.
   He is about to fight, not posing for a portrait.
   The weapon must NOT touch the ground.
2  WALK 1 — mid-stride, front foot planting on the ground, rear foot lifted
   behind, body leaning slightly forward, cape trailing back.
3  WALK 2 — mid-stride, both legs passing each other, body at the highest
   point of the step.
4  WALK 3 — mid-stride, rear foot planting, front foot lifted forward.
   The mirror of pose 2.

STRICT RULES
- Background: solid pure green (#00FF00), completely flat, no gradient,
  no texture, no shadow, no ground.
- ALL 4 figures at the SAME size and SAME scale. Draw them LARGE — one row
  of 4, filling the image height.
- Do NOT draw grid lines, frames or separators. Plain green between figures.
- Nothing cropped: weapon, cape and helmet fully inside with green margin.
- Character only. No slash trails, no motion blur, no effects, no dust,
  no shadows, no text or labels other than the numbers.
- Identical costume in every pose."""

PROMPT_1 = """The attached image is my character reference: {NAME}, a Three Kingdoms general.
Study it carefully — same face, same helmet, same armor pattern and colors,
same cape, same weapon. Chibi proportions, ornate detailed armor,
painterly game art style.

CAMERA — this is the single most important rule, more important than
anything else below:
Every pose is a SIDE VIEW, like a 2D fighting game sprite (Street Fighter,
King of Fighters, Samurai Shodown). The character's shoulders are
PERPENDICULAR to the camera. We see the PROFILE of the face — one eye, one
ear, the nose in silhouette. One arm is nearer the camera and partly covers
the torso. The chest does NOT face the viewer. The feet point to the right.

The attached reference is a FRONT-FACING portrait. Use it ONLY for the
character's identity — face, armor pattern, colors, cape, weapon design.
Do NOT copy its camera angle and do NOT copy its standing pose.

Draw this SAME character in 10 poses on ONE image, numbered 1 to 10:

1  IDLE — side-on combat stance, weapon held ready, calm and watchful.
   In this pose the weapon must NOT touch the ground.
2  WALK 1 — mid-stride, front foot planting, rear foot lifted behind.
3  WALK 2 — mid-stride, both legs passing each other, body at its highest.
4  WALK 3 — mid-stride, rear foot planting, front foot lifted forward.
5  SLASH WINDUP — weapon pulled back over the rear shoulder, torso coiled
   away, weight on the back leg.
6  SLASH IMPACT — weapon swept forward through a horizontal arc at full
   extension, torso rotated into the swing, front foot planted hard.
7  SLASH RECOVERY — just after the swing, weapon low and past the body,
   torso over-rotated, off balance.
8  THRUST WINDUP — weapon drawn back beside the hip, elbow behind, stance
   low and compressed, aiming forward.
9  THRUST IMPACT — deep lunge, weapon driven straight forward at maximum
   reach, back leg stretched far behind, body a straight line.
10 THRUST RECOVERY — pulling the weapon back, front leg still forward,
   weight settling, still extended and open.

STRICT RULES
- Background: solid pure green (#00FF00), completely flat, no gradient,
  no texture, no shadow, no ground.
- ALL figures at the SAME size and SAME scale. Do not vary the character size
  between cells. Draw them as LARGE as the grid allows — I need detail.
- Arrange them as 2 rows x 5 columns.
- Do NOT draw grid lines, frames or separators between cells. Leave plain
  green space between figures.
- Clear empty green space between figures. Nothing may touch or overlap a
  neighbour, and nothing may be cut off at the image edge — especially the
  weapon, the cape and the helmet.
- Every figure faces RIGHT and is seen from the SIDE (side-on combat view,
  NOT front-facing). The reference image is front-facing; copy only the
  character design, not that camera angle.
- Character only. No slash trails, no motion blur, no impact effects, no dust,
  no shadows, no background elements.
- Identical costume in every pose: same face, same helmet, same armor pattern,
  same cape, same weapon."""

PROMPT_2 = """The attached image is my character reference: {NAME}, a Three Kingdoms general.
Study it carefully — same face, same helmet, same armor pattern and colors,
same cape, same weapon. Chibi proportions, ornate detailed armor,
painterly game art style.

CAMERA — this is the single most important rule, more important than
anything else below:
Every pose is a SIDE VIEW, like a 2D fighting game sprite (Street Fighter,
King of Fighters, Samurai Shodown). The character's shoulders are
PERPENDICULAR to the camera. We see the PROFILE of the face — one eye, one
ear, the nose in silhouette. One arm is nearer the camera and partly covers
the torso. The chest does NOT face the viewer. The feet point to the right.

The attached reference is a FRONT-FACING portrait. Use it ONLY for the
character's identity — face, armor pattern, colors, cape, weapon design.
Do NOT copy its camera angle and do NOT copy its standing pose.

This is the SECOND batch for the same character. Keep the exact same costume,
the same size and the same framing as the first batch.

Draw 10 more poses on ONE image, numbered 11 to 20:

11 HEAVY WINDUP — weapon raised high overhead with both hands, body
   stretched upward and leaning back. The most telegraphed wind-up.
12 HEAVY IMPACT — weapon smashed down through a vertical arc, ending near
   the ground, body dropped into a deep crouch, full force committed.
13 HEAVY RECOVERY — weapon resting on the ground, body bent forward over it,
   slow to recover, wide open.
14 GUARD — crouched low and side-on, weapon shaft held across the chest as
   a barrier, head tucked, braced.
15 PARRY — the instant of deflecting a blow: weapon snapped outward, arms
   extended, torso twisting into the block, head up, defiant.
16 HURT LIGHT — upper body recoils backward, head snapped back, off arm
   flying up, both feet still planted, pained grimace.
17 HURT HEAVY — whole body thrown backward and bent at the waist, head flung
   far back, arms flung outward, weapon nearly slipping, front foot lifted
   off the ground. Maximum recoil.
18 STUNNED — slumped FORWARD, knees buckled, shoulders dropped, head hanging,
   dazed, arms limp, weapon dragging on the ground. About to collapse.
19 KO FALL — mid-fall after a fatal blow, body tipped backward about 45
   degrees, feet off the ground, arms thrown up, the weapon flying loose out
   of the hands, cape streaming upward.
20 KO DOWN — collapsed on the ground, body lying horizontally on its back,
   limbs sprawled, eyes closed, the weapon lying separately beside the body.
   This is the only pose where the body is horizontal.

STRICT RULES
- Background: solid pure green (#00FF00), completely flat, no gradient,
  no texture, no shadow, no ground.
- ALL figures at the SAME size and SAME scale. Do not vary the character size
  between cells. Draw them as LARGE as the grid allows — I need detail.
- Arrange them as 2 rows x 5 columns.
- Do NOT draw grid lines, frames or separators between cells. Leave plain
  green space between figures.
- Clear empty green space between figures. Nothing may touch or overlap a
  neighbour, and nothing may be cut off at the image edge — especially the
  weapon, the cape and the helmet.
- Every figure faces RIGHT and is seen from the SIDE (side-on combat view,
  NOT front-facing). The reference image is front-facing; copy only the
  character design, not that camera angle.
- Character only. No slash trails, no motion blur, no impact effects, no dust,
  no shadows, no background elements.
- Identical costume in every pose: same face, same helmet, same armor pattern,
  same cape, same weapon."""


def load_roster():
    s = open(os.path.join(ROOT, 'prototype.html'), encoding='utf-8').read()
    i = s.index('const MANUAL_GENERAL_DEFS = [')
    block = s[i:s.index('\n];', i)]
    pat = re.compile(r"\{\s*id:\s*'([a-z_]+)',\s*name:\s*'([^']+)',\s*buffs:\s*\{([^}]*)\}")
    rows = [{'id': m.group(1), 'name': m.group(2),
             'score': sum(float(v) for v in re.findall(r':\s*([0-9.]+)', m.group(3)))}
            for m in pat.finditer(block)]
    rows.sort(key=lambda r: -r['score'])
    return rows


HTML = '''<!doctype html><meta charset="utf-8">
<title>일기토 장수 레퍼런스</title>
<style>
 :root{--gold:#ffd45c}
 *{box-sizing:border-box}
 body{margin:0;background:#100b07;color:#e9dcc2;
   font:14px/1.6 system-ui,-apple-system,"Apple SD Gothic Neo",sans-serif}
 header{position:sticky;top:0;z-index:5;background:#140e08f2;backdrop-filter:blur(6px);
   padding:14px 20px;border-bottom:1px solid #3a2a16}
 h1{margin:0 0 4px;font-size:18px;color:var(--gold)}
 .sub{color:#a28f6d;font-size:12.5px}
 .bar{display:flex;gap:8px;align-items:center;margin-top:10px;flex-wrap:wrap}
 input,select{font:inherit;padding:6px 10px;border-radius:6px;border:1px solid #6b4f26;
   background:#241809;color:#f0dcb4}
 .grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(190px,1fr));
   gap:14px;padding:18px 20px 60px}
 .card{background:#1b120a;border:1px solid #3d2c18;border-radius:10px;overflow:hidden;
   display:flex;flex-direction:column}
 .card img{width:100%;aspect-ratio:1;object-fit:contain;background:#0b3d0b;display:block}
 .meta{padding:8px 10px}
 .nm{font-weight:800;color:#fff3c4}
 .id{color:#9a8664;font-size:11.5px;font-family:ui-monospace,monospace}
 .rk{float:right;color:var(--gold);font-weight:800;font-size:12px}
 .btns{display:flex;gap:6px;padding:0 10px 10px}
 .btns a,.btns button{flex:1;text-align:center;font:inherit;font-size:12px;font-weight:700;
   padding:6px 4px;border-radius:6px;border:1px solid #6b4f26;background:#2a1c0d;
   color:#f0dcb4;text-decoration:none;cursor:pointer}
 .btns a:hover,.btns button:hover{background:#3a2712}
 .top70{outline:2px solid #7a5a1e}
 .done{border-color:#5c7a3a}
 .tag{background:#7a3a1e;color:#ffdcc0;font-size:11px;font-weight:800;padding:3px 8px}
 .tag.ok{background:#2f4a1e;color:#cfe8b0}
 dialog{background:#1b120a;color:#e9dcc2;border:1px solid #6b4f26;border-radius:10px;
   max-width:920px;width:94vw}
 dialog h3{margin:12px 14px;font-size:14px;color:var(--gold)}
 dialog textarea{width:calc(100% - 28px);height:58vh;margin:0 14px;background:#0e0a06;
   color:#dcc9a0;border:1px solid #3d2c18;border-radius:6px;padding:10px;
   font:12px/1.55 ui-monospace,monospace}
 dialog .row{display:flex;gap:8px;padding:12px 14px}
 dialog button{font:inherit;font-weight:700;padding:8px 14px;border-radius:6px;
   border:1px solid #6b4f26;background:#2a1c0d;color:#f0dcb4;cursor:pointer}
</style>
<header>
  <h1>일기토 장수 레퍼런스</h1>
  <div class="sub"><b>이미지 받기</b>로 레퍼런스를 내려받아 GPT에 첨부하고, <b>프롬프트</b>를 복사해 붙여넣으세요.
     전투력 상위 70명은 금색 테두리입니다.</div>
  <div class="bar">
    <input id="q" placeholder="이름 · id 검색" size="18">
    <select id="filt">
      <option value="all">전체</option>
      <option value="top">전투력 상위 70</option>
      <option value="fix">대기·걷기 교정 필요</option>
      <option value="todo">아직 안 만든 장수</option>
    </select>
    <span id="cnt" class="sub"></span>
  </div>
</header>
<div class="grid" id="grid"></div>
<dialog id="dlg">
  <h3 id="dlgT"></h3>
  <textarea id="dlgX" readonly></textarea>
  <div class="row">
    <button id="copyBtn">프롬프트 복사</button>
    <button onclick="document.getElementById('dlg').close()">닫기</button>
  </div>
</dialog>
<script>
const DATA = __DATA__;
const P0 = __P0__, P1 = __P1__, P2 = __P2__;
const grid = document.getElementById('grid');
const q = document.getElementById('q'), filt = document.getElementById('filt');
function render() {
  const t = q.value.trim().toLowerCase(), f = filt.value;
  const rows = DATA.filter(g => (f !== 'top' || g.rank <= 70)
    && (f !== 'fix' || g.fix) && (f !== 'todo' || !g.has)
    && (!t || g.name.toLowerCase().includes(t) || g.id.includes(t)));
  grid.innerHTML = rows.map(g => `
    <div class="card${g.rank <= 70 ? ' top70' : ''}${g.has ? ' done' : ''}">
      ${g.fix ? '<div class="tag">대기·걷기 교정</div>' : (g.has ? '<div class="tag ok">완료</div>' : '')}
      <img src="./asset_img/refs/${g.id}.png" loading="lazy" alt="${g.name}">
      <div class="meta"><span class="rk">${g.rank}위</span>
        <div class="nm">${g.name}</div><div class="id">${g.id}</div></div>
      <div class="btns">
        <a href="./asset_img/refs/${g.id}.png" download>이미지 받기</a>
        <button data-id="${g.id}" data-name="${g.name}" data-p="0">대기·걷기</button>
        <button data-id="${g.id}" data-name="${g.name}" data-p="1">1차</button>
        <button data-id="${g.id}" data-name="${g.name}" data-p="2">2차</button>
      </div>
    </div>`).join('');
  document.getElementById('cnt').textContent = rows.length + '명';
  grid.querySelectorAll('button[data-id]').forEach(b => b.onclick = () => {
    document.getElementById('dlgT').textContent =
      b.dataset.name + ' (' + b.dataset.id + ') — 첨부할 파일: asset_img/refs/' + b.dataset.id + '.png';
    const src = b.dataset.p === '2' ? P2 : (b.dataset.p === '0' ? P0 : P1);
    document.getElementById('dlgT').textContent +=
      b.dataset.p === '0' ? '  ·  대기·걷기 4컷 (측면 교정)' : '  ·  ' + b.dataset.p + '차 (10컷)';
    document.getElementById('dlgX').value = src.split('{NAME}').join(b.dataset.name);
    document.getElementById('dlg').showModal();
  });
}
document.getElementById('copyBtn').onclick = e => {
  navigator.clipboard.writeText(document.getElementById('dlgX').value);
  e.target.textContent = '복사됨';
  setTimeout(() => e.target.textContent = '프롬프트 복사', 1200);
};
q.oninput = render; filt.onchange = render;
render();
</script>
'''


def main():
    rows = load_roster()
    ST = os.path.join(ROOT, 'assets', 'arcade_duel')
    SIDE_OK = {'zhao_yun', 'hua_xiong'}          # 이미 측면으로 그려진 장수
    data = []
    for i, r in enumerate(rows):
        if not os.path.exists(os.path.join(REF_DIR, r['id'] + '.png')):
            continue
        has = os.path.isdir(os.path.join(ST, r['id'] + '_states'))
        data.append({'id': r['id'], 'name': r['name'], 'rank': i + 1,
                     'has': has,
                     # 세트는 있는데 정면으로 그려진 장수 = 대기·걷기 교정 대상
                     'fix': has and r['id'] not in SIDE_OK})
    html = (HTML.replace('__DATA__', json.dumps(data, ensure_ascii=False))
                .replace('__P0__', json.dumps(PROMPT_0, ensure_ascii=False))
                .replace('__P1__', json.dumps(PROMPT_1, ensure_ascii=False))
                .replace('__P2__', json.dumps(PROMPT_2, ensure_ascii=False)))
    out = os.path.join(ROOT, 'duel_refs.html')
    open(out, 'w', encoding='utf-8').write(html)
    print(f'{len(data)}명 → {os.path.relpath(out, ROOT)}')


if __name__ == '__main__':
    main()
