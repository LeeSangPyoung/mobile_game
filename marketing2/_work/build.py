# -*- coding: utf-8 -*-
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont, ImageFilter, ImageOps, ImageEnhance
import math

ROOT = Path(__file__).resolve().parents[2]
ASSETS = ROOT / "assets"
GEN_FULL = ASSETS / "generals" / "fullbody_v6_aligned"
SRC = ROOT / "marketing2" / "source"
RAW = SRC / "current_raw"
OUT = ROOT / "marketing2" / "exports"
FONTS = ROOT / "marketing2" / "_fonts"

OUT.mkdir(parents=True, exist_ok=True)

W, H = 1080, 1920
GOLD = (255, 207, 88)
CREAM = (255, 244, 205)
INK = (38, 20, 10)
NAVY = (9, 16, 28)


def font(name, size):
    return ImageFont.truetype(str(FONTS / name), size)


HEAD = lambda size: font("BlackHanSans.ttf", size)
SANS = lambda size: font("NotoSansKR.ttf", size)


def gen(gid):
    return Image.open(GEN_FULL / f"{gid}.webp").convert("RGBA")


def cover(img, size, center=(0.5, 0.5)):
    return ImageOps.fit(img.convert("RGB"), size, method=Image.Resampling.LANCZOS, centering=center)


def contain(img, size):
    src = img.convert("RGBA").copy()
    src.thumbnail(size, Image.Resampling.LANCZOS)
    out = Image.new("RGBA", size, (0, 0, 0, 0))
    out.alpha_composite(src, ((size[0] - src.width) // 2, size[1] - src.height))
    return out


def rounded_mask(size, radius):
    mask = Image.new("L", size, 0)
    ImageDraw.Draw(mask).rounded_rectangle((0, 0, size[0] - 1, size[1] - 1), radius=radius, fill=255)
    return mask


def paste_round(base, img, box, radius=42, border=5):
    x, y, w, h = box
    src = cover(img, (w, h)).convert("RGBA")
    mask = rounded_mask((w, h), radius)
    base.paste(src, (x, y), mask)
    d = ImageDraw.Draw(base, "RGBA")
    d.rounded_rectangle((x, y, x + w, y + h), radius=radius, outline=(255, 220, 128, 220), width=border)


def paste_crop_round(base, img, crop, box, radius=34):
    paste_round(base, img.crop(crop), box, radius=radius, border=4)


def vertical_gradient(size, top, bottom):
    w, h = size
    g = Image.new("RGB", (1, h))
    for y in range(h):
        t = y / max(1, h - 1)
        g.putpixel((0, y), tuple(int(top[i] + (bottom[i] - top[i]) * t) for i in range(3)))
    return g.resize(size)


def bg(accent, soft=None):
    soft = soft or tuple(min(255, c + 80) for c in accent)
    base = vertical_gradient((W, H), soft, accent).convert("RGBA")
    d = ImageDraw.Draw(base, "RGBA")
    for i, y in enumerate(range(450, H, 230)):
        alpha = 28 if i % 2 == 0 else 18
        d.rounded_rectangle((-90, y, W + 90, y + 82), radius=42, fill=(255, 255, 255, alpha))
    for x, y, r, alpha in [(-120, 520, 520, 34), (W - 210, 810, 430, 26), (160, 1420, 540, 28)]:
        d.ellipse((x, y, x + r, y + r), fill=(255, 255, 255, alpha))
    d.ellipse((-240, 1180, 520, 2050), fill=(255, 255, 255, 42))
    d.polygon([(0, H - 360), (360, H - 220), (230, H), (0, H)], fill=(155, 28, 18, 70))
    return base


def text_stroke(d, xy, text, fnt, fill=CREAM, stroke=INK, sw=5, anchor="la"):
    d.text(xy, text, font=fnt, fill=fill, stroke_width=sw, stroke_fill=stroke, anchor=anchor)


def draw_headline(base, headline, sub, accent):
    d = ImageDraw.Draw(base, "RGBA")
    d.rounded_rectangle((42, 44, W - 42, 388), radius=58, fill=(255, 255, 255, 226))
    y = 92
    for line in headline.split("\n"):
        text_stroke(d, (72, y), line, HEAD(78), fill=accent, stroke=(255, 255, 255), sw=3)
        y += 88
    d.text((76, y + 10), sub, font=SANS(32), fill=(50, 46, 56))


def paste_general(base, gid, center_x, bottom, height, flip=False):
    img = gen(gid)
    if flip:
        img = ImageOps.mirror(img)
    img = contain(img, (int(height * 0.82), height))
    x = int(center_x - img.width / 2)
    y = int(bottom - img.height)
    shadow = Image.new("RGBA", img.size, (0, 0, 0, 0))
    shadow.paste((0, 0, 0, 150), mask=img.getchannel("A"))
    base.alpha_composite(shadow.filter(ImageFilter.GaussianBlur(22)), (x, y + 18))
    base.alpha_composite(img, (x, y))


def phone_card(base, raw_name, box):
    raw = Image.open(RAW / raw_name)
    x, y, w, h = box
    d = ImageDraw.Draw(base, "RGBA")
    d.rounded_rectangle((x - 12, y - 12, x + w + 12, y + h + 12), radius=48, fill=NAVY, outline=(255, 220, 128, 230), width=6)
    paste_round(base, raw, box, radius=36, border=2)


def badge(base, text, y):
    d = ImageDraw.Draw(base, "RGBA")
    tw = d.textlength(text, font=SANS(38))
    x = (W - tw - 92) / 2
    d.rounded_rectangle((x, y, x + tw + 92, y + 78), radius=39, fill=(40, 24, 12, 235), outline=(255, 222, 118, 230), width=3)
    d.text((W / 2, y + 38), text, font=SANS(38), fill=(255, 228, 140), anchor="mm")


def battle_bubble(d, xy, text, right=False):
    x, y = xy
    tw = int(d.textlength(text, font=SANS(25)))
    w, h = tw + 42, 48
    if right:
        box = (x - w, y, x, y + h)
        tail = [(x - 18, y + h - 2), (x + 10, y + h + 18), (x - 48, y + h - 4)]
        tx = x - w + 20
    else:
        box = (x, y, x + w, y + h)
        tail = [(x + 24, y + h - 2), (x - 6, y + h + 18), (x + 56, y + h - 4)]
        tx = x + 20
    d.rounded_rectangle(box, radius=18, fill=(255, 244, 205, 245), outline=(80, 36, 10, 245), width=3)
    d.polygon(tail, fill=(255, 244, 205, 245), outline=(80, 36, 10, 245))
    d.text((tx, y + 9), text, font=SANS(25), fill=(45, 18, 4))


def soldier_cluster(d, cx, cy, color, flip=False):
    body = color
    dark = (20, 24, 34, 245)
    metal = (255, 232, 176, 245)
    offsets = [(-24, 8), (-8, -2), (12, 10), (28, -4), (-34, -9), (36, 18)]
    for ox, oy in offsets:
        x, y = cx + ox, cy + oy
        d.ellipse((x - 8, y - 8, x + 8, y + 8), fill=dark, outline=metal, width=2)
        d.polygon([(x - 11, y + 8), (x + 11, y + 8), (x + 14, y + 30), (x - 14, y + 30)], fill=body, outline=dark)
        if flip:
            d.line((x + 28, y + 30, x - 24, y - 14), fill=metal, width=3)
        else:
            d.line((x - 28, y + 30, x + 24, y - 14), fill=metal, width=3)


def battle_action_overlay(base, box):
    x, y, _, _ = box
    d = ImageDraw.Draw(base, "RGBA")
    centers = [(x + 310, y + 520), (x + 395, y + 470), (x + 455, y + 315)]
    for cx, cy in centers:
        d.ellipse((cx - 88, cy - 28, cx + 88, cy + 28), fill=(55, 33, 15, 82))
    soldier_cluster(d, x + 292, y + 500, (46, 128, 234, 255))
    soldier_cluster(d, x + 388, y + 455, (215, 56, 42, 255), True)
    soldier_cluster(d, x + 448, y + 310, (215, 56, 42, 255), True)
    soldier_cluster(d, x + 420, y + 365, (46, 128, 234, 255))
    d.ellipse((x + 324, y + 452, x + 428, y + 556), outline=(255, 72, 45, 145), width=6)
    d.line((x + 340, y + 455, x + 420, y + 548), fill=(255, 238, 160, 230), width=7)
    d.line((x + 420, y + 455, x + 340, y + 548), fill=(255, 238, 160, 230), width=7)
    for sx, sy in [(360, 488), (394, 528), (430, 420)]:
        d.polygon(
            [(x + sx, y + sy - 20), (x + sx + 9, y + sy - 4), (x + sx + 31, y + sy),
             (x + sx + 9, y + sy + 5), (x + sx, y + sy + 22), (x + sx - 9, y + sy + 5),
             (x + sx - 31, y + sy), (x + sx - 9, y + sy - 4)],
            fill=(255, 196, 48, 220),
            outline=(100, 28, 8, 230),
        )
    battle_bubble(d, (x + 120, y + 390), "돌격!")
    battle_bubble(d, (x + 560, y + 350), "막아라!", True)


def build_icon():
    size = 512
    base = vertical_gradient((size, size), (255, 238, 186), (243, 139, 42)).convert("RGBA")
    d = ImageDraw.Draw(base, "RGBA")
    for r, alpha in [(360, 30), (250, 48), (160, 60)]:
        d.ellipse((size / 2 - r, size * 0.44 - r, size / 2 + r, size * 0.44 + r), fill=(255, 255, 255, alpha))
    hero = contain(gen("guan_yu"), (430, 560))
    base.alpha_composite(hero, ((size - hero.width) // 2, size - hero.height + 74))
    d.rounded_rectangle((12, 12, size - 12, size - 12), radius=96, outline=(95, 48, 12), width=22)
    d.rounded_rectangle((24, 24, size - 24, size - 24), radius=82, outline=(255, 222, 104), width=10)
    base.convert("RGB").save(OUT / "icon_512.png", quality=95)


def build_feature():
    base = vertical_gradient((1024, 500), (255, 224, 130), (241, 135, 42)).convert("RGBA")
    d = ImageDraw.Draw(base, "RGBA")
    d.rounded_rectangle((-70, 52, 1088, 134), radius=38, fill=(255, 255, 255, 46))
    d.rounded_rectangle((-90, 238, 820, 318), radius=38, fill=(255, 255, 255, 38))
    d.ellipse((500, -180, 1140, 460), fill=(255, 255, 255, 42))
    d.ellipse((650, 120, 1160, 630), fill=(255, 235, 160, 55))
    logo = Image.open(ASSETS / "ui" / "home_logo_samguk.png").convert("RGBA")
    logo.thumbnail((430, 140), Image.Resampling.LANCZOS)
    base.alpha_composite(logo, (44, 46))
    for gid, cx, bh, ht, flip in [
        ("cao_cao", 560, 520, 430, False),
        ("lu_bu", 710, 535, 510, False),
        ("zhao_yun", 865, 520, 430, True),
    ]:
        paste_general(base, gid, cx, bh, ht, flip)
    text_stroke(d, (54, 198), "손끝으로 천하를 지휘", HEAD(54), fill=(255, 255, 255), stroke=(130, 36, 16), sw=5)
    d.rounded_rectangle((54, 270, 462, 320), radius=19, fill=(255, 247, 220, 215))
    d.text((70, 282), "장수 수집 · 포메이션 · 실시간 공성", font=SANS(24), fill=(70, 35, 12))
    d.rounded_rectangle((58, 354, 408, 424), radius=24, fill=(185, 30, 22, 238), outline=(255, 232, 128), width=3)
    d.text((233, 387), "손가락 삼국지", font=SANS(35), fill=(255, 244, 205), anchor="mm")
    base.convert("RGB").save(OUT / "feature_graphic_1024x500.png", quality=95)


def content_shot(fname, accent, accent_dark, headline, sub, raw, badge_text, soft=None):
    base = bg(accent, soft)
    draw_headline(base, headline, sub, accent_dark)
    cw, ch = 760, 1316
    phone_card(base, raw, ((W - cw) // 2, 470, cw, ch))
    badge(base, badge_text, 1812)
    base.convert("RGB").save(OUT / fname, quality=95)


def dust_cloud(d, cx, cy, s=1.0):
    col = (250, 244, 228, 175)
    for dx, dy, r in [(-34, 4, 40), (-2, -16, 48), (32, -2, 40), (10, 16, 34), (-16, 14, 32)]:
        d.ellipse((cx + dx * s - r * s, cy + dy * s - r * s, cx + dx * s + r * s, cy + dy * s + r * s), fill=col)


# 1) 메인/타이틀 — main.png(옛 로고 잘라내고 새 로고 얹음)
def ss_title():
    art = Image.open(ASSETS / "main.png")
    crop = art.crop((0, int(art.height * 0.252), art.width, art.height))
    base = cover(crop, (W, H)).convert("RGBA")
    d = ImageDraw.Draw(base, "RGBA")
    d.rounded_rectangle((40, 36, W - 40, 322), radius=54, fill=(255, 255, 255, 232))
    logo = Image.open(ASSETS / "ui" / "home_logo_samguk.png").convert("RGBA")
    logo.thumbnail((W - 260, 232), Image.Resampling.LANCZOS)
    base.alpha_composite(logo, ((W - logo.width) // 2, 60))
    d.rounded_rectangle((70, H - 290, W - 70, H - 70), radius=50, fill=(40, 24, 12, 236), outline=(255, 222, 118, 235), width=5)
    d.text((W / 2, H - 214), "삼국지 200 명장", font=HEAD(82), fill=(255, 226, 142), anchor="mm")
    d.text((W / 2, H - 124), "손끝으로 천하통일!", font=HEAD(70), fill=(255, 255, 255), anchor="mm", stroke_width=4, stroke_fill=(150, 40, 18))
    base.convert("RGB").save(OUT / "screenshot_01.png", quality=95)


# 2) 전쟁신 — 실시간 전투 + 병사 + 말구름
def ss_war():
    base = bg((64, 150, 230), (190, 232, 255))
    draw_headline(base, "탭 한 번으로 출진!\n실시간 성 점령", "적 성으로 부대를 보내 모두 점령하세요", (35, 115, 210))
    box = (168, 484, 744, 1320)
    phone_card(base, "raw_battle.png", box)
    battle_action_overlay(base, box)
    badge(base, "돌격 · 점령 · 방어", 1812)
    base.convert("RGB").save(OUT / "screenshot_02.png", quality=95)


# 3) 창/기/궁 전략 상성
def ss_strategy():
    base = bg((70, 180, 110), (192, 248, 206))
    draw_headline(base, "성에서 창·기·궁 선택\n상성으로 전투력 ×1.5", "창 > 기 > 궁, 조합을 읽고 승리", (44, 145, 78))
    d = ImageDraw.Draw(base, "RGBA")
    pts = [(W / 2, 720), (262, 1276), (818, 1276)]
    labels = [("창", "SPEAR", (70, 160, 255)), ("기", "CAVALRY", (245, 80, 55)), ("궁", "ARCHER", (255, 184, 55))]
    for a, b in [(pts[0], pts[1]), (pts[1], pts[2]), (pts[2], pts[0])]:
        d.line((a[0], a[1], b[0], b[1]), fill=(255, 255, 255, 205), width=13)
    for (x, y), (ko, en, col) in zip(pts, labels):
        d.ellipse((x - 152, y - 152, x + 152, y + 152), fill=(*col, 240), outline=(255, 255, 255, 235), width=9)
        d.text((x, y - 22), ko, font=HEAD(104), fill=(255, 255, 255), anchor="mm", stroke_width=5, stroke_fill=(20, 34, 20))
        d.text((x, y + 82), en, font=SANS(26), fill=(255, 255, 255), anchor="mm")
    badge(base, "상성 우위 시 데미지 1.5배", 1616)
    base.convert("RGB").save(OUT / "screenshot_03.png", quality=95)


# 4) 내장수 + 디테일 아우라
def ss_generals():
    base = bg((150, 96, 228), (228, 200, 255))
    draw_headline(base, "200 명장 수집\n화려한 장수 연출", "장수마다 고유 능력과 아우라", (118, 64, 208))
    phone_card(base, "raw_aura.png", (92, 500, 486, 864))
    phone_card(base, "raw_deploy.png", (612, 560, 396, 704))
    badge(base, "명장 200명 · 등급별 능력", 1812)
    base.convert("RGB").save(OUT / "screenshot_04.png", quality=95)


# 5) 강화모드(제일 중요) — 과정 → 결과 아우라
def ss_enhance():
    base = bg((232, 150, 40), (255, 224, 142))
    draw_headline(base, "장수 강화!\n별 모아 최강으로", "재료 선택 → 강화 → 화려한 성공 연출", (210, 96, 24))
    phone_card(base, "raw_enhance.png", (60, 540, 462, 822))
    phone_card(base, "raw_enhance_result.png", (560, 540, 446, 794))
    d = ImageDraw.Draw(base, "RGBA")
    ax, ay = 540, 952
    d.ellipse((ax - 52, ay - 52, ax + 52, ay + 52), fill=(255, 255, 255, 240), outline=(180, 90, 10, 240), width=5)
    d.polygon([(ax - 20, ay - 26), (ax - 20, ay + 26), (ax + 26, ay)], fill=(210, 96, 24, 255))
    badge(base, "강화 성공! Lv1 → Lv2", 1812)
    base.convert("RGB").save(OUT / "screenshot_05.png", quality=95)


# 6) 전투력 관리
def ss_power():
    content_shot("screenshot_06.png", (228, 96, 60), (205, 64, 36),
                 "전투력 강화\n계속 성장하는 군단", "성·병력·생산을 올려 더 강하게",
                 "raw_upgrade.png", "전투력 관리 모드")


# 7) 포로 및 보상
def ss_prisoner():
    content_shot("screenshot_07.png", (92, 140, 220), (40, 96, 195),
                 "승리 보상 · 포로 등용", "전투에서 이기면 보상과 포로 획득",
                 "raw_prisoner.png", "보상 · 포로 · 회유")


# 8) 방대한 콘텐츠 + 오프라인
def ss_content():
    content_shot("screenshot_08.png", (84, 188, 160), (36, 150, 112),
                 "10챕터 200스테이지\n+ 무한모드", "오프라인으로 언제든 가볍게",
                 "raw_stage_ch6.png", "방대한 콘텐츠 · 오프라인")


def main():
    for old in OUT.glob("*.png"):
        old.unlink()
    build_icon()
    build_feature()
    ss_title()
    ss_war()
    ss_strategy()
    ss_generals()
    ss_enhance()
    ss_power()
    ss_prisoner()
    ss_content()
    print("marketing2 exports complete")


if __name__ == "__main__":
    main()
