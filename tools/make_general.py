#!/usr/bin/env python3
"""장수 시트 2장 → 게임에 바로 쓰는 20컷 세트.

split_pose_sheet.py 와 harmonize_poses.py 를 순서대로 부르고 검증까지 한다.
장수 한 명당 명령 한 줄이면 끝나게 하려고 묶었다.

  python3 tools/make_general.py taishi_ci ~/Downloads/a.png ~/Downloads/b.png
  python3 tools/make_general.py taishi_ci --latest 2      # 다운로드 최근 2장

끝나면 게임에서 ?boss=taishi_ci 로 바로 확인할 수 있다(코드 편집 없음).
"""
import argparse
import glob
import os
import shutil
import statistics
import subprocess
import sys

import numpy as np
from PIL import Image
from scipy import ndimage

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TOOLS = os.path.join(ROOT, 'tools')

P1 = ['idle', 'walk1', 'walk2', 'walk3',
      'slash_windup', 'slash_impact', 'slash_recovery',
      'thrust_windup', 'thrust_impact', 'thrust_recovery']
P2 = ['heavy_windup', 'heavy_impact', 'heavy_recovery',
      'guard_ready', 'guard_just', 'hurt_light', 'hurt_heavy',
      'stunned', 'ko_fall', 'ko_down']


def run(args):
    r = subprocess.run([sys.executable] + args, capture_output=True, text=True, cwd=ROOT)
    for line in (r.stdout + r.stderr).splitlines():
        if any(k in line for k in ('컷', '보정', '!', '배율', '→', '몸 높이', '세트')):
            print('   ' + line.strip())
    return r.returncode == 0


def verify(out_dir):
    """장수마다 자동으로 돌리는 검사. 전부 실제로 터졌던 문제들이다."""
    files = sorted(glob.glob(os.path.join(out_dir, '*.webp')))
    problems, cores = [], []
    if len(files) != 20:
        problems.append(f'컷이 {len(files)}개 (20개여야 한다)')
    for f in files:
        name = os.path.basename(f)[:-5]
        im = Image.open(f).convert('RGBA')
        a = np.array(im.getchannel('A')) > 16
        if not a.any():
            problems.append(f'{name}: 비어 있다')
            continue
        ys, xs = np.nonzero(a)
        if xs.min() <= 0 or xs.max() >= im.width - 1 or ys.min() <= 0:
            problems.append(f'{name}: 캔버스 밖으로 잘렸다')
        lbl, n = ndimage.label(a)
        sizes = ndimage.sum(a, lbl, range(1, n + 1))
        by, _ = np.nonzero(lbl == int(np.argmax(sizes)) + 1)
        if name != 'ko_fall' and abs(by.max() - 880) > 4:
            problems.append(f'{name}: 발끝이 지면에서 {by.max() - 880:+d}px 떠 있다')
        core = ndimage.binary_erosion(a, np.ones((17, 17)))
        cl, cn = ndimage.label(core)
        if cn:
            cores.append(float(np.sqrt(ndimage.sum(core, cl, range(1, cn + 1)).max())))
    if cores:
        spread = (max(cores) - min(cores)) / statistics.mean(cores) * 100
        print(f'   몸통 크기 편차 {spread:.0f}%  ({min(cores):.0f}~{max(cores):.0f})')
        if spread > 14:
            problems.append(f'몸통 편차 {spread:.0f}% — 그림 배율이 흔들린다(14% 이하 권장)')
    return problems


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('gid', help='장수 id (예: taishi_ci)')
    ap.add_argument('sheets', nargs='*', help='1차·2차 시트 경로')
    ap.add_argument('--latest', type=int, help='다운로드 폴더의 최근 N장을 쓴다')
    ap.add_argument('--size', type=float, default=1.0, help='체격 배율(게임에서 쓸 값)')
    args = ap.parse_args()

    sheets = args.sheets
    if args.latest:
        dl = sorted(glob.glob(os.path.expanduser('~/Downloads/*.png')), key=os.path.getmtime)
        sheets = dl[-args.latest:]
    if len(sheets) != 2:
        ap.error('시트 2장(1차·2차)이 필요하다')

    src_dir = os.path.join(ROOT, 'asset_img', args.gid)
    os.makedirs(src_dir, exist_ok=True)
    kept = []
    for i, (s, names) in enumerate(zip(sheets, [P1, P2]), 1):
        dst = os.path.join(src_dir, f'{args.gid}_p{i}_green.png')
        shutil.copy(s, dst)
        cut = os.path.join(ROOT, 'asset_img', f'cut_{args.gid}_{i}')
        shutil.rmtree(cut, ignore_errors=True)
        print(f'[{i}차] {os.path.basename(s)}')
        cmd = [os.path.join(TOOLS, 'split_pose_sheet.py'), dst, '--out', cut,
               '--names', ','.join(names)]
        if i == 2:
            cmd += ['--lift', 'ko_fall=110']
        run(cmd)
        kept.append(cut)

    out = os.path.join(ROOT, 'assets', 'arcade_duel', f'{args.gid}_states')
    print('[통일]')
    run([os.path.join(TOOLS, 'harmonize_poses.py')] + kept + ['--out', out])

    print('[검증]')
    problems = verify(out)
    if problems:
        for p in problems:
            print(f'   ✗ {p}')
        print(f'\n{len(problems)}건 — 해당 컷을 다시 뽑는 편이 낫다')
    else:
        print('   ○ 이상 없음')
    print(f'\n→ 게임에서 확인: duel_v2.html?boss={args.gid}')


if __name__ == '__main__':
    main()
