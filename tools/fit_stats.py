#!/usr/bin/env python3
"""장수별 능력치(무력·체력·공속·기력)를 generals.json 에 적는다.

왜 필요한가:
  generals.json 에 war·hp 필드가 없어서, 누구를 골라도 플레이어는 조운의
  96/120, 보스는 화웅의 88/150 을 썼다(duel_v2.html 의 SIDE_INFO 기본값).
  화면에 뜨는 "공손찬 무력 88" 은 공손찬 값이 아니라 화웅 값이었다.
  즉 49명이 이름과 그림만 다르고 성능은 진영으로 결정됐다.

무엇을 기준으로 하는가:
  rank70.json 의 전투력 순위. 이 표가 유일한 기준이고, 순위에 없는 장수는
  70위 취급한다.

    무력 = 100 - 30 * ((순위-1)/69)^0.85      → 1위 100, 70위 70
    체력 =  95 + (체격-0.96)*280 + (무력-70)/30*15

  공속·기력은 **무기 길이**로 가른다. 타격 컷 창끝의 최대 전진량을 재서
  삼분위로 나누면 장병기 16 / 중간 17 / 단병기 16 으로 갈린다 — 창·언월도
  쪽과 검·쌍검 쪽이 그대로 나뉜다. 리치가 긴 만큼 느리고 기력을 더 쓴다.

    장병기  공속 1.12 (느림) · 기력 92
    중간    공속 1.00        · 기력 100
    단병기  공속 0.88 (빠름) · 기력 110

  체력 식은 기존에 손으로 잡아 둔 두 값에 맞춘 것이다 —
  조운(체격 1.00·무력 98)이 120, 화웅(1.14·90)이 155 로 나온다(원래 150).

  python3 tools/fit_stats.py
  python3 tools/fit_stats.py --dry-run
"""
import argparse
import json
import os
import statistics

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
STATES = os.path.join(ROOT, 'assets', 'arcade_duel')


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--dry-run', action='store_true')
    args = ap.parse_args()

    rank = {r['id']: r['rank']
            for r in json.load(open(os.path.join(STATES, 'rank70.json'), encoding='utf-8'))}
    pj = os.path.join(STATES, 'generals.json')
    roster = json.load(open(pj, encoding='utf-8'))

    # 무기 길이 — 타격 3컷 창끝의 최대 전진량(화면 px)
    weap = {}
    for g in roster:
        m = json.load(open(os.path.join(STATES, g['id'] + '_states', 'poses.json'),
                           encoding='utf-8'))
        s = 200 * g.get('size', 1) / (m.get('bodyH') or 620)
        p = m.get('poses', {})
        weap[g['id']] = max((p[f'{k}_impact']['tipX'] - 640) * s
                            for k in ('slash', 'thrust', 'heavy') if f'{k}_impact' in p)
    q1, q2 = statistics.quantiles(weap.values(), n=3)

    print(f"{'장수':<7}{'순위':>5}{'무력':>5}{'체력':>5}{'공속':>6}{'기력':>5}  무기")
    for g in roster:
        rk = rank.get(g['id'], 70)
        war = round(100 - 30 * ((rk - 1) / 69) ** 0.85)
        size = g.get('size', 1)
        hp = round(95 + (size - 0.96) * 280 + (war - 70) / 30 * 15)
        w = weap[g['id']]
        cls, spd, stam = ('장병기', 1.12, 92) if w >= q2 else                          ('단병기', 0.88, 110) if w < q1 else ('중간', 1.0, 100)
        g['war'], g['hp'], g['spd'], g['stam'] = war, hp, spd, stam
        print(f"{g['name']:<7}{rk:5}{war:5}{hp:5}{spd:6}{stam:5}  {cls}")

    if not args.dry_run:
        json.dump(roster, open(pj, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
    else:
        print('\n(--dry-run: 아무것도 쓰지 않았다)')


if __name__ == '__main__':
    main()
