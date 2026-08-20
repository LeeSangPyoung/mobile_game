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
import json
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


def _narrowest_walk(out_dir):
    """걷기 컷 중 '통과 자세'(두 발이 모인 것)들의 이름 집합.

    다리를 모으고 망토가 접히면 침식 후 덩어리가 작게 나온다. 실제 크기는
    정상인데 '이 컷만 작게 그렸다'로 오판하므로 크기 편차 계산에서 뺀다.
    (KO 자세를 빼는 것과 같은 이유다.)
    """
    spans = {}
    for w in ('walk1', 'walk2', 'walk3', 'walk4'):
        f = os.path.join(out_dir, w + '.webp')
        if not os.path.exists(f):
            continue
        a = np.array(Image.open(f).convert('RGBA').getchannel('A')) > 16
        lbl, n = ndimage.label(a)
        if not n:
            continue
        m = lbl == int(np.argmax(ndimage.sum(a, lbl, range(1, n + 1)))) + 1
        ys, _ = np.nonzero(m)
        bx = np.nonzero(m[ys.max() - 40:ys.max() + 1, :])[1]
        if not len(bx):
            continue
        spans[w] = bx.max() - bx.min()
    if not spans:
        return set()
    widest = max(spans.values())
    return {w for w, v in spans.items() if v < widest * 0.55}


def verify(out_dir):
    """장수마다 자동으로 돌리는 검사. 전부 실제로 터졌던 문제들이다."""
    files = sorted(glob.glob(os.path.join(out_dir, '*.webp')))
    narrow_walk = _narrowest_walk(out_dir)
    problems, cores = [], []
    # 20컷이 기본. 걷기를 4컷으로 받으면 21컷이 된다(통과 자세가 두 번 재생되지 않는다).
    if len(files) not in (20, 21):
        problems.append(f'컷이 {len(files)}개 (20 또는 21개여야 한다)')
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
        # 누운·뜬 자세는 실루엣이 원래 작다 — 크기 편차 계산에서 뺀다.
        # (여포 ko_down 이 -12% 로 잡혀 멀쩡한 세트가 경고를 받았다)
        # 통과 자세(walk 중 두 발이 가장 모인 컷)도 뺀다. 다리를 모으고 망토가 접혀서
        # 침식 후 덩어리가 작게 나올 뿐, 실제 크기는 정상이다(여포가 -15% 로 잡혔다).
        if name not in ('ko_down', 'ko_fall') and name not in narrow_walk:
            core = ndimage.binary_erosion(a, np.ones((17, 17)))
            cl, cn = ndimage.label(core)
            if cn:
                cores.append(float(np.sqrt(ndimage.sum(core, cl, range(1, cn + 1)).max())))
    if cores:
        spread = (max(cores) - min(cores)) / statistics.mean(cores) * 100
        print(f'   몸통 크기 편차 {spread:.0f}%  ({min(cores):.0f}~{max(cores):.0f})  ※ KO 자세 제외')
        if spread > 14:
            problems.append(f'몸통 편차 {spread:.0f}% — 그림 배율이 흔들린다(14% 이하 권장)')
    return problems


def fix_attack_order(out_dir):
    """공격 3단계가 뒤섞인 경우 바로잡는다.

    타격(impact)은 무기가 가장 앞으로 나간 순간이어야 한다. 생성 결과가
    가끔 순서를 바꿔 그려서(후딜이 타격보다 앞으로 뻗음) 휘두르는 방향이
    거꾸로 보인다. 무기끝 x좌표는 이미 재 놓았으므로 그것으로 판정·교체한다.

    예비는 '가장 뒤로 당긴' 프레임이므로 함께 정렬한다.
    """
    pj = os.path.join(out_dir, 'poses.json')
    if not os.path.exists(pj):
        return []
    meta = json.load(open(pj))
    poses = meta.get('poses', {})
    fixed = []
    for mv in ('slash', 'thrust', 'heavy'):
        names = [f'{mv}_{s}' for s in ('windup', 'impact', 'recovery')]
        tips = [poses.get(n, {}).get('tipX') for n in names]
        if any(t is None for t in tips):
            continue
        if tips[1] >= max(tips[0], tips[2]):
            continue                       # 타격이 가장 앞 — 정상
        # 가장 앞으로 뻗은 것을 타격, 가장 뒤를 예비로
        order = sorted(range(3), key=lambda i: tips[i])
        new = [names[order[0]], names[order[2]], names[order[1]]]
        if new == names:
            continue
        imgs = {n: Image.open(os.path.join(out_dir, n + '.webp')).convert('RGBA')
                for n in names}
        keep = {n: dict(poses.get(n, {})) for n in names}
        for dst, src in zip(names, new):
            imgs[src].save(os.path.join(out_dir, dst + '.webp'), quality=90, method=6)
            poses[dst] = keep[src]
        fixed.append(f'{mv}: ' + ' → '.join(s.split("_")[-1] for s in new))
    if fixed:
        json.dump(meta, open(pj, 'w'), ensure_ascii=False, indent=1)
    return fixed


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

    swapped = fix_attack_order(out)
    if swapped:
        print('[공격 순서 교정] 타격이 가장 앞으로 뻗도록 재배치')
        for x in swapped:
            print('   · ' + x)

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
