#!/usr/bin/env python3
"""Report visual weapon-tip versus collision-distance error for every general.

Collision uses centre-to-centre distance.  A visible hit should therefore occur
when the active-frame tip reaches the opponent's near body edge (74px at size
1.0), not when it reaches that centre.  This checks the final, most-forward
active frame, including the same pose rotation/translation used by duel_v2.
It reports candidates only; assets are never edited.
"""
import json
import math
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ASSETS = ROOT / 'assets' / 'arcade_duel'
BASE = {'slash': 223, 'thrust': 278, 'heavy': 194}
SWING = {'slash': (10, 22), 'thrust': (4, 34), 'heavy': (14, 26)}
CX, GROUND, TARGET_H, BODY_R = 640, 880, 200, 74


def tip_reach(meta, size, move):
    tip = meta['poses'][f'{move}_impact']
    scale = TARGET_H * size / meta.get('bodyH', 620)
    rot, dx = SWING[move]
    # attackMotion active at t=1: rot=.62*rot, dx=1.0*dx
    rad = math.radians(rot * .62)
    x = (tip['tipX'] - CX + dx) * scale
    y = (tip['tipY'] - GROUND) * scale
    return math.cos(rad) * x - math.sin(rad) * y


def main():
    roster = json.loads((ASSETS / 'generals.json').read_text(encoding='utf-8'))
    print('id move visual_contact collision delta')
    all_rows = []
    for general in roster:
        gid, size = general['id'], general.get('size', 1.0)
        meta = json.loads((ASSETS / f'{gid}_states' / 'poses.json').read_text(encoding='utf-8'))
        for move, collision in BASE.items():
            if f'{move}_impact' not in meta.get('poses', {}):
                continue
            # Equal-size opponent: tip projection + opponent near-edge radius.
            visual = tip_reach(meta, size, move) + BODY_R
            delta = visual - collision
            all_rows.append((gid, move, visual, collision, delta))
    for gid, move, visual, collision, delta in sorted(all_rows, key=lambda r: abs(r[4]), reverse=True):
        print(f'{gid:14} {move:6} {visual:7.1f} {collision:9.1f} {delta:+6.1f}')
    worst = max(abs(row[4]) for row in all_rows)
    print(f'rows={len(all_rows)} worst_abs_delta={worst:.1f}')


if __name__ == '__main__':
    main()
