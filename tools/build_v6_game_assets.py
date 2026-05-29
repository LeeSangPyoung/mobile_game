#!/usr/bin/env python3
# 신규 v6 전신/반신 200세트를 모바일용 WebP로 변환해 게임 배포 폴더로 정리.
# 원본(new_characters/*)은 보존. 출력: assets/generals/{halfbody_v6,fullbody_v6}/{id}.webp
import os, re, sys
from PIL import Image

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
GEN = os.path.join(ROOT, 'assets', 'generals')
HALF_SRC = os.path.join(GEN, 'new_characters', 'upper_body_200_redraw_v6_above_navel')
FULL_SRC = os.path.join(GEN, 'new_characters', 'front_gaze_200_v10_scale_audit')
HALF_OUT = os.path.join(GEN, 'halfbody_v6')
FULL_OUT = os.path.join(GEN, 'fullbody_v6')

def roster_ids():
    js = open(os.path.join(GEN, 'roster_200.js'), encoding='utf-8').read()
    # ["id", "한글"] 형태에서 첫 토큰(id)만 추출
    return re.findall(r"""\[\s*['"]([a-z0-9_]+)['"]\s*,""", js)

def convert(src, out, target_dim, axis, quality):
    os.makedirs(out, exist_ok=True)
    ids = roster_ids()
    done = 0; miss = []
    for gid in ids:
        suffix = '_halfbody_redraw_v6.png' if axis == 'w' else '_front_gaze_v1.png'
        sp = os.path.join(src, gid + suffix)
        if not os.path.exists(sp):
            miss.append(gid); continue
        im = Image.open(sp).convert('RGBA')
        w, h = im.size
        if axis == 'w':
            nw = target_dim; nh = round(h * target_dim / w)
        else:
            nh = target_dim; nw = round(w * target_dim / h)
        im = im.resize((nw, nh), Image.LANCZOS)
        im.save(os.path.join(out, gid + '.webp'), 'WEBP', quality=quality, method=6)
        done += 1
    return done, miss

if __name__ == '__main__':
    dh, mh = convert(HALF_SRC, HALF_OUT, 600, 'w', 80)
    df, mf = convert(FULL_SRC, FULL_OUT, 760, 'h', 82)
    print(f'반신 변환 {dh}개 -> {HALF_OUT}  (누락 {len(mh)}: {mh[:5]})')
    print(f'전신 변환 {df}개 -> {FULL_OUT}  (누락 {len(mf)}: {mf[:5]})')
