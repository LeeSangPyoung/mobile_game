#!/usr/bin/env python3
"""이미 만든 장수 세트에서 일부 컷만 갈아 끼운다.

전체를 다시 뽑지 않고 문제 있는 컷만 교체하기 위한 도구.
대기·걷기가 정면으로 나온 장수들을 측면 버전으로 바꾸는 데 쓴다.

새 컷은 **기존 세트의 크기에 맞춰서** 넣는다. 그냥 덮어쓰면 그 컷만
덩치가 달라져서, 걷다가 공격하면 크기가 튀는 문제가 되살아난다.

  python3 tools/patch_general.py guan_yu ~/Downloads/새시트.png
  python3 tools/patch_general.py guan_yu --latest      # 다운로드 최신 1장
"""
import argparse
import glob
import json
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
CANVAS_W, CANVAS_H, CX, BASELINE = 1280, 1024, 640, 880
# 걷기 4컷 = 앞접지·통과·뒷접지·통과(반대 다리). 반복 프레임이 없는 표준 사이클이다.
# 3컷이면 통과 컷을 두 번 써야 해서 '두 장면이 번갈아 나온다'고 읽힌다.
DEFAULT_NAMES = ['idle', 'walk1', 'walk2', 'walk3', 'walk4']


def core_size(img):
    a = np.array(img.getchannel('A')) > 16
    core = ndimage.binary_erosion(a, np.ones((17, 17)))
    lbl, n = ndimage.label(core)
    if n == 0:
        return None
    return float(np.sqrt(ndimage.sum(core, lbl, range(1, n + 1)).max()))


def rescale(img, k):
    """규격 기준점(CX, BASELINE)을 축으로 — 정렬을 유지한 채 크기만 바꾼다."""
    if abs(k - 1) < 1e-3:
        return img
    w, h = max(1, round(img.width * k)), max(1, round(img.height * k))
    r = img.resize((w, h), Image.LANCZOS)
    out = Image.new('RGBA', (CANVAS_W, CANVAS_H), (0, 0, 0, 0))
    out.alpha_composite(r, (round(CX - CX * k), round(BASELINE - BASELINE * k)))
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('gid')
    ap.add_argument('sheet', nargs='?')
    ap.add_argument('--latest', action='store_true')
    ap.add_argument('--names', default=','.join(DEFAULT_NAMES))
    args = ap.parse_args()

    sheet = args.sheet
    if args.latest:
        sheet = sorted(glob.glob(os.path.expanduser('~/Downloads/*.png')),
                       key=os.path.getmtime)[-1]
    if not sheet:
        ap.error('시트 경로가 필요하다')

    names = [n.strip() for n in args.names.split(',') if n.strip()]
    out_dir = os.path.join(ROOT, 'assets', 'arcade_duel', f'{args.gid}_states')
    if not os.path.isdir(out_dir):
        ap.error(f'{out_dir} 가 없다 — make_general.py 로 먼저 만들어야 한다')

    # 1) 새 시트를 분리·정렬
    cut = os.path.join(ROOT, 'asset_img', f'patch_{args.gid}')
    shutil.rmtree(cut, ignore_errors=True)
    src_dir = os.path.join(ROOT, 'asset_img', args.gid)
    os.makedirs(src_dir, exist_ok=True)
    dst = os.path.join(src_dir, f'{args.gid}_patch_green.png')
    shutil.copy(sheet, dst)
    print(f'[분리] {os.path.basename(sheet)}')
    r = subprocess.run([sys.executable, os.path.join(TOOLS, 'split_pose_sheet.py'),
                        dst, '--out', cut, '--names', ','.join(names)]
                       # 걷기가 든 시트만 보정을 끈다.
                       # 두 발을 모은 통과 자세는 몸통 지표가 작게 나와 '작게 그렸다'로
                       # 오판되고, 그대로 두면 그 컷만 커진다(여포 walk2 가 16% 커졌다).
                       # 걷기가 없는 시트(공격·반응)는 보정이 필요하다 — 안량 공격 9컷은
                       # 컷 간 크기 편차가 27% 였고 보정을 켜니 5% 가 됐다.
                       + (['--no-fit-body'] if any(n.startswith('walk') for n in names) else []),
                       capture_output=True, text=True, cwd=ROOT,
                       encoding='utf-8', errors='replace')
    for line in (r.stdout + r.stderr).splitlines():
        if any(k in line for k in ('컷', '보정', '!', '배율')):
            print('   ' + line.strip())

    made = sorted(glob.glob(os.path.join(cut, '*.png')))
    if len(made) != len(names):
        print(f'   ✗ 컷이 {len(made)}개 — {len(names)}개여야 한다. 중단.')
        return

    # 2) 기존 세트의 크기 기준 — 교체 대상이 아닌 컷들의 중앙값
    keep = [f for f in glob.glob(os.path.join(out_dir, '*.webp'))
            if os.path.basename(f)[:-5] not in names]
    ref = statistics.median([c for c in (core_size(Image.open(f).convert('RGBA'))
                                         for f in keep) if c])
    new = statistics.median([c for c in (core_size(Image.open(f)) for f in made) if c])
    k = ref / new
    print(f'[크기 맞춤] 기존 {ref:.0f} / 새 컷 {new:.0f} → 배율 {k:.3f}')

    # 3) 교체 + 창끝 좌표 갱신
    pj = os.path.join(cut, 'poses.json')
    meta = json.load(open(pj)) if os.path.exists(pj) else {'poses': {}}
    tgt = os.path.join(out_dir, 'poses.json')
    cur = json.load(open(tgt)) if os.path.exists(tgt) else {'poses': {}}
    for f in made:
        n = os.path.basename(f)[:-4]
        img = rescale(Image.open(f).convert('RGBA'), k)
        img.save(os.path.join(out_dir, n + '.webp'), quality=90, method=6)
        t = meta.get('poses', {}).get(n)
        if t and 'tipX' in t:
            cur.setdefault('poses', {})[n] = {
                'tipX': round(CX + (t['tipX'] - CX) * k),
                'tipY': round(BASELINE + (t['tipY'] - BASELINE) * k)}
        print(f'   ○ {n} 교체')
    # '가속' 컷(*_swing)을 넣었으면 표시해 둔다 — 게임이 이 표시를 보고
    # 그 파일들을 요청한다. 없으면 아예 안 부르므로 404 가 안 뜬다.
    if any(n.endswith('_swing') for n in names):
        cur['swing'] = True
    json.dump(cur, open(tgt, 'w'), ensure_ascii=False, indent=1)

    # 4) 검증
    cores = [c for c in (core_size(Image.open(f).convert('RGBA'))
                         for f in glob.glob(os.path.join(out_dir, '*.webp'))) if c]
    spread = (max(cores) - min(cores)) / statistics.mean(cores) * 100
    print(f'[검증] 몸통 편차 {spread:.0f}%  ' + ('○' if spread <= 14 else '✗ 14% 초과'))
    print(f'\n→ duel_v2.html 에서 {args.gid} 확인')


if __name__ == '__main__':
    main()
