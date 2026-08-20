#!/usr/bin/env python3
"""대기·걷기 4컷 재발주용 레퍼런스 이미지 + 프롬프트를 만든다.

왜 필요한가:
  20컷 세트에서 **대기와 걷기만** 정면으로 나온 장수가 많다. 공격 컷은
  전부 측면인데 대기만 정면이라, 게임에서 공격할 때마다 캐릭터가 홱 돌아간다.
  가장 오래 보이는 자세가 대기라 체감이 가장 크다.

핵심:
  레퍼런스로 **정면 도감 그림을 붙이면 안 된다**. 생성 모델은 레퍼런스의
  카메라 각도를 그대로 따라간다 — 대기가 계속 정면으로 나온 원인이 그것이었다.
  대신 그 장수의 **이미 측면으로 잘 나온 공격 컷**을 붙인다. 그러면 카메라·
  의상·크기가 한꺼번에 고정된다.

  두 컷은 같은 배율로, 같은 지면선 위에 놓는다. 크기를 따로 맞추면
  "SAME size" 지시가 무의미해진다.

  python3 tools/make_walk_ref.py guan_yu
  python3 tools/make_walk_ref.py --all-front        # 정면으로 남은 장수 전원
  python3 tools/make_walk_ref.py lu_bu --cuts guard_ready,thrust_impact

출력: asset_img/refs/<id>_walkref.png   (첨부할 이미지)
     asset_img/refs/<id>_walkprompt.txt (붙여넣을 프롬프트)
"""
import argparse
import glob
import json
import os
import statistics

import numpy as np
from PIL import Image
from scipy import ndimage

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
STATES = os.path.join(ROOT, 'assets', 'arcade_duel')
OUT = os.path.join(ROOT, 'asset_img', 'refs')
CANVAS_W, CANVAS_H, GROUND = 1280, 1024, 880
# guard_ready = 측면 중립 자세(만들고 싶은 대기에 가장 가깝다)
# slash_windup = 망토와 무기 전체가 드러난다
DEFAULT_CUTS = ['guard_ready', 'slash_windup']
# 레퍼런스 후보 — 전부 측면으로 나오는 컷들. 앞쪽이 우선순위가 높다.
CANDIDATES = ['guard_ready', 'thrust_recovery', 'guard_just', 'slash_recovery',
              'slash_windup', 'heavy_windup']
# 레퍼런스가 극단적으로 웅크린 자세면 모델이 그 높이를 따라가서
# 대기만 걷기보다 낮게 그려진다(감녕 guard_ready 는 키 464, 세트 중앙값 615).
# 세트 중앙값에서 이만큼 벗어난 컷은 레퍼런스로 쓰지 않는다.
HEIGHT_TOL = 0.12
# 기본 컷이 못 쓰는 장수. 눈으로 확인하고 골라 둔 예외다.
CUT_OVERRIDES = {
    # 장비의 slash_windup 은 무기가 몸에서 떨어져 허공에 떠 있다
    'zhang_fei': ['guard_ready', 'slash_impact'],
    # 여포의 slash_windup 은 망토 조각이 떨어져 나가 있다(조각 3개)
    'lu_bu': ['guard_ready', 'thrust_recovery'],
}

PROMPT = """I am attaching TWO images. They serve DIFFERENT purposes — do not mix them up.

IMAGE 1 (the character sheet) — this is WHO to draw.
  It shows MY character {NAME}, a Three Kingdoms general, in two poses.
  Take from it: the face, the beard, the helmet, the armour pattern and
  colours, the cape, the weapon, the chibi proportions, the painterly art
  style, the figure size, and the SIDE VIEW camera angle.

IMAGE 2 (the walk strip) — this is HOW THE LEGS MOVE.
  It shows a DIFFERENT character walking, in four poses.
  Take from it ONLY the leg positions and the body lean of each of the four
  poses. Take NOTHING else — not his face, not his armour, not his colours,
  not his weapon, not his cape. He is only a mannequin showing the motion.

Now draw {NAME} — the character from IMAGE 1 — in 5 poses on ONE image, in
ONE ROW, left to right:

  [leftmost]  IDLE — a FIGHTING STANCE, not standing at attention.
      Knees clearly bent, weight settled low, body coiled. Feet apart,
      front shoulder turned toward the opponent. The weapon is raised and
      POINTED AT THE OPPONENT, held across the body — never hanging at his
      side, never resting on his shoulder, never held above his head.

  [second]  copy the LEG POSITIONS of the 1st figure in IMAGE 2
  [third]   copy the LEG POSITIONS of the 2nd figure in IMAGE 2
  [fourth]  copy the LEG POSITIONS of the 3rd figure in IMAGE 2
  [fifth]   copy the LEG POSITIONS of the 4th figure in IMAGE 2

  Match those four leg positions as closely as you can — how far apart the
  feet are, which foot is planted flat, which foot is lifted and how high,
  how much the knees bend. The 1st and 3rd walking poses have the OPPOSITE
  leg forward from each other; they must NOT look like the same pose.
  The 2nd and 4th are the narrow poses where the legs pass each other.

  Above the waist he stays exactly as in the IDLE: same head height, same
  torso angle, same arms, same weapon aim. Only the legs and the cape move.

THE WEAPON MUST STAY OFF THE GROUND — in ALL FIVE poses

  His BOOTS must be the lowest thing in every figure. Keep the whole weapon
  — blade, axe head, spear tip, shaft, tassels — clearly ABOVE the level of
  his boots, at waist height or higher. Nothing but his feet may come near
  the ground line. A blade resting low next to his boots is wrong even if it
  does not quite touch the floor.

MOST IMPORTANT RULE — HEAD HEIGHT MUST NOT CHANGE

  In ALL FIVE poses — the IDLE included — the top of the helmet must be at
  exactly the SAME height above the ground. He never stands up out of the
  stance and never sinks deeper into it. Do NOT change the body size
  between poses.

CAMERA — every pose is a SIDE VIEW

  Shoulders PERPENDICULAR to the camera. Profile of the face: one eye, one
  ear, the nose in silhouette. The chest does NOT face the viewer. The feet
  point RIGHT and he faces RIGHT in all five poses. Never flip or mirror.

LAYOUT — nothing may be cut off

  Leave a WIDE band of empty green down the LEFT and RIGHT edges — at least
  half a figure wide — and empty green above the helmets and below the
  boots. The weapon is the widest part and it is what gets cut. No blade,
  shaft, plume or cape may touch the image border, and no figure's weapon
  may reach into the next figure. If they do not all fit, draw every figure
  SMALLER — losing a little detail is fine, losing the tip of the weapon is
  not.

STRICT RULES

  - Background: solid pure green (#00FF00), completely flat. No gradient, no
    texture, no shadow, no ground, no background elements.
  - Do NOT draw any numbers, letters, labels, captions, grid lines, frames,
    boxes or separators. Plain green between the figures.
  - Clear green space between figures. Nothing may touch or overlap a
    neighbour.
  - Character only. No slash trails, no motion blur, no impact effects, no
    dust, no shadows.
  - Identical costume in every pose — the costume from IMAGE 1, never the
    costume from IMAGE 2.
"""


def _height(path):
    a = np.array(Image.open(path).convert('RGBA').getchannel('A')) > 16
    lbl, n = ndimage.label(a)
    if not n:
        return None
    m = lbl == int(np.argmax(ndimage.sum(a, lbl, range(1, n + 1)))) + 1
    ys, _ = np.nonzero(m)
    return GROUND - int(ys.min())


def pick_cuts(gid):
    """레퍼런스로 쓸 측면 컷 2장을 고른다 — 키가 세트 중앙값에 가까운 것 우선."""
    d = os.path.join(STATES, gid + '_states')
    hs = {}
    for f in glob.glob(os.path.join(d, '*.webp')):
        n = os.path.basename(f)[:-5]
        if n in ('ko_down', 'ko_fall'):        # 누운 자세는 기준에서 뺀다
            continue
        h = _height(f)
        if h:
            hs[n] = h
    if not hs:
        return DEFAULT_CUTS, '측정 실패'
    med = statistics.median(hs.values())
    ok = [c for c in CANDIDATES if c in hs and abs(hs[c] - med) / med <= HEIGHT_TOL]
    dropped = [f'{c}(키 {hs[c]}, 중앙값 {med:.0f})'
               for c in CANDIDATES[:2] if c in hs and c not in ok]
    if len(ok) < 2:
        ok = (ok + [c for c in CANDIDATES if c in hs and c not in ok])[:2]
    return ok[:2], ('; '.join(dropped) if dropped else '')


def build(gid, name, cuts):
    d = os.path.join(STATES, gid + '_states')
    have = [c for c in cuts if os.path.exists(os.path.join(d, c + '.webp'))]
    if len(have) < 2:
        return None, f'측면 컷이 부족하다 ({cuts})'
    k = 0.72                                   # 두 컷에 **동일** 적용 — 크기가 어긋나면 안 된다
    cw, ch = int(CANVAS_W * k), int(CANVAS_H * k)
    crop = (int(230 * k), 0, int(1080 * k), ch)   # 인물은 캔버스 중앙 근처다. 좌우 여백만 덜어낸다
    tile = crop[2] - crop[0]
    canvas = Image.new('RGB', (tile * len(have), ch), (0, 255, 0))
    for i, c in enumerate(have):
        s = Image.open(os.path.join(d, c + '.webp')).convert('RGBA').resize((cw, ch), Image.LANCZOS)
        bg = Image.new('RGBA', (cw, ch), (0, 255, 0, 255))
        bg.alpha_composite(s)
        canvas.paste(bg.convert('RGB').crop(crop), (i * tile, 0))
    os.makedirs(OUT, exist_ok=True)
    img_path = os.path.join(OUT, gid + '_walkref.png')
    txt_path = os.path.join(OUT, gid + '_walkprompt.txt')
    canvas.save(img_path)
    with open(txt_path, 'w', encoding='utf-8') as f:
        f.write(PROMPT.replace('{NAME}', name))
    return (img_path, txt_path), ' · '.join(have)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('gids', nargs='*')
    ap.add_argument('--all-front', action='store_true',
                    help='generals.json 에서 side=false 인 장수 전원')
    ap.add_argument('--cuts', default=','.join(DEFAULT_CUTS))
    args = ap.parse_args()

    roster = json.load(open(os.path.join(STATES, 'generals.json'), encoding='utf-8'))
    names = {g['id']: g['name'] for g in roster}
    gids = args.gids
    if args.all_front:
        gids = [g['id'] for g in roster if not g.get('side')]
    if not gids:
        ap.error('장수 id 를 주거나 --all-front 를 쓴다')

    for gid in gids:
        cuts = args.cuts.split(',')
        note = ''
        if cuts == DEFAULT_CUTS:
            if gid in CUT_OVERRIDES:
                cuts = CUT_OVERRIDES[gid]
            else:
                cuts, note = pick_cuts(gid)
        if note:
            print(f'   · 자세가 치우쳐 제외: {note}')
        out, note = build(gid, names.get(gid, gid), cuts)
        if out is None:
            print(f'{gid:<14} ✗ {note}')
        else:
            print(f'{gid:<14} {os.path.relpath(out[0], ROOT)}   ({note})')


if __name__ == '__main__':
    main()
