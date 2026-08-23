#!/usr/bin/env python3
"""타격 컷에서 무기가 **적 쪽으로 뻗어 있는지** 전수 조사한다.

왜 필요한가:
  태사자로 싸우면 "찌르기조차 안 닿는 느낌"이고 "칼날이 적 방향이 아니다" 는
  제보가 있었다. 재보니 사실이었다 — 태사자 thrust_impact 은 창이 앞으로
  75px, 뒤로 85px 이다. **뒤가 더 멀다.** 찌르는 그림이 아니라 창을 몸 앞에
  가로로 들고 있는 그림이었다.

  사거리(fit_reach.py)는 창끝이 몸 중심에서 얼마나 앞에 있는지로 정해진다.
  그림이 이러면 사거리가 하한까지 떨어지고, 하한으로 올려 놔도 **그림에는
  안 닿아 보인다**. 숫자로 못 고치는 문제라 재발주 대상을 골라내야 한다.

무엇을 재나 (화면 px 로 환산 — 장수마다 덩치가 달라 원본 px 은 비교 불가):
  앞  몸 중심에서 오른쪽(적 방향)으로 가장 먼 불투명 픽셀까지
  뒤  몸 중심에서 왼쪽으로 가장 먼 불투명 픽셀까지

판정:
  뒤 > 앞          → 무기가 뒤를 향한다. 재발주.
  앞 < FWD_MIN     → 무기가 거의 안 나간다. 재발주 권장.

  강베기는 내리치는 자세가 많아 앞으로 덜 나가는 게 자연스럽다 — 기준을
  따로 둔다.

  python3 tools/audit_weapon.py
  python3 tools/audit_weapon.py --all      # 전원 출력
"""
import argparse
import json
import os

import numpy as np
from PIL import Image
from scipy import ndimage

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
STATES = os.path.join(ROOT, 'assets', 'arcade_duel')
TARGET_H = 200
MOVES = ('slash', 'thrust', 'heavy')
# 창끝이 몸 중심에서 이만큼은 앞에 있어야 '적을 향해 뻗었다' 고 볼 수 있다.
# 강베기는 내리치는 자세라 앞으로 덜 나가는 게 자연스러워 기준을 낮춘다.
FWD_MIN = {'slash': 110, 'thrust': 130, 'heavy': 70}
# 상대 몸 반지름(평균). reach 는 중심 간 거리라, 그림이 이만큼 안쪽까지만
# 오면 눈에는 '안 닿았는데 맞았다' 로 보인다.
FOE_R = 77
GAP_BAD, GAP_REDRAW = 25, 60


def measure(path, scale, tip):
    """게임이 실제로 쓰는 창끝(poses.json 의 tipX)이 몸 중심에서 얼마나 앞인가.

    실루엣의 좌우 끝으로 재면 **망토를 잡는다** — 강베기는 몸을 젖히며 내리치니
    망토가 뒤로 길게 날린다. 그걸 '무기가 뒤를 향한다' 로 세면 전부 오탐이다.
    게임은 tipX 로 아우라와 궤적을 그리므로, 그 점이 기준이어야 맞다.
    """
    a = np.array(Image.open(path).convert('RGBA').getchannel('A')) > 24
    if not a.any():
        return None
    lbl, n = ndimage.label(a)
    body = lbl == int(np.argmax(ndimage.sum(a, lbl, range(1, n + 1)))) + 1
    _, bx = ndimage.center_of_mass(body)
    xs = np.nonzero(a)[1]
    return ((tip - bx) * scale,            # 창끝이 몸 중심에서 앞으로 얼마나
            (xs.max() - bx) * scale)       # 실루엣이 앞으로 얼마나(참고)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--all', action='store_true')
    args = ap.parse_args()

    roster = json.load(open(os.path.join(STATES, 'generals.json'), encoding='utf-8'))
    rows = []
    for g in roster:
        d = os.path.join(STATES, g['id'] + '_states')
        meta = json.load(open(os.path.join(d, 'poses.json'), encoding='utf-8'))
        scale = TARGET_H * g.get('size', 1) / (meta.get('bodyH') or 620)
        reach = meta.get('reach', {})
        got, flags = {}, []
        for mv in MOVES:
            f = os.path.join(d, f'{mv}_impact.webp')
            tip = (meta.get('poses', {}).get(f'{mv}_impact', {}) or {}).get('tipX')
            if not os.path.exists(f) or tip is None:
                continue
            r = measure(f, scale, tip)
            if not r:
                continue
            fwd = r[0]
            # 게임이 맞았다고 판정하는 거리에서, 상대 몸 가장자리는 어디인가.
            # reach 는 중심 간 거리이고 상대 몸 반지름은 평균 77px 이다.
            need = reach.get(mv, 0) - FOE_R
            got[mv] = (fwd, need, need - fwd)      # 그린거리 / 닿아야할거리 / 허공
            if need - fwd > GAP_BAD:
                flags.append(f'{mv} {need - fwd:.0f}px 모자람')
        if got:
            rows.append((g['name'], g['id'], got, flags, max(v[2] for v in got.values())))

    rows.sort(key=lambda r: -r[4])
    print('■ 판정이 닿는 자리까지 그림이 못 미치는 거리 (px · 클수록 나쁨)')
    print(f"  기준: 상대 몸 반지름 {FOE_R}px · {GAP_BAD}px 초과면 눈에 띈다"); print()
    print(f"{'장수':<7}{'베기':>8}{'찌르기':>8}{'강베기':>8}  최악  판정")
    for name, gid, got, flags, worst in rows:
        if worst <= GAP_BAD and not args.all:
            continue
        cell = lambda mv: (f"{got[mv][2]:+.0f}" if mv in got else '-')
        mark = '재발주' if worst > GAP_REDRAW else ('경계' if worst > GAP_BAD else 'OK')
        print(f"{name:<7}{cell('slash'):>8}{cell('thrust'):>8}{cell('heavy'):>8}"
              f"{worst:>7.0f}  {mark}")
    redraw = [r for r in rows if r[4] > GAP_REDRAW]
    watch = [r for r in rows if GAP_BAD < r[4] <= GAP_REDRAW]
    print(); print(f"조사 {len(rows)}명")
    print(f"  재발주 필요 ({GAP_REDRAW}px 초과)  {len(redraw)}명: "
          + ', '.join(f"{n}({','.join(f for f in fl)})" for n, _, _, fl, _ in redraw))
    print(f"  경계 ({GAP_BAD}~{GAP_REDRAW}px)      {len(watch)}명: "
          + ', '.join(n for n, _, _, _, _ in watch))


if __name__ == '__main__':
    main()
