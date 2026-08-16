#!/usr/bin/env python3
"""컷아웃 1장 → 부위별 조각 + 리그 JSON.

컷 넘기기(프레임 애니메이션)를 버리고 조각을 코드로 움직이기 위한 전처리.
조각 경계는 폴리곤/사각형으로 잘라내되, 회전시켰을 때 이음매가 벌어지지 않도록
각 마스크를 몇 px 부풀리고(dilate) 가장자리를 흐린다(feather).

출력: assets/duel_rig/<name>/{part}.webp + rig.json
"""
import json
import os
import sys

from PIL import Image, ImageChops, ImageDraw, ImageFilter

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT_ROOT = os.path.join(ROOT, 'assets', 'duel_rig')

DILATE = 7      # 조각끼리 겹치는 여유. 회전해도 살 틈이 안 보이게
FEATHER = 1.6   # 경계 흐림. 잘린 티를 없앤다


def rect(x0, y0, x1, y1):
    return [(x0, y0), (x1, y0), (x1, y1), (x0, y1)]


def inpaint(img, hole, rounds=16):
    """구멍(hole=255)을 주변 색으로 메운다.

    무기를 별도 관절로 떼어내면 몸통에 무기가 지나가던 대각선 구멍이 남는다.
    갑옷은 무늬가 촘촘해서 주변 색을 번지게 하는 것만으로 충분히 가려진다
    (게다가 기본 자세에서는 무기가 그 자리를 거의 도로 덮는다).
    """
    known = img.getchannel('A').point(lambda v: 255 if v > 8 else 0)
    known = Image.composite(Image.new('L', img.size, 0), known, hole)
    rgb = img.convert('RGB')
    for _ in range(rounds):
        blurred = rgb.filter(ImageFilter.GaussianBlur(4))
        rgb = Image.composite(rgb, blurred, known)
        known = known.filter(ImageFilter.MaxFilter(5))
    # 알파: 구멍을 무작정 채우면 무기가 몸 밖을 지나던 구간까지 살이 붙는다.
    # 닫힘(closing)으로 '몸에 둘러싸인 구멍'만 골라 메운다.
    a = img.getchannel('A')
    k = 61
    closed = a.filter(ImageFilter.MaxFilter(k)).filter(ImageFilter.MinFilter(k))
    fill = Image.composite(closed, Image.new('L', img.size, 0), hole)
    out = rgb.convert('RGBA')
    out.putalpha(ImageChops.lighter(a, fill))
    return out


# 조운 기본 자세(pose_sheet 프레임 0, 알파 트림 후 383x423) 기준 조각 정의.
# 순서가 곧 뒤→앞 그리기 순서다.
RIGS = {
    # ── 현재 리그 소스 ──────────────────────────────────────────────
    # 새로 그린 대기 자세(초록 배경 시트 ①)를 조각낸다. 공격·피격 포즈와
    # 같은 회차에 그려져 의상이 정확히 일치한다 — 리그가 담당하는 걷기/대시만
    # 옛 의상으로 남던 문제가 이걸로 없어진다.
    'zhao_yun': {
        'src': 'asset_img/cut_atk/idle.png',
        'frame': (0, 0, 1280, 1024),
        'faces': 1,          # 이미 오른쪽을 본다
        'ground': 622,
        'height': 622,
        'claim': {'upper': [
            [(-4, 224), (698, 495), (684, 533), (-18, 262)],       # 창대
            [(499, 378), (705, 457), (663, 565), (457, 486)],      # 칼날 + 손잡이 장식
            [(-4, 209), (80, 242), (56, 306), (-28, 273)],         # 물미
        ]},
        'parts': [
            {'name': 'cape', 'pivot': (245, 320),
             'poly': [(232, 296), (258, 362), (232, 470), (162, 532),
                      (68, 542), (18, 480), (34, 388), (120, 318)]},
            {'name': 'legBack',  'pivot': (200, 405), 'poly': rect(98, 398, 302, 622)},
            {'name': 'legFront', 'pivot': (390, 420), 'poly': rect(302, 414, 512, 622)},
            {'name': 'upper',    'pivot': (300, 410), 'poly': None},
            {'name': 'head',     'pivot': (335, 190), 'poly': rect(202, 0, 442, 192)},
        ],
        'markers': {
            'weaponTip':  {'bone': 'upper', 'at': (668, 505)},
            'weaponButt': {'bone': 'upper', 'at': (12, 252)},
            'hand':       {'bone': 'upper', 'at': (395, 395)},
        },
    },

    # 화웅 — 조운과 같은 규격으로 뽑은 대기 자세를 조각낸다.
    # 리그가 있으면 걷기·피격·경직·KO 를 그림 없이 만들 수 있어서
    # 잘린 옛 시트를 완전히 끊을 수 있다(크기 튐의 마지막 원인이었다).
    'hua_xiong': {
        'src': 'asset_img/cut_hx/idle.png',
        'frame': (0, 0, 1280, 1024),
        'faces': 1,
        'ground': 562,
        'height': 562,
        'claim': {'upper': [
            [(19, 180), (706, 450), (692, 488), (5, 218)],         # 도끼 자루
            [(470, 372), (741, 398), (741, 562), (452, 520)],      # 도끼날
            [(-12, 182), (74, 206), (58, 254), (-28, 230)],        # 자루 끝
        ]},
        'parts': [
            {'name': 'cape', 'pivot': (450, 205),
             'poly': [(438, 182), (522, 176), (592, 240), (602, 332),
                      (560, 414), (478, 434), (443, 358), (432, 252)]},
            {'name': 'legBack',  'pivot': (215, 402), 'poly': rect(112, 396, 302, 562)},
            {'name': 'legFront', 'pivot': (378, 412), 'poly': rect(302, 406, 474, 562)},
            {'name': 'upper',    'pivot': (300, 405), 'poly': None},
            {'name': 'head',     'pivot': (365, 178), 'poly': rect(276, 0, 458, 180)},
        ],
        'markers': {
            'weaponTip':  {'bone': 'upper', 'at': (700, 520)},
            'weaponButt': {'bone': 'upper', 'at': (35, 208)},
            'hand':       {'bone': 'upper', 'at': (330, 300)},
        },
    },

    # ── 이전 소스 (구 의상) — 참고용 ─────────────────────────────────
    # pose_sheet 는 쓰지 않는다: 5명이 한 이미지에 딱 붙어 있어서 셀 경계에서
    # 망토와 창이 잘려 있다(모든 프레임이 좌/우 끝에 닿아 있음). 게임에서 창끝이
    # 잘려 보이던 것이 바로 이것이다 — 리그 문제가 아니라 원본 문제였다.
    # walk3_stable_v2 는 3프레임 모두 여백이 남아 있어 잘림이 없다.
    'zhao_yun_walk3': {
        'src': 'assets/arcade_duel/zhao_yun_walk3_stable_v2.png',
        'frame': (0, 0, 617, 849),
        'faces': 1,          # 이미 오른쪽을 본다 — 반전 불필요
        'ground': 542,
        'height': 542,
        # 창: 창대(얇게) / 칼날 / 물미를 각각 잡아 합친다
        'claim': {'upper': [
            [(55, 230), (531, 445), (515, 481), (39, 266)],        # 창대
            [(396, 361), (542, 428), (510, 502), (364, 435)],      # 칼날
            [(58, 214), (120, 243), (92, 307), (28, 278)],         # 물미
        ]},
        'parts': [
            {'name': 'cape', 'pivot': (168, 232),
             'poly': [(150, 190), (180, 232), (168, 322), (124, 356),
                      (40, 350), (0, 300), (2, 236), (58, 200)]},
            {'name': 'legBack',  'pivot': (170, 360), 'poly': rect(80, 352, 258, 542)},
            {'name': 'legFront', 'pivot': (330, 372), 'poly': rect(258, 366, 448, 542)},
            {'name': 'upper',    'pivot': (255, 365), 'poly': None},
            {'name': 'head',     'pivot': (288, 138), 'poly': rect(168, 0, 392, 140)},
        ],
        'markers': {
            'weaponTip':  {'bone': 'upper', 'at': (505, 455)},
            'weaponButt': {'bone': 'upper', 'at': (62, 255)},
            'hand':       {'bone': 'upper', 'at': (205, 300)},
        },
    },

    # 예전 소스 — 잘림 때문에 보류. 참고용으로 남긴다.
    'zhao_yun_posesheet': {
        'src': 'assets/arcade_duel/zhao_yun_pose_sheet.png',
        'frame': (0, 0, 396, 793),
        # 창은 화면을 대각선으로 가로지른다. 하나의 넓은 띠로 잡으면 몸통까지 딸려오므로
        # 창대(얇게) / 창날 / 물미를 각각 잡아서 합친다.
        'claim': {'upper': [
            [(24, 22), (356, 361), (324, 392), (-8, 53)],          # 창대
            [(27, 5), (125, 106), (73, 156), (-25, 56)],           # 창날
            [(310, 289), (359, 339), (301, 395), (252, 345)],      # 물미
        ]},
        'parts': [
            # 망토는 몸 뒤. 어깨를 축으로 늦게 따라오면 관성이 생긴다.
            {'name': 'cape', 'pivot': (258, 168),
             'poly': [(248, 128), (300, 132), (352, 168), (383, 214),
                      (376, 268), (330, 306), (272, 300), (246, 244)]},
            # 뒷다리 — 접지면이 애니메이션의 기준이다
            {'name': 'legBack', 'pivot': (128, 306), 'poly': rect(26, 296, 170, 423)},
            {'name': 'legFront', 'pivot': (212, 306), 'poly': rect(170, 300, 302, 423)},
            # 상체 = 몸통 + 양팔 + 창.
            # 창을 따로 떼면 가슴을 가로지르는 자리에 구멍이 남는다 — 한 덩어리로 둔다.
            {'name': 'upper', 'pivot': (176, 302), 'poly': None},   # None = 나머지 전부
            {'name': 'head', 'pivot': (172, 140), 'poly': rect(88, 0, 264, 142)},
            # NOTE: 창을 별도 관절로 떼면 큰 휘두름이 가능하지만, 창이 지나가던 자리에
            # 남는 대각선 구멍을 자동 보정(inpaint)으로는 못 메운다 — 뭉개진다.
            # 제대로 하려면 '창 없는 몸' 컷아웃 한 장을 따로 뽑아야 한다.
            # 그때까지는 창을 상체에 붙여 둔다.
        ],
        # 리그가 쓰는 기준점 (조각 좌표계 = 트림된 원본 픽셀)
        'faces': -1,        # 원본 그림이 왼쪽을 본다 (오른쪽을 보게 하려면 좌우 반전)
        'ground': 423,      # 발끝
        'height': 423,      # 알파 기준 실제 키 — 렌더 스케일 계산용
        # 뼈에 붙어 따라다니는 점. 무기 끝은 궤적 리본과 사거리 계산에 쓴다 —
        # 이게 있으면 사거리를 더 이상 손으로 맞추지 않아도 된다.
        'markers': {
            'weaponTip':  {'bone': 'upper', 'at': (22, 52)},
            'weaponButt': {'bone': 'upper', 'at': (312, 348)},
            'hand':       {'bone': 'upper', 'at': (196, 246)},
        },
    },
}


def build(name, spec):
    src = Image.open(os.path.join(ROOT, spec['src'])).convert('RGBA')
    frame = src.crop(spec['frame'])
    bbox = frame.getbbox()
    frame = frame.crop(bbox)
    W, H = frame.size

    alpha = frame.getchannel('A')
    taken = Image.new('L', (W, H), 0)          # 이미 다른 조각이 가져간 픽셀

    out_dir = os.path.join(OUT_ROOT, name)
    os.makedirs(out_dir, exist_ok=True)

    parts_meta = []
    # 세 종류: 폴리곤으로 자르는 것 / 선점 영역을 통째로 갖는 것(무기) / 나머지 전부(몸통)
    ordered = [p for p in spec['parts'] if p.get('poly')]
    claimed = [p for p in spec['parts'] if p.get('from_claim')]
    rest = [p for p in spec['parts'] if not p.get('poly') and not p.get('from_claim')]

    claims = {}
    for owner, polys in (spec.get('claim') or {}).items():
        if polys and not isinstance(polys[0], (list, tuple)) or isinstance(polys[0][0], (int, float)):
            polys = [polys]
        c = Image.new('L', (W, H), 0)
        for poly in polys:
            ImageDraw.Draw(c).polygon([tuple(pt) for pt in poly], fill=255)
        claims[owner] = c

    reserved = Image.new('L', (W, H), 0)       # 선점된 픽셀 — 다른 조각이 못 가져간다
    for c in claims.values():
        reserved.paste(255, (0, 0), c)
    free = reserved.point(lambda v: 255 - v)

    masks = {}
    for p in ordered:
        m = Image.new('L', (W, H), 0)
        ImageDraw.Draw(m).polygon(p['poly'], fill=255)
        m = m.filter(ImageFilter.MaxFilter(DILATE * 2 + 1))   # 여유분 부풀리기
        m = Image.composite(m, Image.new('L', (W, H), 0), free)
        masks[p['name']] = m
        taken.paste(255, (0, 0), m)

    for p in claimed:
        masks[p['name']] = claims[p['name']]    # 선점 영역이 곧 이 조각

    for p in rest:
        m = taken.point(lambda v: 255 - v)     # 아무도 안 가져간 나머지
        m = m.filter(ImageFilter.MaxFilter(DILATE * 2 + 1))
        # 무기가 빠져나간 자리도 몸통이 떠안는다 — 그 구멍은 아래에서 메운다
        for q in claimed:
            if q.get('from_claim') == p['name']:
                m.paste(255, (0, 0), claims[q['name']])
        masks[p['name']] = m

    for p in spec['parts']:
        m = masks[p['name']].filter(ImageFilter.GaussianBlur(FEATHER))
        # 조각 알파 = 원본 알파 × 마스크
        piece = frame.copy()
        piece.putalpha(Image.composite(alpha, Image.new('L', (W, H), 0), m))

        # 무기를 떼어낸 몸통은 그 자리에 구멍이 남는다 → 주변 색으로 메운다
        holes = [claims[q['name']] for q in claimed if q.get('from_claim') == p['name']]
        if holes:
            hole = Image.new('L', (W, H), 0)
            for h in holes:
                hole.paste(255, (0, 0), h)
            piece = inpaint(piece, hole)

        bb = piece.getbbox()
        if bb is None:
            print(f'  ! {p["name"]}: 빈 조각 — 폴리곤 확인 필요')
            continue
        cropped = piece.crop(bb)
        cropped.save(os.path.join(out_dir, f'{p["name"]}.webp'), quality=92, method=6)

        px, py = p['pivot']
        parts_meta.append({
            'name': p['name'],
            'file': f'{p["name"]}.webp',
            'w': cropped.width, 'h': cropped.height,
            # 조각 이미지 안에서의 회전축 위치 (px)
            'px': px - bb[0], 'py': py - bb[1],
            # 회전축의 캐릭터 좌표 (발끝 중앙 원점, y는 위가 음수)
            'ax': px - W / 2, 'ay': py - spec['ground'],
        })
        print(f'  {p["name"]:9s} {cropped.width:4d}x{cropped.height:4d}  pivot=({px},{py})')

    rig = {
        'name': name,
        'source': spec['src'],
        'width': W, 'height': H,
        'ground': spec['ground'],
        'faces': spec.get('faces', 1),
        'parts': parts_meta,
        'markers': {k: {'bone': v['bone'], 'x': v['at'][0], 'y': v['at'][1]}
                    for k, v in (spec.get('markers') or {}).items()},
    }
    with open(os.path.join(out_dir, 'rig.json'), 'w', encoding='utf-8') as f:
        json.dump(rig, f, ensure_ascii=False, indent=2)
    print(f'  → {out_dir}/rig.json')


if __name__ == '__main__':
    targets = sys.argv[1:] or list(RIGS)
    for t in targets:
        print(f'[{t}]')
        build(t, RIGS[t])
