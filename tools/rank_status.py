#!/usr/bin/env python3
"""상위 70명 순위표를 읽어 완료/미완료 현황을 찍는다.

전투력 순위는 저장소 어디에도 없어서(roster_200.js 는 id·이름만, index.html 은
지력만 있다) 대화 중 매번 다르게 인용되며 혼선이 있었다. rank70.json 을
유일한 기준으로 삼는다.

  python3 tools/rank_status.py          # 요약 + 다음 발주 대상
  python3 tools/rank_status.py --all    # 70명 전체
"""
import argparse
import glob
import json
import os

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RANK = os.path.join(ROOT, 'assets', 'arcade_duel', 'rank70.json')
STATES = os.path.join(ROOT, 'assets', 'arcade_duel')


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--all', action='store_true')
    args = ap.parse_args()

    rows = json.load(open(RANK, encoding='utf-8'))
    done = {os.path.basename(p)[:-7] for p in glob.glob(os.path.join(STATES, '*_states'))}
    for r in rows:
        r['done'] = r['id'] in done

    todo = [r for r in rows if not r['done']]
    ready = [r for r in todo if r['art']]
    noart = [r for r in todo if not r['art']]

    if args.all:
        for r in rows:
            mark = '완료' if r['done'] else ('대기' if r['art'] else '도감없음')
            print(f"{r['rank']:>3}. {r['name']:<5} {mark}")
        print()

    print(f"완료 {len(rows) - len(todo)}/70 · 남음 {len(todo)}명"
          f"(도감 없어 후순위 {len(noart)}명 포함)")
    extra = sorted(done - {r['id'] for r in rows})
    if extra:
        print('순위 밖 완료:', extra)
    if ready:
        nxt = ready[0]
        print(f"다음 발주: {nxt['rank']}위 {nxt['name']} ({nxt['id']})")
        print('이어서: ' + ' · '.join(f"{r['rank']}위 {r['name']}" for r in ready[1:6]))
    if noart:
        print('도감 없음: ' + ' · '.join(f"{r['rank']}위 {r['name']}" for r in noart))


if __name__ == '__main__':
    main()
