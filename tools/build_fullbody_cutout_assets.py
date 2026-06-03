#!/usr/bin/env python3
# 누끼 처리된 신규 전신(fullbody_game_cutout_v1)을 모바일 WebP로 변환,
# 게임 배포 폴더(assets/generals/fullbody_v6/)에 덮어쓴다.
# 누끼 없는 id는 기존 v6 fullbody 유지.
import os
from PIL import Image

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC  = os.path.join(ROOT, 'assets', 'generals', 'new_characters', 'fullbody_game_cutout_v1')
OUT  = os.path.join(ROOT, 'assets', 'generals', 'fullbody_v6')

# 진행 페이지의 fullbodyCutoutFiles 매핑(특수 버전만 명시 — 나머지는 v1 디폴트)
SPECIAL_VERSION = {'cao_cao': 'v3', 'dong_zhuo': 'v2'}

TARGET_H = 760    # 모바일 디테일 모달용 세로 760px
QUALITY  = 82

def file_for(gid):
    ver = SPECIAL_VERSION.get(gid, 'v1')
    return os.path.join(SRC, f'{gid}_fullbody_game_cutout_{ver}.png')

def convert(gid, sp):
    im = Image.open(sp).convert('RGBA')
    w, h = im.size
    nh = TARGET_H
    nw = round(w * nh / h)
    im = im.resize((nw, nh), Image.LANCZOS)
    op = os.path.join(OUT, f'{gid}.webp')
    im.save(op, 'WEBP', quality=QUALITY, method=6)
    return op

if __name__ == '__main__':
    os.makedirs(OUT, exist_ok=True)
    files = [f for f in os.listdir(SRC) if f.endswith('.png')]
    # 파일명 → id 추출 (예: 'xun_yu_fullbody_game_cutout_v1.png' → 'xun_yu')
    ids = set()
    for f in files:
        idx = f.find('_fullbody_game_cutout_')
        if idx > 0: ids.add(f[:idx])
    done, miss = 0, []
    for gid in sorted(ids):
        sp = file_for(gid)
        if not os.path.exists(sp):
            miss.append(gid); continue
        convert(gid, sp); done += 1
    print(f'fullbody 누끼 변환 {done}개 -> {OUT}')
    if miss:
        print(f'  ⚠️ 누락 {len(miss)}: {miss[:6]}{"..." if len(miss)>6 else ""}')
