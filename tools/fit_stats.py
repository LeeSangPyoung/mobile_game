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

  t = (순위-1)/69   (0 = 1위, 1 = 70위)

    무력 = 100 - 38 * t^0.85                  → 1위 100, 70위 62
    체력 =  96 + (1-t)*46 + (체격-1.04)*90    → 순위가 주(主), 체격은 보조
    기력 = 무기별 기본값 * (0.90 + 0.20*(1-t))

  예전 체력 식은 `95 + (체격-0.96)*280 + (무력-70)/30*15` 였다.
  체격 몫이 최대 +50, 순위 몫이 최대 +15 — **체격이 순위를 3배 넘게 눌렀다.**
  그래서 48위 황개(124)가 4위 조운(120)보다 튼튼했다. 순위표를 만들어 놓고
  순위가 뒤집히면 표가 있으나 마나다. 지금은 순위 몫 46, 체격 몫 ±9 다.

  공속은 여전히 **무기 길이**로만 가른다. 이건 전투력이 아니라 무기의
  개성이다 — 창을 쓰면 느리고 검을 쓰면 빠른 것이지, 강해서 빠른 게 아니다.
  대신 기력에는 순위를 곱한다. 상위 장수가 더 많이 휘두른다.

    장병기  공속 1.12 (느림) · 기력 기본 92
    중간    공속 1.00        · 기력 기본 100
    단병기  공속 0.88 (빠름) · 기력 기본 110

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
        t = (rk - 1) / 69
        war = round(100 - 38 * t ** 0.85)
        size = g.get('size', 1)
        # 순위가 주, 체격은 보조. 순위 몫 46 · 체격 몫 ±9
        hp = round(96 + (1 - t) * 46 + (size - 1.04) * 90)
        w = weap[g['id']]
        cls, spd, base = ('장병기', 1.12, 92) if w >= q2 else                          ('단병기', 0.88, 110) if w < q1 else ('중간', 1.0, 100)
        stam = round(base * (0.90 + 0.20 * (1 - t)))
        g['war'], g['hp'], g['spd'], g['stam'] = war, hp, spd, stam
        print(f"{g['name']:<7}{rk:5}{war:5}{hp:5}{spd:6}{stam:5}  {cls}")

    if not args.dry_run:
        json.dump(roster, open(pj, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
    else:
        print('\n(--dry-run: 아무것도 쓰지 않았다)')


if __name__ == '__main__':
    main()
