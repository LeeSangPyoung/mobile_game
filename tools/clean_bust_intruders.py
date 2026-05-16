#!/usr/bin/env python3
"""
Re-crop general bust PNGs that contain a partial neighbor character.

Two-pass strategy:
  Pass A — original alpha threshold → connected components → kill intruders
           (whose centroid is far from the main subject's centroid).
  Pass B — if pass A keeps a single component but bbox is unusually wide
           (i.e. main + intruder are touching), apply morphological erosion
           on the alpha mask to break thin pixel bridges, redo components,
           then dilate back.

Originals are backed up to assets/generals/busts/_orig/.
"""

import os, sys, shutil
from collections import deque
from PIL import Image, ImageFilter

SRC_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'assets', 'generals', 'busts'))
BACKUP_DIR = os.path.join(SRC_DIR, '_orig')

ALPHA_THRESH = 32
MIN_FRAG = 150                # 픽셀 단위. 이보다 작으면 노이즈로 간주
INTRUDER_CENTROID_DIST = 0.22 # main centroid에서 x 비율로 이만큼 벗어나면 침입자
EROSION_PASSES = (3, 5, 8, 12, 16)   # 점점 강하게 침식해가며 분리 시도
SPLIT_AREA_FRAC = 0.20          # 침식 후 두 번째 컴포넌트가 첫 번째의 이 비율 이상이면 분리 성공으로 간주

def find_components(mask, w, h):
    visited = bytearray(w * h)
    comps = []
    nb = [(-1,-1),(0,-1),(1,-1),(-1,0),(1,0),(-1,1),(0,1),(1,1)]
    for sy in range(h):
        rb = sy * w
        for sx in range(w):
            i = rb + sx
            if visited[i] or not mask[i]:
                continue
            q = deque(); q.append((sx, sy)); visited[i] = 1
            pixels = []; sumx = sumy = 0
            x0=x1=sx; y0=y1=sy
            while q:
                x, y = q.popleft()
                pixels.append((x, y))
                sumx += x; sumy += y
                if x<x0: x0=x
                if x>x1: x1=x
                if y<y0: y0=y
                if y>y1: y1=y
                for dx, dy in nb:
                    nx, ny = x+dx, y+dy
                    if 0<=nx<w and 0<=ny<h:
                        j = ny*w+nx
                        if not visited[j] and mask[j]:
                            visited[j] = 1; q.append((nx, ny))
            a = len(pixels)
            if a < MIN_FRAG: continue
            comps.append({'pixels': pixels, 'area': a,
                          'cx': sumx/a, 'cy': sumy/a,
                          'bbox': (x0, y0, x1+1, y1+1)})
    return comps

def score(c, w, h):
    cxd = abs(c['cx'] - w/2) / (w/2)
    cyd = abs(c['cy'] - h/2) / (h/2)
    return c['area'] * max(0.05, 1.0 - 0.55*cxd - 0.20*cyd)

def alpha_mask(img, thresh):
    a = img.split()[-1].tobytes()
    return bytes(1 if b >= thresh else 0 for b in a)

def erode_mask(mask, w, h, iters):
    """4-connectivity erosion via Pillow (faster than Python loops)."""
    bw = Image.frombytes('L', (w, h), bytes(255 if v else 0 for v in mask))
    for _ in range(iters):
        bw = bw.filter(ImageFilter.MinFilter(3))
    out = bw.tobytes()
    return bytes(1 if b > 127 else 0 for b in out)

def keep_only(img, keep_pixels):
    w, h = img.size
    src = bytearray(img.tobytes())
    keep = bytearray(w*h)
    for x, y in keep_pixels:
        keep[y*w + x] = 1
    for i in range(w*h):
        if not keep[i]:
            src[i*4 + 3] = 0
    return Image.frombytes('RGBA', (w, h), bytes(src))

def recenter(img):
    """원본과 동일한 캔버스(width,height)에 메인을 수평 중앙·수직 하단 정렬."""
    w, h = img.size
    bb = img.getbbox()
    if not bb: return img
    crop = img.crop(bb)
    cw, ch = crop.size
    canvas = Image.new('RGBA', (w, h), (0,0,0,0))
    px = (w - cw) // 2
    py = h - ch
    if py < 0: py = 0
    canvas.paste(crop, (px, py))
    return canvas

def select_main(comps, w, h):
    if not comps: return None, []
    comps_sorted = sorted(comps, key=lambda c: score(c, w, h), reverse=True)
    main = comps_sorted[0]
    others = []
    for c in comps_sorted[1:]:
        # 중심 거리 기반 침입자 판정
        dx = abs(c['cx'] - main['cx']) / w
        dy = abs(c['cy'] - main['cy']) / h
        far = dx > INTRUDER_CENTROID_DIST or dy > 0.35
        if far:
            others.append(c)
        elif c['area'] > main['area'] * 0.20:
            # 메인에 가까운데 큼 → 일단 침입자로 간주(보수적으로 자르기보단 살리는 게 안전하지만,
            # 보통 분리된 큰 두 덩어리 = 두 캐릭터)
            others.append(c)
    return main, others

def try_erosion_split(img, mask, w, h):
    """침식으로 분리 시도. 성공하면 (main_pixels) 반환, 실패하면 None."""
    for it in EROSION_PASSES:
        eroded = erode_mask(mask, w, h, it)
        ec = find_components(eroded, w, h)
        if len(ec) < 2:
            continue
        ec_sorted = sorted(ec, key=lambda c: -c['area'])
        # 1·2위가 둘 다 의미있는 크기일 때만 "두 인물 분리됨"으로 간주
        if ec_sorted[1]['area'] < ec_sorted[0]['area'] * SPLIT_AREA_FRAC:
            continue
        em, eo = select_main(ec, w, h)
        if not eo:
            continue
        # 침식된 메인을 시드로 원본 마스크에서 재성장 (4-connectivity)
        seed = bytearray(w*h)
        for x, y in em['pixels']:
            seed[y*w + x] = 1
        grown = grow_within(seed, mask, w, h)
        kept = [(i % w, i // w) for i, v in enumerate(grown) if v]
        return kept, it
    return None

GAP_MIN = 6                      # 한 행 안에서 "구멍"으로 인정할 픽셀 폭
ROWRUN_CUT_THRESH = 100          # 한 버킷에 이만큼 이상 행이 모이면 침입자 인정
ROWRUN_LEFT_FRAC = 0.30          # bbox 가로의 이 비율 안쪽에 갭이 있으면 좌측 침입자
ROWRUN_RIGHT_FRAC = 0.70         # 우측 침입자 판정 (bbox 가로 비율)
ROWRUN_BUCKET = 20               # 갭 중점 히스토그램 버킷 폭
MIN_BODY_RUN = 55                # 갭 양쪽이 이 픽셀 이상이어야 "두 인물"로 간주 (얇은 무기 제외)

# 자동 검출이 무기/장식과 구분하지 못하는 touching 침입자에 대한 수동 절단점
# 값은 원본 좌표계에서의 컷 x — x < cut_x 영역의 알파를 0으로 만듦
MANUAL_LEFT_CUT = {
    'cao_cao.png': 200,
    'lu_bu.png': 210,
    'zhang_fei.png': 180,
}
MANUAL_RIGHT_CUT = {}

def detect_rowrun_cut(img, bbox, w, h):
    """행별 알파 런 분석으로 좌/우 침입자 경계를 찾는다.

    반환: ('left', cut_x) | ('right', cut_x) | None
      cut_x 의미:
        left  → x < cut_x 영역을 알파 0으로 만든다 (좌측 침입자 제거)
        right → x > cut_x 영역을 알파 0으로 만든다 (우측 침입자 제거)
    """
    a = img.split()[-1].load()
    bx0, by0, bx1, by1 = bbox
    bw = bx1 - bx0
    rows_with_gap = []  # (gap_left_end, gap_right_start, mid)
    for y in range(max(60, by0), min(h - 60, by1)):
        runs = []
        in_run = False
        rs = 0
        for x in range(w):
            on = a[x, y] >= ALPHA_THRESH
            if on and not in_run:
                rs = x; in_run = True
            elif not on and in_run:
                runs.append((rs, x - 1)); in_run = False
        if in_run:
            runs.append((rs, w - 1))
        if len(runs) < 2:
            continue
        # 가장 큰 갭 선택 (단, 양쪽 모두 "몸통" 수준의 너비여야 함 — 무기 제외)
        best = None; best_w = 0
        for i in range(len(runs) - 1):
            gw = runs[i + 1][0] - runs[i][1]
            left_run_w = runs[i][1] - runs[i][0] + 1
            right_run_w = runs[i + 1][1] - runs[i + 1][0] + 1
            if gw < GAP_MIN: continue
            if left_run_w < MIN_BODY_RUN or right_run_w < MIN_BODY_RUN:
                continue  # 얇은 쪽은 무기/장식
            if gw > best_w:
                best_w = gw
                best = (runs[i][1], runs[i + 1][0], (runs[i][1] + runs[i + 1][0]) // 2)
        if best:
            rows_with_gap.append(best)
    if not rows_with_gap:
        return None
    # 미드포인트 히스토그램
    buckets = {}
    for _, _, mid in rows_with_gap:
        k = (mid // ROWRUN_BUCKET) * ROWRUN_BUCKET
        buckets[k] = buckets.get(k, 0) + 1
    if not buckets:
        return None
    # 최빈 버킷 + 인접 버킷 합산
    best_k = max(buckets, key=buckets.get)
    count = buckets[best_k] + buckets.get(best_k - ROWRUN_BUCKET, 0) + buckets.get(best_k + ROWRUN_BUCKET, 0)
    if count < ROWRUN_CUT_THRESH:
        return None
    mid_center = best_k + ROWRUN_BUCKET / 2
    # 좌·우 침입자 판정 (bbox 기준)
    rel = (mid_center - bx0) / bw if bw > 0 else 0.5
    if rel <= ROWRUN_LEFT_FRAC:
        # 갭의 우측 시작점들의 평균을 컷으로 사용 (메인 시작 경계)
        relevant = [r for r in rows_with_gap if abs(r[2] - mid_center) <= ROWRUN_BUCKET]
        cut = int(round(sum(r[1] for r in relevant) / len(relevant)))
        return ('left', cut)
    if rel >= ROWRUN_RIGHT_FRAC:
        relevant = [r for r in rows_with_gap if abs(r[2] - mid_center) <= ROWRUN_BUCKET]
        cut = int(round(sum(r[0] for r in relevant) / len(relevant)))
        return ('right', cut)
    return None

def apply_xcut(img, side, cut_x):
    w, h = img.size
    src = bytearray(img.tobytes())
    if side == 'left':
        for y in range(h):
            base = y * w * 4
            for x in range(cut_x):
                src[base + x * 4 + 3] = 0
    elif side == 'right':
        for y in range(h):
            base = y * w * 4
            for x in range(cut_x + 1, w):
                src[base + x * 4 + 3] = 0
    return Image.frombytes('RGBA', (w, h), bytes(src))

def process(src, dst, fname):
    img = Image.open(src).convert('RGBA')
    w, h = img.size
    mask = alpha_mask(img, ALPHA_THRESH)
    comps = find_components(mask, w, h)
    if not comps:
        return ('empty', 0)

    main, others = select_main(comps, w, h)
    cleaned = img
    actions = []

    # 1) 명확한 별개 컴포넌트(침입자) 제거
    if others:
        cleaned = keep_only(cleaned, main['pixels'])
        actions.append(f'multi:{len(others)}')

    # 2) 수동 컷 (자동 검출이 어려운 touching 침입자)
    if fname in MANUAL_LEFT_CUT:
        cleaned = apply_xcut(cleaned, 'left', MANUAL_LEFT_CUT[fname])
        actions.append(f'manual-left@{MANUAL_LEFT_CUT[fname]}')
    if fname in MANUAL_RIGHT_CUT:
        cleaned = apply_xcut(cleaned, 'right', MANUAL_RIGHT_CUT[fname])
        actions.append(f'manual-right@{MANUAL_RIGHT_CUT[fname]}')

    # 3) 행 런 분석으로 좌/우 침입자(touching) 절단 (수동 컷 미설정 파일만)
    if fname not in MANUAL_LEFT_CUT and fname not in MANUAL_RIGHT_CUT:
        bbox = (cleaned.getbbox() or main['bbox'])
        rcut = detect_rowrun_cut(cleaned, bbox, w, h)
        if rcut is not None:
            side, cut_x = rcut
            cleaned = apply_xcut(cleaned, side, cut_x)
            actions.append(f'cut-{side}@{cut_x}')

    if not actions:
        shutil.copy2(src, dst)
        return ('clean', 0)

    recenter(cleaned).save(dst, 'PNG', optimize=True)
    return ('cleaned', '+'.join(actions))

def grow_within(seed, mask, w, h):
    """seed에서 시작해 mask=1인 픽셀로만 4-connectivity BFS 확장."""
    out = bytearray(seed)
    q = deque()
    for i, v in enumerate(out):
        if v:
            q.append((i % w, i // w))
    nb = [(-1,0),(1,0),(0,-1),(0,1)]
    while q:
        x, y = q.popleft()
        for dx, dy in nb:
            nx, ny = x+dx, y+dy
            if 0<=nx<w and 0<=ny<h:
                j = ny*w + nx
                if not out[j] and mask[j]:
                    out[j] = 1
                    q.append((nx, ny))
    return out

def main():
    if not os.path.isdir(SRC_DIR):
        print('busts dir not found:', SRC_DIR); sys.exit(1)
    os.makedirs(BACKUP_DIR, exist_ok=True)
    files = sorted(f for f in os.listdir(SRC_DIR) if f.endswith('.png') and not f.startswith('_'))
    print(f'Processing {len(files)} bust files...')
    results = []
    for fn in files:
        live = os.path.join(SRC_DIR, fn)
        bak = os.path.join(BACKUP_DIR, fn)
        if not os.path.exists(bak):
            shutil.copy2(live, bak)
        status, info = process(bak, live, fn)
        results.append((fn, status, info))
        print(f'  {fn:24s}  {status:18s}  {info}')
    print()
    by = {}
    for _, s, _ in results:
        by[s] = by.get(s, 0) + 1
    print('Summary:', by)

if __name__ == '__main__':
    main()
