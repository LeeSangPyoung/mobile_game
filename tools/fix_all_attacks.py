#!/usr/bin/env python3
"""이미 만든 장수들의 공격 3단계 순서를 일괄 점검·교정한다.

타격(impact)은 무기가 가장 앞으로 나간 프레임이어야 한다.
생성 결과가 가끔 순서를 바꿔 그려서 '뒤로 휘두르는' 것처럼 보인다.
무기끝 좌표가 이미 있으므로 그것으로 판정하고 파일을 서로 바꾼다.

  python3 tools/fix_all_attacks.py            # 점검만
  python3 tools/fix_all_attacks.py --apply    # 교정까지
"""
import argparse
import glob
import json
import os
import sys

from PIL import Image

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, 'tools'))
from make_general import fix_attack_order  # noqa: E402


def report(out_dir):
    pj = os.path.join(out_dir, 'poses.json')
    if not os.path.exists(pj):
        return []
    poses = json.load(open(pj)).get('poses', {})
    bad = []
    for mv in ('slash', 'thrust', 'heavy'):
        names = [f'{mv}_{s}' for s in ('windup', 'impact', 'recovery')]
        tips = [poses.get(n, {}).get('tipX') for n in names]
        if any(t is None for t in tips):
            continue
        if tips[1] < max(tips[0], tips[2]):
            bad.append((mv, tips))
    return bad


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--apply', action='store_true')
    args = ap.parse_args()

    total = 0
    for d in sorted(glob.glob(os.path.join(ROOT, 'assets', 'arcade_duel', '*_states'))):
        gid = os.path.basename(d)[:-7]
        bad = report(d)
        if not bad:
            continue
        total += len(bad)
        print(f'[{gid}]')
        for mv, tips in bad:
            print(f'   {mv:7s} 예비 {tips[0]:4d} / 타격 {tips[1]:4d} / 후딜 {tips[2]:4d}'
                  '   ← 타격이 가장 앞이 아니다')
        if args.apply:
            for line in fix_attack_order(d):
                print(f'   ○ {line}')
    print(f'\n문제 {total}건' + ('  → 교정 완료' if args.apply else '  (--apply 로 교정)'))


if __name__ == '__main__':
    main()
