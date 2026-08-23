#!/usr/bin/env python3
"""일기토를 본편이 서비스하는 폴더(public/)로 복사한다.

왜 복사인가:
  본편은 app/android/app/src/main/assets/public/ 에서 서비스되고, APK 도 그
  폴더를 그대로 담는다. 일기토는 저장소 루트에서 따로 개발해 왔다(그래야
  본편 45,000줄을 건드리지 않고 결투만 띄워 볼 수 있다). 두 곳을 잇는 방법은
  '배포 시 복사' 뿐이다 — 심볼릭 링크는 APK 패키징에서 깨진다.

무엇을 복사하나:
  · duel_v2.html · duel/sfx.js
  · assets/arcade_duel 의 **webp 와 json 만** (100MB / 1,093개)
    png 원본 54MB 는 발주·검수용이라 게임에 필요 없다.
  초상(assets/generals/halfbody_v6)은 이미 public 에 있어 복사하지 않는다.

  한 판에 실제로 받는 양은 1.3MB 다(고른 두 장수 + 배경). 100MB 는 '언제든
  고를 수 있게 놓아두는' 용량이다.

  python3 tools/sync_duel_to_app.py
  python3 tools/sync_duel_to_app.py --dry-run
"""
import argparse
import filecmp
import os
import shutil

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DEST = os.path.join(ROOT, 'app', 'android', 'app', 'src', 'main', 'assets', 'public')

FILES = ['duel_v2.html', os.path.join('duel', 'sfx.js')]
TREES = [(os.path.join('assets', 'arcade_duel'), ('.webp', '.json'))]


def copy(src, dst, dry):
    if os.path.exists(dst) and filecmp.cmp(src, dst, shallow=False):
        return 0
    if not dry:
        os.makedirs(os.path.dirname(dst), exist_ok=True)
        shutil.copy2(src, dst)
    return 1


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--dry-run', action='store_true')
    args = ap.parse_args()

    if not os.path.isdir(DEST):
        raise SystemExit(f'대상 폴더가 없다: {DEST}')

    n = size = 0
    for rel in FILES:
        s = os.path.join(ROOT, rel)
        if not os.path.exists(s):
            print(f'  ! 없음 {rel}')
            continue
        c = copy(s, os.path.join(DEST, rel), args.dry_run)
        n += c
        size += os.path.getsize(s) if c else 0

    for rel, exts in TREES:
        base = os.path.join(ROOT, rel)
        for cur, _, fs in os.walk(base):
            for f in fs:
                if not f.endswith(exts):
                    continue
                s = os.path.join(cur, f)
                d = os.path.join(DEST, rel, os.path.relpath(s, base))
                c = copy(s, d, args.dry_run)
                n += c
                size += os.path.getsize(s) if c else 0

    tag = '(--dry-run) ' if args.dry_run else ''
    print(f'{tag}복사 {n}개 · {size / 1048576:.1f}MB')
    print(f'대상: {os.path.relpath(DEST, ROOT)}')


if __name__ == '__main__':
    main()
