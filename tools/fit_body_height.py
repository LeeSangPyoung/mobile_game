#!/usr/bin/env python3
"""장수별 화면 키를 맞춘다 — poses.json 의 bodyH 를 실측값으로 다시 적는다.

게임은 스프라이트를 `200 * size / bodyH` 배로 그린다(STATE_TARGET_H=200).
bodyH 가 없으면 620 을 쓰는데, 49명 중 38명이 그 상태였다. 실제 그림 키는
장수마다 510~715px 로 제각각이라 화면 키가 168~246px, 편차 37% 까지 벌어졌다
— 조운(174) 옆에 공손찬(226)이 서면 거인과 싸우는 그림이 된다.

bodyH 를 **대기 자세의 키**로 적는다. 그러면 서 있을 때 화면 키가 정확히
200 * size 가 되어 모두 같아진다(size 는 여포 1.1, 사마의 0.96 처럼 일부러
준 체격 차이다). 컷 키 중앙값으로도 해봤지만, 대기의 웅크린 깊이가 장수마다
달라 편차가 37% → 33% 로밖에 안 줄었다. 플레이어가 나란히 놓고 비교하는
자세는 대기다.

  python3 tools/fit_body_height.py            # 전원
  python3 tools/fit_body_height.py --dry-run  # 적지 않고 표만
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
GROUND = 880
TARGET_H = 200            # duel_v2.html 의 STATE_TARGET_H 와 같아야 한다
SKIP = ('ko_down', 'ko_fall')


def height(path):
    a = np.array(Image.open(path).convert('RGBA').getchannel('A')) > 16
    lbl, n = ndimage.label(a)
    if not n:
        return None
    m = lbl == int(np.argmax(ndimage.sum(a, lbl, range(1, n + 1)))) + 1
    ys, _ = np.nonzero(m)
    return GROUND - int(ys.min())


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--dry-run', action='store_true')
    args = ap.parse_args()

    roster = json.load(open(os.path.join(STATES, 'generals.json'), encoding='utf-8'))
    before, after = [], []
    print(f"{'장수':<7}{'bodyH':>12}{'화면키':>14}")
    for g in roster:
        d = os.path.join(STATES, g['id'] + '_states')
        pj = os.path.join(d, 'poses.json')
        ih = height(os.path.join(d, 'idle.webp'))
        if not ih:
            continue
        med = ih
        meta = json.load(open(pj, encoding='utf-8'))
        old = meta.get('bodyH') or 620
        size = g.get('size', 1)
        before.append(TARGET_H * size / old * ih)
        after.append(TARGET_H * size / med * ih)
        print(f"{g['name']:<7}{old:>5} → {med:<4}{before[-1]:>8.0f} → {after[-1]:<5.0f}")
        if not args.dry_run:
            meta['bodyH'] = med
            json.dump(meta, open(pj, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)

    def spread(v):
        return (max(v) - min(v)) / statistics.median(v) * 100
    print(f"\n화면 키 편차  {spread(before):.0f}% → {spread(after):.0f}%")
    print(f"  이전 {min(before):.0f}~{max(before):.0f}px / 이후 {min(after):.0f}~{max(after):.0f}px")
    if args.dry_run:
        print('\n(--dry-run: 아무것도 쓰지 않았다)')


if __name__ == '__main__':
    main()
