#!/usr/bin/env python3
"""창끝 좌표를 그림에서 다시 재어 poses.json 에 적는다.

무기 아우라와 휘두른 궤적이 이 좌표에 붙는다. 틀리면 빛이 허공이나 등 뒤에서 난다.

기존 검출은 '몸 중심에서 가장 먼 불투명 픽셀'인데, 자루 끝(물미)이 날보다
멀면 반대쪽을 집는다. 여포 slash_impact 은 창끝이 418 로 잡혔다 — 몸 중심이
659 이니 베는 순간 빛이 등 뒤에서 났다.

타격(impact)과 후딜(recovery)에서는 무기가 앞으로 나가 있어야 하므로
**몸 중심보다 앞쪽**에서 가장 먼 점을 고른다. 예비(windup)는 무기를 뒤로
당긴 자세라 그대로 둔다.

  python3 tools/fix_tips.py --all
"""
import argparse
import glob
import json
import os

import numpy as np
from PIL import Image
from scipy import ndimage

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
STATES = os.path.join(ROOT, 'assets', 'arcade_duel')
FORWARD = ('_impact', '_recovery')     # 무기가 앞으로 나가 있어야 하는 컷


def tip_of(path, forward_only):
    a = np.array(Image.open(path).convert('RGBA').getchannel('A')) > 24
    if not a.any():
        return None
    ys, xs = np.nonzero(a)
    lbl, n = ndimage.label(a)
    body = lbl == int(np.argmax(ndimage.sum(a, lbl, range(1, n + 1)))) + 1
    by, bx = ndimage.center_of_mass(body)
    d = (xs - bx) ** 2 + (ys - by) ** 2
    if forward_only:
        sel = xs > bx
        if sel.any():
            d, xs, ys = d[sel], xs[sel], ys[sel]
    i = int(np.argmax(d))
    return int(xs[i]), int(ys[i])


def fix(gid):
    d = os.path.join(STATES, gid + '_states')
    pj = os.path.join(d, 'poses.json')
    if not os.path.exists(pj):
        return []
    meta = json.load(open(pj, encoding='utf-8'))
    poses = meta.setdefault('poses', {})
    moved = []
    for f in sorted(glob.glob(os.path.join(d, '*.webp'))):
        n = os.path.basename(f)[:-5]
        t = tip_of(f, any(n.endswith(s) for s in FORWARD))
        if t is None:
            continue
        old = poses.get(n, {})
        if 'tipX' in old:
            dd = ((old['tipX'] - t[0]) ** 2 + (old['tipY'] - t[1]) ** 2) ** 0.5
            if dd > 30:
                moved.append((n, (old['tipX'], old['tipY']), t, dd))
        poses.setdefault(n, {}).update({'tipX': t[0], 'tipY': t[1]})
    json.dump(meta, open(pj, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
    return moved


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
    total = 0
    for gid in gids:
        for n, old, new, dd in fix(gid):
            print(f'{gid:<14} {n:<16} {old} → {new}   {dd:.0f}px')
            total += 1
    print(f'\n{total}컷 교정' if total else '\n교정할 컷 없음')


if __name__ == '__main__':
    main()
