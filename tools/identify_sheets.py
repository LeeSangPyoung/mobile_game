#!/usr/bin/env python3
"""받은 시트가 어느 장수인지 자동으로 알아낸다.

생성 결과 파일명은 전부 'ChatGPT Image ....png' 라 누가 누군지 알 수 없다.
장수마다 갑옷·망토 배색이 뚜렷하게 다르므로, 레퍼런스 이미지와 **색 분포**를
비교하면 상당히 정확하게 맞출 수 있다.

  python3 tools/identify_sheets.py --latest 20

같이 하는 일:
  · 1차/2차 판별 (2차에는 바닥에 누운 KO 컷이 있어 납작한 덩어리가 나온다)
  · 시간순으로 1차-2차 짝짓기
"""
import argparse
import glob
import os
import sys

import numpy as np
from PIL import Image
from scipy import ndimage

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
REF_DIR = os.path.join(ROOT, 'asset_img', 'refs')
sys.path.insert(0, os.path.join(ROOT, 'tools'))
from split_pose_sheet import chroma_key  # noqa: E402

BINS = 6          # 채널당 색 구간 — 너무 잘게 나누면 명암 차이에 흔들린다


def signature(rgb, mask):
    """캐릭터 픽셀의 색 분포. 밝기 차이에 덜 민감하도록 정규화한다."""
    px = rgb[mask].astype(float)
    if len(px) < 500:
        return None
    # 밝기를 나눠 색상 비율만 남긴다 (조명·대비 차이 흡수)
    s = px.sum(axis=1, keepdims=True) + 1e-6
    chrom = px / s
    idx = np.clip((chrom * BINS).astype(int), 0, BINS - 1)
    flat = idx[:, 0] * BINS * BINS + idx[:, 1] * BINS + idx[:, 2]
    h = np.bincount(flat, minlength=BINS ** 3).astype(float)
    # 밝기 분포도 조금 섞는다 — 배색이 비슷한 장수를 가른다
    lum = np.clip((px.mean(axis=1) / 256 * 8).astype(int), 0, 7)
    h2 = np.bincount(lum, minlength=8).astype(float)
    v = np.concatenate([h / h.sum(), 0.35 * h2 / h2.sum()])
    return v


def sheet_info(path):
    rgb = np.array(Image.open(path).convert('RGB'))
    fg = chroma_key(rgb)
    if fg is None:
        return None
    lbl, n = ndimage.label(fg)
    sizes = ndimage.sum(fg, lbl, range(1, n + 1))
    flat = 0.0
    for i in range(1, n + 1):
        if sizes[i - 1] < 3000:
            continue
        ys, xs = np.nonzero(lbl == i)
        flat = max(flat, (xs.max() - xs.min()) / max(1, ys.max() - ys.min()))
    return {'sig': signature(rgb, fg), 'batch': 2 if flat > 2.2 else 1, 'flat': flat}


def ref_signatures():
    out = {}
    for f in sorted(glob.glob(os.path.join(REF_DIR, '*.png'))):
        gid = os.path.basename(f)[:-4]
        rgb = np.array(Image.open(f).convert('RGB'))
        fg = chroma_key(rgb)
        if fg is None:
            continue
        sig = signature(rgb, fg)
        if sig is not None:
            out[gid] = sig
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--latest', type=int, default=20)
    ap.add_argument('--dir', default='~/Downloads')
    args = ap.parse_args()

    files = sorted(glob.glob(os.path.expanduser(os.path.join(args.dir, '*.png'))),
                   key=os.path.getmtime)[-args.latest:]
    print(f'레퍼런스 서명 계산 중...')
    refs = ref_signatures()
    print(f'  {len(refs)}명\n')

    rows = []
    for f in files:
        info = sheet_info(f)
        if not info or info['sig'] is None:
            continue
        # 코사인 거리로 가장 가까운 장수
        cand = sorted(((float(np.dot(info['sig'], s) /
                        (np.linalg.norm(info['sig']) * np.linalg.norm(s) + 1e-9)), gid)
                       for gid, s in refs.items()), reverse=True)[:3]
        rows.append((f, info['batch'], cand))

    print(f'{"시각":<10} {"차수":<5} {"1순위":<14} {"점수":<7} 2·3순위')
    for f, batch, cand in rows:
        t = os.path.basename(f)[19:-4].replace('_', ':')
        alts = ' · '.join(f'{g}({s:.3f})' for s, g in cand[1:])
        print(f'{t:<10} {batch}차   {cand[0][1]:<14} {cand[0][0]:.3f}   {alts}')

    # 시간순 짝짓기
    print('\n[짝짓기]')
    i, pairs = 0, []
    while i < len(rows) - 1:
        if rows[i][1] == 1 and rows[i + 1][1] == 2:
            pairs.append((rows[i], rows[i + 1]))
            i += 2
        else:
            print(f'  ! {os.path.basename(rows[i][0])[19:-4]} — {rows[i][1]}차가 홀로 있다(재시도로 보임)')
            i += 1
    for p1, p2 in pairs:
        print(f'  {p1[2][0][1]:<14} {os.path.basename(p1[0])[19:-4]} + {os.path.basename(p2[0])[19:-4]}')


if __name__ == '__main__':
    main()
