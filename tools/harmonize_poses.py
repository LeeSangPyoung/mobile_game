#!/usr/bin/env python3
"""여러 시트에서 뽑은 포즈들의 크기를 하나의 기준으로 맞춘다.

split_pose_sheet.py 는 **시트 한 장 안에서만** 크기를 맞춘다. 그래서 공격 시트와
상태(피격·가드·KO) 시트를 따로 뽑으면 두 세트의 크기가 서로 어긋난다 —
실제로 조운은 가드·피격 자세가 공격 자세보다 15% 컸다.
캐릭터가 맞을 때마다 커졌다 작아졌다 한 원인이 이것이다.

여기서 하는 일:
  1) 무기를 걷어낸 몸통 크기로 각 세트의 대표값(중앙값)을 잰다
  2) 'idle' 이 든 세트를 기준으로 나머지 세트를 통째로 맞춘다
     (세트 **안**의 자세별 차이는 그대로 둔다 — 웅크린 자세는 실제로 작다)
  3) 캐릭터마다 idle 크기를 동일한 목표값으로 맞춘다
     → 장수 간 덩치 차이는 게임 코드의 CHAR_SIZE 하나로만 준다

크기 조정은 규격 기준점(중심 x=CX, 발끝 y=BASELINE)을 축으로 하므로
정렬은 그대로 유지된다.

  python3 tools/harmonize_poses.py asset_img/cut_atk asset_img/cut --out assets/arcade_duel/zhao_yun_states
"""
import argparse
import glob
import json
import os
import statistics

import numpy as np
from PIL import Image
from scipy import ndimage

CANVAS_W, CANVAS_H, CX, BASELINE = 1280, 1024, 640, 880
TARGET_CORE = 360.0        # 모든 캐릭터의 idle 이 갖게 될 몸통 크기


def core_size(img):
    """무기를 걷어낸 몸통의 선형 크기. 자세보다 '그려진 배율'에 반응한다."""
    a = np.array(img.getchannel('A')) > 16
    core = ndimage.binary_erosion(a, np.ones((17, 17)))
    lbl, n = ndimage.label(core)
    if n == 0:
        return None
    return float(np.sqrt(ndimage.sum(core, lbl, range(1, n + 1)).max()))


def torso_center(img):
    """몸통(머리·어깨)의 중심 x. 무기의 영향을 받지 않는 유일하게 안정적인 기준.

    왜 필요한가: 정규화는 '가장 큰 덩어리'의 중심을 캔버스 중앙에 맞추는데,
    무기가 손을 통해 몸에 붙어 있어서 도끼·창까지 그 덩어리에 포함된다.
    그래서 화웅은 몸이 중앙에서 55px 밀린 채 저장됐고, 발밑에 그려야 할
    그림자가 도끼 아래에 찍혔다.
    아래쪽(발·무기)은 자세마다 제멋대로라 못 쓰고, 머리·어깨는 언제나 몸 위에 있다.
    """
    a = np.array(img.getchannel('A')) > 16
    if not a.any():
        return None
    ys, _ = np.nonzero(a)
    y0, y1 = ys.min(), ys.max()
    h = max(1, y1 - y0)
    core = ndimage.binary_erosion(a, np.ones((13, 13)))
    top = core[y0:y0 + max(8, int(h * 0.30))]
    tx = np.nonzero(top.any(axis=0))[0]
    if len(tx) < 4:
        return None
    return float((tx.min() + tx.max()) / 2), float(tx.max() - tx.min())


def foot_span(img, body_h):
    """양발이 놓인 x 구간. 바닥에 닿은 무기는 걸러낸다.

    화웅 대기 자세의 바닥 밴드에는 덩어리가 셋 있다 —
    왼쪽 장화 / 오른쪽 장화 / **도끼날**. 도끼까지 발로 세면 중심이 85px 밀리고,
    그림자가 발이 아니라 도끼 밑에 찍힌다.
    그래서 '몸통에 가장 가까운 덩어리'를 먼저 발로 확정하고,
    거기서 한 걸음 거리(키의 42%) 안에 있는 덩어리만 나머지 발로 인정한다.
    """
    a = np.array(img.getchannel('A')) > 16
    if not a.any():
        return None
    ys, _ = np.nonzero(a)
    y0, y1 = ys.min(), ys.max()
    h = max(1, y1 - y0)

    tc = torso_center(img)
    torso_cx = tc[0] if tc else CX

    band = np.zeros_like(a)
    lo = max(0, int(y1 - h * 0.06))
    band[lo:y1 + 1] = a[lo:y1 + 1]
    lbl, n = ndimage.label(band)
    blobs = []
    for i in range(1, n + 1):
        cx = np.nonzero((lbl == i).any(axis=0))[0]
        if len(cx) < 6:
            continue
        blobs.append((int(cx.min()), int(cx.max()), float((cx.min() + cx.max()) / 2)))
    if not blobs:
        return None

    primary = min(blobs, key=lambda b: abs(b[2] - torso_cx))   # 몸통에 가장 가까운 = 발
    reach = body_h * 0.42                                      # 한 걸음 거리
    feet = [b for b in blobs if abs(b[2] - primary[2]) <= reach]
    return min(b[0] for b in feet), max(b[1] for b in feet)


def _unused_foot_span(img):
    """(구) 양발 추정 — 무기 오검출이 많아 보류.

    '가장 큰 덩어리'의 중심을 쓰면 안 된다. 무기가 손을 통해 몸에 붙어 있어서
    도끼·창까지 몸으로 계산되고, 그 중심은 실제 발에서 크게 벗어난다
    (화웅은 그림자가 도끼 밑에 그려졌다).
    그래서 위쪽(머리·어깨)으로 몸의 중심을 잡고, 바닥 근처에서 그 중심에
    가까운 덩어리만 발로 인정한다.
    """
    a = np.array(img.getchannel('A')) > 16
    if not a.any():
        return None
    ys, xs = np.nonzero(a)
    y0, y1 = ys.min(), ys.max()
    h = max(1, y1 - y0)

    core = ndimage.binary_erosion(a, np.ones((13, 13)))
    top = core[y0:y0 + int(h * 0.35)]
    tx = np.nonzero(top.any(axis=0))[0]
    torso_cx = (tx.min() + tx.max()) / 2 if len(tx) else (xs.min() + xs.max()) / 2
    body_w = (tx.max() - tx.min()) if len(tx) else (xs.max() - xs.min())

    band = np.zeros_like(a)
    lo = max(0, int(y1 - h * 0.09))
    band[lo:y1 + 1] = a[lo:y1 + 1]
    lbl, n = ndimage.label(band)
    keep = []
    for i in range(1, n + 1):
        cxs = np.nonzero((lbl == i).any(axis=0))[0]
        if len(cxs) < 6:
            continue
        c = (cxs.min() + cxs.max()) / 2
        if abs(c - torso_cx) <= body_w * 0.95:      # 너무 멀면 무기다
            keep.append((cxs.min(), cxs.max()))
    if not keep:
        return (torso_cx - body_w * 0.35, torso_cx + body_w * 0.35)
    return (min(k[0] for k in keep), max(k[1] for k in keep))


def rescale(img, k):
    """규격 기준점(CX, BASELINE)을 축으로 확대·축소. 정렬이 깨지지 않는다."""
    if abs(k - 1) < 1e-3:
        return img
    w, h = max(1, round(img.width * k)), max(1, round(img.height * k))
    r = img.resize((w, h), Image.LANCZOS)
    out = Image.new('RGBA', (CANVAS_W, CANVAS_H), (0, 0, 0, 0))
    out.alpha_composite(r, (round(CX - CX * k), round(BASELINE - BASELINE * k)))
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('sets', nargs='+', help='포즈 세트 폴더들 (첫 폴더에 idle 이 있어야 한다)')
    ap.add_argument('--out', required=True, help='webp 출력 폴더')
    ap.add_argument('--target', type=float, default=TARGET_CORE)
    args = ap.parse_args()

    os.makedirs(args.out, exist_ok=True)

    loaded, medians, ref_core = [], [], None
    for d in args.sets:
        files = sorted(glob.glob(os.path.join(d, '*.png')))
        imgs = [(os.path.basename(f)[:-4], Image.open(f).convert('RGBA')) for f in files]
        cores = [(n, core_size(im)) for n, im in imgs]
        vals = [c for _, c in cores if c]
        medians.append(statistics.median(vals) if vals else 1.0)
        loaded.append((d, imgs, dict(cores)))
        for n, c in cores:
            if n == 'idle' and c:
                ref_core = c

    if not ref_core:
        ref_core = medians[0]
    base = args.target / ref_core          # idle 을 목표 크기로
    print(f'기준 idle 몸통 {ref_core:.1f} → 목표 {args.target:.0f}  (배율 {base:.3f})')

    tips = {}
    for (d, imgs, cores), med in zip(loaded, medians):
        # 세트 통째 보정 — 'idle 이 든 세트'의 중앙값에 맞춘다
        k = base * (medians[0] / med)
        print(f'  {os.path.basename(d):14s} 세트 중앙값 {med:6.1f} → 배율 {k:.3f}')
        pj = os.path.join(d, 'poses.json')
        meta = json.load(open(pj)) if os.path.exists(pj) else {'poses': {}}
        for name, im in imgs:
            out = rescale(im, k)
            out.save(os.path.join(args.out, name + '.webp'), quality=90, method=6)
            entry = {}
            t = meta.get('poses', {}).get(name)
            if t:   # 창끝 좌표도 같은 축으로 옮긴다 — 안 하면 이펙트가 허공에서 난다
                entry['tipX'] = round(CX + (t['tipX'] - CX) * k)
                entry['tipY'] = round(BASELINE + (t['tipY'] - BASELINE) * k)
            fs = foot_span(out, 600)   # 최종 이미지에서 잰다
            if fs:
                entry['footL'], entry['footR'] = int(fs[0]), int(fs[1])
            if entry:
                tips[name] = entry

    # 최종 몸 높이를 기록한다. 게임 코드가 이 값으로 렌더 배율을 정한다 —
    # 620 같은 가정값을 박아두면 여기서 크기를 조정한 순간 어긋난다.
    idle_path = os.path.join(args.out, 'idle.webp')
    body_h = 0
    if os.path.exists(idle_path):
        im = Image.open(idle_path).convert('RGBA')
        a = np.array(im.getchannel('A')) > 16
        lbl, n = ndimage.label(a)
        if n:
            sizes = ndimage.sum(a, lbl, range(1, n + 1))
            ys, _ = np.nonzero(lbl == int(np.argmax(sizes)) + 1)
            body_h = int(ys.max() - ys.min())
    print(f'  최종 몸 높이 {body_h}px  (게임 렌더 배율의 기준)')

    json.dump({'canvasW': CANVAS_W, 'canvasH': CANVAS_H, 'cx': CX,
               'ground': BASELINE, 'bodyH': body_h, 'poses': tips},
              open(os.path.join(args.out, 'poses.json'), 'w'), ensure_ascii=False, indent=2)
    print(f'→ {args.out}  포즈 {len(tips)}개')


if __name__ == '__main__':
    main()
