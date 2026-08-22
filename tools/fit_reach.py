#!/usr/bin/env python3
"""장수별 사정거리를 그림에서 재서 poses.json 의 reach 에 적는다.

왜 필요한가:
  타격 판정이 무기와 무관하게 고정 거리였다(베기 240 · 찌르기 310 · 강타 262).
  타격 컷의 창끝을 화면 좌표로 환산해 재보니, 상대 몸통 반지름(74)을 빼고도
  49명 중 48명이 무기가 닿기 전에 판정이 성립했다. 마초 찌르기는 175px
  모자랐다 — 화면 폭의 1/6 이다.

왜 실측값을 그대로 쓰지 않는가:
  두 장수가 겹치지 않는 최소 간격이 SEPARATE=205 다. 실측대로면 태사자
  찌르기는 80+74=154 로 영영 닿지 않는다. 그래서 '중앙값 대비 비율'만
  가져와 기준값의 0.88~1.12 배로 환산하고 225 를 하한으로 둔다.
  창을 쓰는 장수가 검을 쓰는 장수보다 실제로 멀리 닿는다는 개성은 살리되,
  밸런스가 깨지지 않는 폭이다.

  python3 tools/fit_reach.py            # 전원
  python3 tools/fit_reach.py --dry-run
"""
import argparse
import json
import os
import statistics

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
STATES = os.path.join(ROOT, 'assets', 'arcade_duel')
CX, TARGET_H = 640, 200
BASE = {'slash': 240, 'thrust': 310, 'heavy': 262}   # duel_v2.html 의 MOVES.reach
LO, HI, FLOOR = 0.88, 1.12, 225


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--dry-run', action='store_true')
    args = ap.parse_args()

    roster = json.load(open(os.path.join(STATES, 'generals.json'), encoding='utf-8'))
    metas, weap = {}, {}
    for g in roster:
        pj = os.path.join(STATES, g['id'] + '_states', 'poses.json')
        m = json.load(open(pj, encoding='utf-8'))
        metas[g['id']] = (pj, m)
        s = TARGET_H * g.get('size', 1) / (m.get('bodyH') or 620)
        p = m.get('poses', {})
        weap[g['id']] = {mv: (p[f'{mv}_impact']['tipX'] - CX) * s
                         for mv in BASE if f'{mv}_impact' in p}

    med = {mv: statistics.median(v[mv] for v in weap.values() if mv in v) for mv in BASE}
    print('실측 무기 리치 중앙값: ' + ' · '.join(f'{k} {v:.0f}px' for k, v in med.items()))
    print(f"\n{'장수':<7}{'베기':>6}{'찌르기':>7}{'강타':>6}")
    for g in roster:
        w = weap[g['id']]
        reach = {mv: max(FLOOR, round(BASE[mv] * min(HI, max(LO, w[mv] / med[mv]))))
                 for mv in w}
        pj, m = metas[g['id']]
        m['reach'] = reach
        if not args.dry_run:
            json.dump(m, open(pj, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
        print(f"{g['name']:<7}{reach.get('slash', 0):6}{reach.get('thrust', 0):7}"
              f"{reach.get('heavy', 0):6}")
    if args.dry_run:
        print('\n(--dry-run: 아무것도 쓰지 않았다)')


if __name__ == '__main__':
    main()
