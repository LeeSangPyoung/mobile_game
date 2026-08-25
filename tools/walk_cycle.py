#!/usr/bin/env python3
"""걷기 3컷의 재생 순서를 그림에서 직접 재서 poses.json 에 적는다.

왜 필요한가:
  walk1/2/3 은 시트에서 **왼쪽부터** 잘라낸 순서일 뿐이다. 생성 결과가
  순서를 바꿔 그리면(허저처럼 walk2 가 뒷발 접지) 걸음이 앞뒤로 튄다.
  파일명을 믿지 말고 발 위치로 판정한다 — fix_all_attacks.py 가 공격
  3단계를 창끝으로 판정하는 것과 같은 방식이다.

무엇을 쓰는가:
  poses.json 에 "walkCycle" 을 넣는다. 4비트다.

      앞발 접지 → 통과 → 뒷발 접지 → 통과

  걷기 한 주기는 두 걸음이라 짝수여야 한다. 3컷을 그대로 1-2-3 으로
  돌리면 통과 자세가 한 번만 나와서 절뚝인다(발소리는 주기당 2번인데
  그림은 3장이라 리듬도 안 맞았다). 통과 컷을 두 번 쓰면 해결된다.

  python3 tools/walk_cycle.py guan_yu          # 한 명
  python3 tools/walk_cycle.py --all            # 걷기 컷이 있는 전원
"""
import argparse
import glob
import json
import os
import sys

import numpy as np
from PIL import Image
from scipy import ndimage

# Diagnostic prose contains punctuation unavailable in some Windows cp949
# consoles.  Reporting must not interrupt the metadata update.
try:
    sys.stdout.reconfigure(errors='replace')
except (AttributeError, OSError):
    pass

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
STATES = os.path.join(ROOT, 'assets', 'arcade_duel')
WALKS3 = ['walk1', 'walk2', 'walk3']
WALKS4 = WALKS3 + ['walk4']


def foot_offset(path):
    """지면에 닿은 부분에서 세 값을 잰다.

      offset : 발 중심이 몸 중심보다 얼마나 앞(+)인가 — 어느 발로 딛고 있나
      span   : 두 발이 얼마나 벌어졌나 — **통과 자세는 이게 가장 좁다**
      height : 실루엣 키
    """
    a = np.array(Image.open(path).convert('RGBA').getchannel('A')) > 16
    lbl, n = ndimage.label(a)
    if not n:
        return None
    m = lbl == int(np.argmax(ndimage.sum(a, lbl, range(1, n + 1)))) + 1
    ys, xs = np.nonzero(m)
    band = m[ys.max() - 40:ys.max() + 1, :]          # 지면에 닿은 부분만
    bx = np.nonzero(band)[1]
    if not len(bx):
        return None
    return (float(bx.mean() - xs.mean()), int(bx.max() - bx.min()), int(880 - ys.min()))


def head_x(path):
    """실루엣 위쪽 18%(머리)의 가로 중심. 걷기 중에도 거의 안 흔들리는 기준점이다."""
    a = np.array(Image.open(path).convert('RGBA').getchannel('A')) > 16
    lbl, n = ndimage.label(a)
    if not n:
        return None
    m = lbl == int(np.argmax(ndimage.sum(a, lbl, range(1, n + 1)))) + 1
    ys, _ = np.nonzero(m)
    top, h = ys.min(), ys.max() - ys.min()
    hx = np.nonzero(m[top:top + int(h * 0.18), :])[1]
    return float(hx.mean()) if len(hx) else None


def feet_of(path):
    """대기 자세에서 두 발의 중심과 폭을 잰다 — 접지 그림자를 발밑에 놓기 위한 값.

    지면에 닿은 띠에서 **가장 바깥 두 덩어리**를 발로 본다. 망토 자락이 두 발
    사이로 늘어져 같이 걸리는 경우가 있는데(감녕은 379-482 / 587-702 / 762-897 로
    가운데가 망토다), 큰 것부터 고르면 발 하나와 망토를 짝지어 버린다.
    서 있는 자세에서 지면에 닿는 것 중 가장 바깥은 언제나 두 발이다.
    """
    a = np.array(Image.open(path).convert('RGBA').getchannel('A')) > 16
    lbl, n = ndimage.label(a)
    if not n:
        return None
    m = lbl == int(np.argmax(ndimage.sum(a, lbl, range(1, n + 1)))) + 1
    ys, _ = np.nonzero(m)
    cols = m[ys.max() - 40:ys.max() + 1, :].any(axis=0)
    cl, cn = ndimage.label(cols[None, :])
    if not cn:
        return None
    runs = [np.nonzero(cl[0] == i)[0] for i in range(1, cn + 1)]
    lo = min(int(r.min()) for r in runs)
    hi = max(int(r.max()) for r in runs)
    return {'cx': round((lo + hi) / 2), 'w': hi - lo}


def cycle_for(gid):
    d = os.path.join(STATES, gid + '_states')
    pj = os.path.join(d, 'poses.json')
    if not os.path.exists(pj):
        return None, 'poses.json 없음'
    walks = WALKS4 if os.path.exists(os.path.join(d, 'walk4.webp')) else WALKS3
    vals = {}
    for w in walks:
        f = os.path.join(d, w + '.webp')
        if not os.path.exists(f):
            return None, '걷기 컷 없음 (리그가 담당)'
        v = foot_offset(f)
        if v is None:
            return None, f'{w} 측정 실패'
        vals[w] = v

    # 통과 자세 = 두 발이 **몸 아래에 모인** 컷.
    # 발폭만 보면 안 된다: 뒷발을 높이 든 접지 자세는 지면에 닿은 발이 하나뿐이라
    # 발폭이 좁게 나온다(마초 walk1 은 발폭 127 인데 발중심이 +222 로 훨씬 앞이었다).
    # 발 중심만 봐도 안 된다: 두 접지 컷의 중심이 비슷한 경우가 있다(황충 -26.5 / -23.3).
    # 둘을 합쳐서 본다 — 통과는 좁고 **동시에** 몸 아래에 있다.
    score = lambda w: vals[w][1] + 2 * abs(vals[w][0])
    order = sorted(walks, key=score)
    if len(walks) == 4:
        # 통과 2컷 · 접지 2컷. 접지는 발 중심이 앞인 쪽이 앞발 접지.
        mids, contacts = order[:2], order[2:]
        front, back = sorted(contacts, key=lambda w: -vals[w][0])
        # 통과 두 컷도 앞뒤로 갈라 각 접지 뒤에 배치한다 — 반복 프레임이 없어진다
        m1, m2 = sorted(mids, key=lambda w: -vals[w][0])
        cycle = [front, m1, back, m2]
        mid = m1
    else:
        mid = order[0]
        front, back = sorted([w for w in walks if w != mid], key=lambda w: -vals[w][0])
        cycle = [front, mid, back, mid]

    spread = vals[front][0] - vals[back][0]
    ch = abs(vals[front][2] - vals[back][2]) / max(1, vals[mid][2]) * 100
    narrow = vals[mid][1] / max(1, max(vals[front][1], vals[back][1])) * 100
    meta = json.load(open(pj, encoding='utf-8'))
    # 컷마다 몸이 좌우로 어긋나 있으면 걸을 때 캐릭터가 순간이동한다.
    # 정렬 기준인 '몸통 중심'은 망토·무기 때문에 자세마다 크게 흔들린다
    # (마초는 걷기 컷 사이에서 머리가 118px 튀었다 — 화면상 38px).
    # 머리 x 를 재서 평균에 맞추는 보정값을 적어 둔다. 그림은 건드리지 않는다.
    heads = {w: head_x(os.path.join(d, w + '.webp')) for w in walks}
    heads = {w: v for w, v in heads.items() if v is not None}
    if heads:
        avg = sum(heads.values()) / len(heads)
        meta['walkAlign'] = {w: round(avg - v) for w, v in heads.items()}
    ft = feet_of(os.path.join(d, 'idle.webp'))
    if ft:
        meta['feet'] = ft
    meta['walkCycle'] = cycle
    # 한 걸음에 그림이 나아가는 거리(캔버스 px). 게임이 이 값만큼만 이동시키면
    # 보폭이 크든 작든 디딘 발이 미끄러지지 않는다.
    meta['walkStep'] = round(spread)
    json.dump(meta, open(pj, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
    note = (f'{len(walks)}컷 · 교대 {spread:.0f}px · 접지 키차 {ch:.1f}% · 통과 발폭 {narrow:.0f}%')
    if spread < 40:
        note += '  ! 다리 교대가 거의 없다 — 재발주 대상'
    if ch > 4:
        note += '  ! 두 접지 컷의 키가 어긋난다 — 재발주 대상'
    if narrow > 70:
        note += '  ! 두 발이 모이는 컷이 없다 — 재발주 대상'
    if len(walks) == 3:
        note += '  · 통과 컷이 두 번 재생된다(4컷 권장)'
    return cycle, note


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('gids', nargs='*')
    ap.add_argument('--all', action='store_true')
    args = ap.parse_args()
    gids = args.gids
    if args.all:
        gids = sorted(os.path.basename(p)[:-7]
                      for p in glob.glob(os.path.join(STATES, '*_states')))
    if not gids:
        ap.error('장수 id 를 주거나 --all 을 쓴다')
    for gid in gids:
        cycle, note = cycle_for(gid)
        if cycle is None:
            print(f'{gid:<14} — {note}')
        else:
            print(f'{gid:<14} {" → ".join(c[-1] for c in cycle)}   {note}')


if __name__ == '__main__':
    main()
