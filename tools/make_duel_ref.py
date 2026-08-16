#!/usr/bin/env python3
"""장수 전신 아트 → 일기토 발주용 레퍼런스 이미지 + 프롬프트.

일기토에 장수를 추가하려면 생성 모델에 '이 캐릭터로 이 포즈를 그려라'고 시켜야 하고,
그러려면 **캐릭터를 특정하는 레퍼런스 이미지**가 필요하다.
다행히 assets/generals/fullbody_v6_aligned/ 에 200명 전신이 이미 규격화돼 있다
(507x760, 투명 배경, 정면 직립). 그걸 발주 규격에 맞춰 배치만 하면 된다.

  python3 tools/make_duel_ref.py lu_bu guan_yu
  python3 tools/make_duel_ref.py --top 70          # 전투력 상위 70명 일괄

출력: asset_img/refs/<id>.png  (초록 배경 위 캐릭터 — 발주 결과와 같은 조건)
     asset_img/refs/<id>_prompt.md
"""
import argparse
import os
import re

from PIL import Image

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC_DIR = os.path.join(ROOT, 'assets', 'generals', 'fullbody_v6_aligned')
OUT_DIR = os.path.join(ROOT, 'asset_img', 'refs')

# 발주 규격과 같은 캔버스. 결과물이 이 배치로 돌아와야 파이프라인이 그대로 먹는다.
CANVAS = 1024
BODY_H = 760          # 캐릭터 키
BASELINE = 900        # 발끝
GREEN = (0, 255, 0, 255)


def load_roster():
    """MANUAL_GENERAL_DEFS 에서 id·이름·버프합(=전투력 순위)을 읽는다."""
    p = os.path.join(ROOT, 'prototype.html')
    s = open(p, encoding='utf-8').read()
    i = s.index('const MANUAL_GENERAL_DEFS = [')
    block = s[i:s.index('\n];', i)]
    pat = re.compile(r"\{\s*id:\s*'([a-z_]+)',\s*name:\s*'([^']+)',\s*buffs:\s*\{([^}]*)\}")
    rows = []
    for m in pat.finditer(block):
        score = sum(float(v) for v in re.findall(r':\s*([0-9.]+)', m.group(3)))
        rows.append({'id': m.group(1), 'name': m.group(2), 'score': score})
    rows.sort(key=lambda r: -r['score'])
    return rows


def make_ref(gid):
    src = os.path.join(SRC_DIR, gid + '.webp')
    if not os.path.exists(src):
        return None
    im = Image.open(src).convert('RGBA')
    bb = im.getbbox()
    if not bb:
        return None
    ch = im.crop(bb)
    k = BODY_H / ch.height
    ch = ch.resize((max(1, round(ch.width * k)), BODY_H), Image.LANCZOS)

    out = Image.new('RGBA', (CANVAS, CANVAS), GREEN)
    out.alpha_composite(ch, (CANVAS // 2 - ch.width // 2, BASELINE - BODY_H))
    os.makedirs(OUT_DIR, exist_ok=True)
    path = os.path.join(OUT_DIR, gid + '.png')
    out.convert('RGB').save(path)
    return path


PROMPT = '''# {name} ({gid}) — 일기토 발주

첨부: `asset_img/refs/{gid}.png`

## 1단계 — 고정 블록 (대화 처음 한 번)

```
You are helping me produce game sprite art for a Three Kingdoms mobile game.

The attached image is my CHARACTER REFERENCE. Study it carefully: this exact
character — same face, same helmet, same armor pattern and colors, same cape,
same weapon — is the one you must draw in every pose I ask for.
Chibi proportions, ornate detailed armor, painterly game-art style.

I will ask you for poses ONE AT A TIME. For every single one of them:

1. ONE character in ONE pose. Never a grid, never a sheet, never variations.
2. Background: solid pure green (#00FF00). Completely flat. No gradient,
   no texture, no vignette, no ground, no shadow.
3. Square image. Character centered horizontally, standing on the lower part
   of the frame, FULL BODY occupying about 80% of the frame height.
   Use the SAME framing and the SAME character size in every pose.
4. Nothing cropped. Weapon tip, weapon butt and cape fully inside the frame
   with clear green margin around them.
5. Character only. No slash trails, no motion blur, no impact sparks, no dust,
   no text, no labels, no borders, no numbers.
6. Facing right.
7. In the IDLE pose the weapon must NOT touch the ground — keep the blade
   clearly above the floor line. (Other poses may touch the ground.)

Confirm you understand, then wait for my first pose request.
```

## 2단계 — 포즈 20컷 (하나씩)

| # | 파일명 | 지시문 |
|---|---|---|
| 1 | `idle` | Standing ready in a side-on combat stance, weight balanced, weapon held across the body. Calm and alert. The weapon must NOT touch the ground. |
| 2 | `walk1` | Mid-stride: front foot planting on the ground, rear foot lifted behind. Body leaning slightly forward. |
| 3 | `walk2` | Mid-stride: both legs passing each other, body at its highest point of the step. |
| 4 | `walk3` | Mid-stride: rear foot planting, front foot lifted forward. The mirror of walk1. |
| 5 | `slash_windup` | Weapon pulled back over the rear shoulder, torso coiled away, weight on the back leg. Wound up, not released. |
| 6 | `slash_impact` | Weapon swept forward through a HORIZONTAL arc at full extension, torso rotated into the swing, front foot planted hard. |
| 7 | `slash_recovery` | Just after the swing: weapon low and past the body, torso over-rotated, off balance, guard open. |
| 8 | `thrust_windup` | Weapon drawn straight back beside the hip, both hands gripping, stance compressed and low, aiming forward. |
| 9 | `thrust_impact` | A deep lunge, weapon driven straight forward at maximum reach, back leg fully extended behind, body a straight line. |
| 10 | `thrust_recovery` | Pulling the weapon back, front leg still forward, weight settling, still extended and vulnerable. |
| 11 | `heavy_windup` | Weapon raised HIGH OVERHEAD with both hands, body stretched upward and leaning back. The most telegraphed wind-up. |
| 12 | `heavy_impact` | Weapon smashed DOWN through a vertical arc toward the ground, body dropped into a deep crouch, full force committed. |
| 13 | `heavy_recovery` | Weapon resting near the ground, body bent forward and heavy, slow to recover, wide open. |
| 14 | `guard_ready` | Crouched low, side-on, weapon shaft held across the chest as a barrier, head tucked. Braced. |
| 15 | `guard_just` | The instant of a perfect parry: weapon snapped outward to deflect, arms extended, torso rotating into the block, head up, defiant. |
| 16 | `hurt_light` | Taking a light hit: upper body recoils BACKWARD, head snapped back, one arm flying up, both feet still planted. |
| 17 | `hurt_heavy` | Taking a heavy hit: whole body thrown BACKWARD and bent at the waist, head far back, arms flung out, front foot lifted. Maximum recoil. |
| 18 | `stunned` | Stunned and defenseless: slumped FORWARD, knees buckled, head hanging, dazed, arms limp, weapon dragging down. |
| 19 | `ko_fall` | Mid-fall after a fatal blow: tipped backward ~45°, feet leaving the ground, arms thrown up, the weapon flying loose out of the hands. |
| 20 | `ko_down` | Collapsed on the ground: body lying horizontally, limbs sprawled, eyes closed, the weapon lying separately beside the body. |

각 요청은 이렇게 보낸다:

```
Pose <번호> of 20 — <파일명 대문자>.
<위 표의 지시문>
Apply all the rules from my first message.
```

## 3단계 — 받은 뒤

`asset_img/{gid}/` 에 넣으면 파이프라인이 처리한다.
(한 장에 여러 컷이 모여 나와도 자동 분리된다)

---
체격 참고: 전투력 순위 {rank}위 / {score:.3f}
'''


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('ids', nargs='*')
    ap.add_argument('--top', type=int, help='전투력 상위 N명 일괄 생성')
    ap.add_argument('--list', action='store_true', help='순위만 출력')
    args = ap.parse_args()

    roster = load_roster()
    rank_of = {r['id']: (i + 1, r) for i, r in enumerate(roster)}

    if args.list:
        for i, r in enumerate(roster[:args.top or 70], 1):
            have = '○' if os.path.exists(os.path.join(SRC_DIR, r['id'] + '.webp')) else '✗'
            print(f'{i:3d}. {have} {r["id"]:14s} {r["name"]}')
        return

    targets = args.ids or [r['id'] for r in roster[:args.top or 0]]
    if not targets:
        ap.error('장수 id 를 주거나 --top N 을 쓰세요')

    made = 0
    for gid in targets:
        path = make_ref(gid)
        if not path:
            print(f'  ✗ {gid}: 전신 아트가 없다')
            continue
        rank, row = rank_of.get(gid, (0, {'name': gid, 'score': 0}))
        with open(os.path.join(OUT_DIR, gid + '_prompt.md'), 'w', encoding='utf-8') as f:
            f.write(PROMPT.format(gid=gid, name=row['name'], rank=rank, score=row['score']))
        print(f'  ○ {rank:3d}위 {row["name"]:6s} → {os.path.relpath(path, ROOT)}')
        made += 1
    print(f'\n{made}명 준비 완료 → {os.path.relpath(OUT_DIR, ROOT)}/')


if __name__ == '__main__':
    main()
