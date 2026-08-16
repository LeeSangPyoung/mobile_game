#!/usr/bin/env python3
"""컨택트 시트 → 포즈별 개별 PNG(투명 배경, 규격 정렬).

생성 모델은 "1 이미지 = 1 포즈, 배경 투명"을 거의 지키지 않는다. 여러 컷을
한 장에 늘어놓고 배경까지 칠해서 준다. 그걸 게임에 쓸 수 있게 되돌리는 도구.

  1) 배경 제거 — 배경은 매끄러운 그라데이션이고 캐릭터는 디테일이 많다.
     테두리에서 시작하는 flood fill 로 '연결된 매끄러운 영역'만 지운다.
  2) 컷 분리 — 남은 알파를 연결요소로 묶고, 무기·망토처럼 떨어진 조각은
     가까운 덩어리에 합친다.
  3) 규격 정렬 — 발끝을 같은 y, 몸통 중심을 같은 x, 키를 같게 맞춘다.
     이 단계가 핵심이다. 이걸 해야 컷을 넘겨도 캐릭터가 튀지 않는다.

  python3 tools/split_pose_sheet.py asset_img/<시트>.png --out asset_img/cut --prefix zy
"""
import argparse
import json
import os

import numpy as np
from PIL import Image
from scipy import ndimage

# 출력 규격 — 게임 코드(duel_v2.html 의 STATE_* 상수)와 반드시 일치해야 한다.
# 캔버스가 왜 이렇게 넓은가: 찌르기·강베기는 창이 몸 중심에서 570px 넘게 뻗는다.
# 768 캔버스에서는 창끝이 캔버스 밖으로 나가 잘렸다.
CANVAS_W = 1280     # 가로 — 창이 가장 멀리 뻗는 자세 기준
CANVAS_H = 1024     # 세로
CX = 640            # 몸통 중심 x — 모든 컷 동일
BASELINE = 880      # 발끝 y — 모든 컷 동일
H_TARGET = 620      # 캐릭터 키(px) — 기준 컷 기준


def chroma_key(rgb):
    """단색 초록 배경을 뺀다. 없으면 None.

    이미지 모델은 '투명 배경'을 제대로 못 만든다. 대신 순수 초록을 깔아 달라고
    하면 확실하게 분리된다 — 조운 배색(은/금/청/백)에 초록이 없어서 안전하다.
    """
    a = rgb.astype(int)
    r, g, b = a[..., 0], a[..., 1], a[..., 2]
    key = (g > 120) & (g - r > 60) & (g - b > 60)
    if key.mean() < 0.25:
        return None
    fg = ~key
    fg = ndimage.binary_opening(fg, np.ones((3, 3)))      # 초록 위 잔점 제거
    fg = ndimage.binary_closing(fg, np.ones((5, 5)))
    fg = ndimage.binary_fill_holes(fg)
    return fg


def despill(rgb, fg):
    """가장자리에 남은 초록 테두리를 없앤다 — 안 하면 캐릭터에 초록 실선이 생긴다."""
    out = rgb.astype(np.int16).copy()
    r, g, b = out[..., 0], out[..., 1], out[..., 2]
    cap = np.maximum(r, b)
    spill = fg & (g > cap + 8)
    g[spill] = cap[spill] + 8
    return np.clip(out, 0, 255).astype(np.uint8)


def remove_background(rgb, tol=34):
    """테두리에서 번져나가는 flood fill 로 배경을 지운다."""
    a = rgb.astype(np.int16)
    h, w, _ = a.shape

    # 배경 후보: 테두리 픽셀들의 색과 비슷하면서 '평평한'(주변과 색차가 작은) 곳
    border = np.concatenate([a[0], a[-1], a[:, 0], a[:, -1]])
    # 그라데이션이라 대표색 하나로는 부족하다 — 국소 대비로 판단한다
    gray = a.mean(axis=2)
    # 국소 표준편차: 배경은 매끄러워 작고, 캐릭터는 크다
    m = ndimage.uniform_filter(gray, 7)
    m2 = ndimage.uniform_filter(gray * gray, 7)
    local_std = np.sqrt(np.maximum(m2 - m * m, 0))

    flat = local_std < 6.0
    dark = gray < 150

    seed = np.zeros((h, w), bool)
    seed[0, :] = seed[-1, :] = seed[:, 0] = seed[:, -1] = True
    seed &= flat

    # flat & dark 영역 중 테두리와 연결된 덩어리만 배경
    cand = flat & dark
    lbl, n = ndimage.label(cand)
    bg_labels = set(np.unique(lbl[seed & cand]))
    bg_labels.discard(0)
    bg = np.isin(lbl, list(bg_labels))

    # 캐릭터 안쪽에 생긴 작은 구멍은 되돌린다
    fg = ~bg
    fg = ndimage.binary_closing(fg, np.ones((5, 5)))
    fg = ndimage.binary_fill_holes(fg)
    return fg


def _bands(profile, min_run, gap_thresh):
    """1차원 투영에서 '내용이 있는 구간'들을 뽑는다."""
    on = profile > gap_thresh
    bands, start = [], None
    for i, v in enumerate(on):
        if v and start is None:
            start = i
        elif not v and start is not None:
            if i - start >= min_run:
                bands.append((start, i))
            start = None
    if start is not None and len(on) - start >= min_run:
        bands.append((start, len(on)))
    return bands


def _valley_cuts(cols, edge_margin=120, min_cell=200, depth=0.22):
    """열 투영의 골짜기에서 자른다 — 창이 옆 컷과 겹쳐도 나뉜다."""
    sm = ndimage.uniform_filter1d(cols.astype(float), 41)
    peak = sm.max()
    cands = [i for i in range(edge_margin, len(sm) - edge_margin)
             if sm[i] == sm[max(0, i - 50):i + 50].min() and sm[i] < peak * depth]
    # 붙어 있는 후보는 하나로
    groups = []
    for i in cands:
        if groups and i - groups[-1][-1] <= 60:
            groups[-1].append(i)
        else:
            groups.append([i])
    cuts = [int(np.mean(g)) for g in groups]
    # 너무 가까운 절단선은 더 깊은 쪽만 남긴다
    kept = []
    for c in cuts:
        if kept and c - kept[-1] < min_cell:
            if sm[c] < sm[kept[-1]]:
                kept[-1] = c
        else:
            kept.append(c)
    edges = [0] + kept + [len(cols)]
    out = []
    for a, b in zip(edges, edges[1:]):
        if cols[a:b].sum() > 0:
            out.append((a, b))
    return out


def split_components(fg, body_area=18000, drop_area=1200):
    """연결요소로 나누고, 떨어져 나온 무기 조각은 가장 가까운 몸에 붙인다.

    투영으로만 자르면 두 가지가 어긋난다.
      · 컷 번호(①②…)가 배경에 찍혀 있어 캐릭터에 섞인다 → 작은 조각은 버린다
      · 손에서 놓친 창이 옆 컷 영역까지 날아가 엉뚱한 컷에 붙는다
        → 거리로 주인을 찾아준다
    """
    # 옆 컷의 무기끼리 살짝 닿아 두 인물이 한 덩어리가 되는 일이 있다.
    # 침식으로 얇은 다리를 끊고 라벨을 매긴 뒤, 원래 픽셀을 가장 가까운 라벨에 돌려준다.
    # 먼저 원래 연결요소를 구해 '작은 조각'(컷 번호 ①②…)을 걸러낸다.
    # 아래 거리 기반 배정은 남은 전경을 전부 어딘가에 붙이므로,
    # 여기서 안 버리면 번호가 캐릭터에 딸려 들어간다.
    olbl, on = ndimage.label(fg)
    if on:
        osz = ndimage.sum(fg, olbl, range(1, on + 1))
        tiny = np.isin(olbl, [i + 1 for i in range(on) if osz[i] < drop_area])
        fg = fg & ~tiny

    seeds = ndimage.binary_erosion(fg, np.ones((9, 9)))
    slbl, sn = ndimage.label(seeds)
    if sn:
        # 각 전경 픽셀을 가장 가까운 씨앗 라벨로 — 끊긴 덩어리를 원래 크기로 복원
        idx = ndimage.distance_transform_edt(slbl == 0, return_distances=False,
                                             return_indices=True)
        lbl = np.where(fg, slbl[tuple(idx)], 0)
        n = sn
    else:
        lbl, n = ndimage.label(fg)
    sizes = ndimage.sum(fg, lbl, range(1, n + 1))
    cents = ndimage.center_of_mass(fg, lbl, range(1, n + 1))

    bodies = [i for i in range(n) if sizes[i] >= body_area]
    orphans = [i for i in range(n) if drop_area <= sizes[i] < body_area]

    owner = {b: [b] for b in bodies}
    for o in orphans:
        oy, ox = cents[o]
        best = min(bodies, key=lambda b: (cents[b][0] - oy) ** 2 + (cents[b][1] - ox) ** 2)
        owner[best].append(o)

    out = []
    for b in bodies:
        m = np.isin(lbl, [i + 1 for i in owner[b]])
        ys, xs = np.nonzero(m)
        # 정렬은 bbox 가 아니라 **몸통 중심**으로 한다. 팔을 치켜든 컷은 bbox 가
        # 위로 튀어 올라 다른 행으로 오인된다.
        out.append((xs.min(), ys.min(), xs.max() + 1, ys.max() + 1, m, cents[b]))

    ys_all = sorted(o[5][0] for o in out)
    rows, cur = [], [ys_all[0]]
    for y in ys_all[1:]:
        if y - cur[-1] < 150:
            cur.append(y)
        else:
            rows.append(cur)
            cur = [y]
    rows.append(cur)
    centers = [sum(r) / len(r) for r in rows]

    def row_of(o):
        return min(range(len(centers)), key=lambda i: abs(centers[i] - o[5][0]))

    ordered = sorted(out, key=lambda o: (row_of(o), o[5][1]))
    return [o[:5] for o in ordered]


def split_blobs(fg, min_area=4000):
    """행/열 투영으로 격자를 찾아 컷을 나눈다.

    연결요소 + 팽창 방식은 컷 사이가 좁으면 전부 한 덩어리로 붙어버린다.
    시트는 격자로 배치돼 있으니 투영으로 빈 줄을 찾는 편이 훨씬 안정적이다.
    """
    h, w = fg.shape
    out = []
    for y0, y1 in _bands(fg.sum(axis=1), min_run=60, gap_thresh=max(2, w // 400)):
        band = fg[y0:y1]
        cols = band.sum(axis=0)
        # 열 방향은 무기가 옆 컷으로 삐져나와 붙기 쉽다 — 문턱을 높게 잡아
        # '몸통이 있는 자리'만 컷으로 인정한다
        # 컷 사이가 완전히 비어 있지 않다 — 창이 옆 컷까지 뻗어 다리를 놓는다.
        # 그래서 '0인 구간'이 아니라 '골짜기'를 찾아 자른다.
        for x0, x1 in _valley_cuts(cols):
            m = np.zeros_like(fg)
            m[y0:y1, x0:x1] = band[:, x0:x1]
            if m.sum() < min_area:
                continue
            ys, xs = np.nonzero(m)
            out.append((xs.min(), ys.min(), xs.max() + 1, ys.max() + 1, m))
    return out


def body_metrics(piece):
    """몸통(가장 큰 연결요소)의 접지 y 와 중심 x. 떨어져 나간 창은 무시한다."""
    a = np.array(piece.getchannel('A')) > 16
    lbl, n = ndimage.label(a)
    if n == 0:
        return None
    sizes = ndimage.sum(a, lbl, range(1, n + 1))
    body = (lbl == int(np.argmax(sizes)) + 1)
    ys, xs = np.nonzero(body)
    return ys.max(), (xs.min() + xs.max()) / 2, ys.max() - ys.min()


def weapon_tip(canvas_img):
    """그려진 창끝 좌표를 찾는다 — 몸 중심에서 가장 먼 불투명 픽셀.

    이펙트(발광·궤적)를 창에 붙이려면 포즈마다 칼끝이 실제로 어디 있는지
    알아야 한다. 손으로 찍으면 17개를 다 찍어야 하고 포즈를 다시 뽑을 때마다
    또 찍어야 한다 — 그림에서 직접 재는 편이 정확하고 유지보수도 없다.
    """
    a = np.array(canvas_img.getchannel('A')) > 24
    if not a.any():
        return None
    ys, xs = np.nonzero(a)
    # 기준점은 몸통(가장 큰 덩어리)의 무게중심. 창은 거기서 뻗어나간다.
    lbl, n = ndimage.label(a)
    sizes = ndimage.sum(a, lbl, range(1, n + 1))
    body = lbl == int(np.argmax(sizes)) + 1
    by, bx = ndimage.center_of_mass(body)
    d = (xs - bx) ** 2 + (ys - by) ** 2
    i = int(np.argmax(d))
    return int(xs[i]), int(ys[i])


def body_core(piece):
    """무기를 걷어낸 '몸통 크기'. 자세가 바뀌어도 비교적 안 변한다.

    무기는 가늘어서 침식(erosion)하면 사라지고 몸통만 남는다.
    생성 모델이 컷마다 캐릭터를 다른 크기로 그렸는지 판별하는 척도로 쓴다.
    """
    a = np.array(piece.getchannel('A')) > 16
    core = ndimage.binary_erosion(a, np.ones((17, 17)))
    lbl, n = ndimage.label(core)
    if n == 0:
        return None
    sizes = ndimage.sum(core, lbl, range(1, n + 1))
    return float(np.sqrt(sizes.max()))


def normalize_set(pieces, names, out_dir, ref=0, lift=None, fit_body=True):
    """컷들을 **같은 배율**로 맞추고 접지면만 정렬한다.

    한 장의 시트에서 나온 컷들은 이미 같은 축척으로 그려져 있다. 컷마다 따로
    bbox 높이로 정규화하면 팔을 치켜든 컷이 도리어 작아진다 — 지금 게임이
    프레임마다 크기가 튀는 이유가 정확히 이것이다.
    기준 컷 하나로 배율을 정하고, 나머지는 그 배율 그대로 쓴다.
    """
    lift = lift or {}
    m0 = body_metrics(pieces[ref])
    scale = H_TARGET / m0[2]

    # 컷마다 캐릭터를 다른 크기로 그려 오는 경우가 있다(모델이 규격을 못 지킨다).
    # 몸통 크기로 편차를 재서 **부분적으로만** 되돌린다.
    # 전부 되돌리면 웅크린 자세까지 억지로 키워서 오히려 어색해진다.
    cores = [body_core(p) for p in pieces]
    fixes = [1.0] * len(pieces)
    if fit_body and all(cores):
        ref_core = sorted(cores)[len(cores) // 2]           # 중앙값을 기준으로
        spread = (max(cores) - min(cores)) / (sum(cores) / len(cores))
        if spread > 0.10:                                    # 10% 넘게 흔들릴 때만 손댄다
            DAMP = 0.65
            fixes = [min(1.12, max(0.89, 1 + (ref_core / c - 1) * DAMP)) for c in cores]
            print(f'  · 원본 크기 편차 {spread * 100:.0f}% → 컷별 보정 적용'
                  f' ({min(fixes):.3f}~{max(fixes):.3f})')

    out_paths, tips = [], {}
    for piece, name, fix in zip(pieces, names, fixes):
        sc = scale * fix
        w = max(1, round(piece.width * sc))
        h = max(1, round(piece.height * sc))
        r = piece.resize((w, h), Image.LANCZOS)
        m = body_metrics(r)
        canvas = Image.new('RGBA', (CANVAS_W, CANVAS_H), (0, 0, 0, 0))
        # 몸통 바닥을 지면에, 몸통 중심을 기준선에
        dx = round(CX - m[1])
        dy = round(BASELINE - m[0]) - lift.get(name, 0)
        canvas.alpha_composite(r, (dx, dy))
        # 캔버스 밖으로 나간 게 있으면 규격이 잘못된 것 — 조용히 잘리면 안 된다
        if dx < 0 or dy < 0 or dx + w > CANVAS_W or dy + h > CANVAS_H:
            print(f'  ! {name}: 캔버스를 벗어난다 — 잘림 발생 (CANVAS 를 키워야 한다)')
        path = os.path.join(out_dir, f'{name}.png')
        canvas.save(path)
        out_paths.append(path)
        tip = weapon_tip(canvas)
        if tip:
            tips[name] = {'tipX': tip[0], 'tipY': tip[1]}
        print(f'  {name:14s} 배율 {sc:.3f}  몸높이 {round(m[2])}px  접지 {m[0]}→{BASELINE}'
              + (f'  창끝 ({tip[0]},{tip[1]})' if tip else ''))

    meta = {'canvasW': CANVAS_W, 'canvasH': CANVAS_H, 'cx': CX,
            'ground': BASELINE, 'height': H_TARGET, 'poses': tips}
    with open(os.path.join(out_dir, 'poses.json'), 'w', encoding='utf-8') as f:
        json.dump(meta, f, ensure_ascii=False, indent=2)
    print(f'  → {out_dir}/poses.json  (창끝 {len(tips)}개)')
    return out_paths


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('sheet')
    ap.add_argument('--out', default='asset_img/cut')
    ap.add_argument('--prefix', default='pose')
    ap.add_argument('--raw-only', action='store_true', help='정렬 없이 잘라내기만')
    ap.add_argument('--names', help='쉼표로 구분한 컷 이름 (순서대로)')
    ap.add_argument('--lift', default='', help='공중 동작 띄우기. 예: ko_fall=90')
    args = ap.parse_args()

    os.makedirs(args.out, exist_ok=True)
    im = Image.open(args.sheet).convert('RGBA')
    rgb = np.array(im.convert('RGB'))

    fg = chroma_key(rgb)
    if fg is not None:
        rgb = despill(rgb, fg)
        print('  초록 배경 감지 → 크로마키로 분리')
    else:
        fg = remove_background(rgb)
    blobs = split_components(fg)
    print(f'{os.path.basename(args.sheet)} → 컷 {len(blobs)}개')

    pieces, names = [], []
    for i, (x0, y0, x1, y1, m) in enumerate(blobs, 1):
        a = (m * 255).astype(np.uint8)
        piece = Image.fromarray(np.dstack([rgb, a])).convert('RGBA')
        pieces.append(piece.crop((x0, y0, x1, y1)))
        names.append(f'{args.prefix}_{i:02d}')

    if args.names:
        given = [s.strip() for s in args.names.split(',') if s.strip()]
        if len(given) != len(pieces):
            print(f'  ! 이름 {len(given)}개 / 컷 {len(pieces)}개 — 개수가 안 맞아 기본 이름을 쓴다')
        else:
            names = given

    if args.raw_only:
        for piece, name in zip(pieces, names):
            piece.save(os.path.join(args.out, name + '.png'))
            print(f'  {name}  {piece.width}x{piece.height}')
        return

    lift = {}
    for token in filter(None, (t.strip() for t in args.lift.split(','))):
        k, _, v = token.partition('=')
        lift[k.strip()] = int(v)
    normalize_set(pieces, names, args.out, lift=lift)


if __name__ == '__main__':
    main()
