#!/usr/bin/env python3
"""Fast, conservative sprite audit for the duel roster.

It deliberately measures only states that should keep the same body scale.
Attack windups are excluded from size flags because an overhead weapon is a
valid silhouette change.  Output is a candidate list for visual review, not
an automatic asset replacement decision.
"""
import argparse
import json
from pathlib import Path

import numpy as np
from PIL import Image
from scipy import ndimage

ROOT = Path(__file__).resolve().parents[1]
ASSETS = ROOT / 'assets' / 'arcade_duel'
STABLE = ('idle', 'walk1', 'walk2', 'walk3', 'walk4', 'guard_ready',
          'hurt_light', 'hurt_heavy', 'stunned')
CHECK_FRAGMENTS = STABLE + ('slash_impact', 'thrust_impact', 'heavy_impact')
REQUIRED = STABLE + ('ko_fall', 'ko_down', 'slash_windup', 'slash_impact',
                     'slash_recovery', 'thrust_windup', 'thrust_impact',
                     'thrust_recovery', 'heavy_windup', 'heavy_impact',
                     'heavy_recovery')


def mask(path):
    im = Image.open(path).convert('RGBA')
    im.thumbnail((320, 256), Image.Resampling.NEAREST)
    return np.asarray(im.getchannel('A')) > 16


def body_metrics(alpha):
    labels, count = ndimage.label(alpha)
    if not count:
        return None
    sizes = ndimage.sum(alpha, labels, range(1, count + 1))
    body_id = int(np.argmax(sizes)) + 1
    body = labels == body_id
    ys, xs = np.nonzero(body)
    return labels, body_id, sizes, (int(ys.min()), int(ys.max()), int(xs.min()), int(xs.max()))


def audit(gid):
    folder = ASSETS / f'{gid}_states'
    missing, blank, shapes, fragments = [], [], {}, []
    cache = {}
    for state in REQUIRED:
        path = folder / f'{state}.webp'
        if not path.exists():
            missing.append(state)
            continue
        alpha = cache.setdefault(state, mask(path))
        data = body_metrics(alpha)
        if not data:
            blank.append(state)
            continue
        if state in STABLE:
            _, _, _, box = data
            shapes[state] = (box[1] - box[0] + 1, box[1])
        if state in CHECK_FRAGMENTS:
            labels, body_id, sizes, box = data
            body = labels == body_id
            by, bx = np.nonzero(body)
            for component, area in enumerate(sizes, 1):
                if component == body_id or area < 190:  # about 3,000 source pixels
                    continue
                oy, ox = np.nonzero(labels == component)
                # Large disconnected art more than roughly 50 source pixels away.
                gap = min(((by - y) ** 2 + (bx - x) ** 2).min()
                          for y, x in zip(oy[::8], ox[::8])) ** .5
                if gap > 13:
                    fragments.append(state)
                    break
    heights = [value[0] for value in shapes.values()]
    bottoms = [value[1] for value in shapes.values()]
    scale_spread = ((max(heights) - min(heights)) / np.median(heights) * 100) if heights else 0
    foot_spread = (max(bottoms) - min(bottoms)) * 4 if bottoms else 0
    return missing, blank, scale_spread, foot_spread, sorted(set(fragments))


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('ids', nargs='*')
    args = parser.parse_args()
    roster = json.loads((ASSETS / 'generals.json').read_text(encoding='utf-8'))
    ids = args.ids or [g['id'] for g in roster]
    print('id scale_spread foot_spread fragment_states missing_or_blank')
    for gid in ids:
        missing, blank, scale, foot, fragments = audit(gid)
        flags = bool(missing or blank or fragments or scale > 14 or foot > 32)
        if flags:
            print(f'{gid} {scale:.1f}% {foot:.0f}px '
                  f'{",".join(fragments) or "-"} '
                  f'{",".join(missing + blank) or "-"}')


if __name__ == '__main__':
    main()
