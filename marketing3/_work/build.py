# -*- coding: utf-8 -*-
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont, ImageFilter, ImageOps, ImageEnhance

ROOT = Path(__file__).resolve().parents[2]
SRC = ROOT / "marketing3" / "source"
OUT = ROOT / "marketing3" / "exports"
ASSETS = ROOT / "assets"
OUT.mkdir(parents=True, exist_ok=True)

W, H = 1080, 1920
GOLD = (235, 190, 102)
GOLD2 = (255, 226, 151)
INK = (5, 8, 13)
RED = (150, 24, 18)
SLATE = (78, 91, 108)


def font(size, bold=False):
    candidates = [
        Path("C:/Windows/Fonts/malgunbd.ttf" if bold else "C:/Windows/Fonts/malgun.ttf"),
        ROOT / "marketing2" / "_fonts" / ("BlackHanSans.ttf" if bold else "NotoSansKR.ttf"),
        Path("C:/Windows/Fonts/arialbd.ttf" if bold else "C:/Windows/Fonts/arial.ttf"),
    ]
    for p in candidates:
        if p.exists():
            return ImageFont.truetype(str(p), size)
    return ImageFont.load_default()


F_EYEBROW = font(27, True)
F_TITLE = font(74, True)
F_TITLE_SMALL = font(64, True)
F_SUB = font(31, True)
F_CHIP = font(25, True)
F_BUTTON = font(34, True)


def cover(img, size, centering=(0.5, 0.5)):
    return ImageOps.fit(img.convert("RGB"), size, method=Image.Resampling.LANCZOS, centering=centering)


def contain(img, size, bg=(8, 12, 20, 255)):
    src = img.convert("RGBA").copy()
    src.thumbnail(size, Image.Resampling.LANCZOS)
    out = Image.new("RGBA", size, bg)
    out.alpha_composite(src, ((size[0] - src.width) // 2, (size[1] - src.height) // 2))
    return out


def rounded_mask(size, radius):
    mask = Image.new("L", size, 0)
    ImageDraw.Draw(mask).rounded_rectangle((0, 0, size[0] - 1, size[1] - 1), radius=radius, fill=255)
    return mask


def paste_round(base, img, box, radius=42, mode="cover", centering=(0.5, 0.5)):
    x, y, w, h = box
    if mode == "contain":
        src = contain(img, (w, h))
    else:
        src = cover(img, (w, h), centering).convert("RGBA")
    mask = rounded_mask((w, h), radius)
    base.paste(src, (x, y), mask)


def enhance_image(img, brightness=0.94, color=1.08, contrast=1.08):
    out = ImageEnhance.Brightness(img).enhance(brightness)
    out = ImageEnhance.Color(out).enhance(color)
    out = ImageEnhance.Contrast(out).enhance(contrast)
    return out


def background(src, accent=GOLD):
    bg = cover(src, (W, H)).filter(ImageFilter.GaussianBlur(22))
    bg = enhance_image(bg, 0.52, 1.08, 1.12).convert("RGBA")
    decor = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(decor, "RGBA")
    d.rectangle((0, 0, W, H), fill=(0, 0, 0, 150))
    d.rounded_rectangle((-70, 345, W + 70, 455), radius=48, fill=(255, 255, 255, 16))
    d.rounded_rectangle((-90, 1510, W + 90, 1605), radius=48, fill=(255, 255, 255, 13))
    d.polygon([(W - 350, 0), (W, 0), (W, 410), (W - 470, 312)], fill=(*accent, 58))
    d.polygon([(0, H - 430), (370, H - 260), (245, H), (0, H)], fill=(*RED, 62))
    d.polygon([(W - 220, H), (W, H - 180), (W, H)], fill=(*SLATE, 52))
    d.rounded_rectangle((34, 34, W - 34, H - 34), radius=38, outline=(*GOLD, 95), width=2)
    bg = Image.alpha_composite(bg, decor)
    return bg


def text_stroke(d, xy, text, fnt, fill=GOLD2, stroke=(34, 14, 6), sw=4, anchor=None):
    d.text(xy, text, font=fnt, fill=fill, stroke_width=sw, stroke_fill=stroke, anchor=anchor)


def draw_copy(base, eyebrow, title, sub):
    d = ImageDraw.Draw(base, "RGBA")
    badge_w = int(d.textlength(eyebrow, font=F_EYEBROW)) + 54
    d.rounded_rectangle((64, 58, 64 + badge_w, 110), radius=26, fill=(8, 13, 22, 220), outline=(*GOLD2, 210), width=2)
    d.text((91, 72), eyebrow, font=F_EYEBROW, fill=GOLD2, stroke_width=1, stroke_fill=(35, 16, 6))
    y = 150
    title_font = F_TITLE_SMALL if max(len(line) for line in title.split("\n")) >= 11 else F_TITLE
    for line in title.split("\n"):
        text_stroke(d, (64, y), line, title_font, sw=5)
        y += 78
    d.text((66, y + 14), sub, font=F_SUB, fill=(255, 233, 181), stroke_width=3, stroke_fill=(22, 9, 4))


def phone_frame(base, shot, y=500, w=720, h=1279, mode="cover", centering=(0.5, 0.5)):
    x = (W - w) // 2
    shadow = Image.new("RGBA", (w + 78, h + 78), (0, 0, 0, 0))
    sd = ImageDraw.Draw(shadow, "RGBA")
    sd.rounded_rectangle((39, 39, w + 39, h + 39), radius=58, fill=(0, 0, 0, 140))
    base.alpha_composite(shadow.filter(ImageFilter.GaussianBlur(22)), (x - 39, y - 22))
    d = ImageDraw.Draw(base, "RGBA")
    d.rounded_rectangle((x - 10, y - 10, x + w + 10, y + h + 10), radius=60, fill=(7, 11, 18, 255), outline=(*GOLD2, 225), width=5)
    d.rounded_rectangle((x - 2, y - 2, x + w + 2, y + h + 2), radius=48, outline=(98, 112, 130, 170), width=3)
    paste_round(base, shot, (x, y, w, h), radius=42, mode=mode, centering=centering)
    return x, y, w, h


def chip(base, text, xy, anchor="left"):
    d = ImageDraw.Draw(base, "RGBA")
    tw = d.textlength(text, font=F_CHIP)
    w, h = int(tw) + 44, 48
    x, y = xy
    if anchor == "center":
        x -= w // 2
    d.rounded_rectangle((x, y, x + w, y + h), radius=22, fill=(8, 13, 22, 225), outline=(*GOLD2, 205), width=2)
    d.text((x + 22, y + 10), text, font=F_CHIP, fill=(255, 236, 180), stroke_width=1, stroke_fill=(35, 16, 6))


def screenshot(out_name, src_name, eyebrow, title, sub, y=510, mode="cover", centering=(0.5, 0.5), chip_text=None):
    src = Image.open(SRC / src_name)
    base = background(src)
    draw_copy(base, eyebrow, title, sub)
    phone_frame(base, src, y=y, mode=mode, centering=centering)
    if chip_text:
        chip(base, chip_text, (W // 2, H - 190), "center")
    base.convert("RGB").save(OUT / out_name, quality=95)


def keyart_screenshot():
    src = Image.open(SRC / "01_keyart.png")
    base = background(src)
    draw_copy(base, "삼국지 전략", "손끝으로\n천하를 지휘", "장수 수집 · 편성 · 전쟁을 한 번에")
    phone_frame(base, src, y=460, w=700, h=1340, mode="cover", centering=(0.5, 0.5))
    d = ImageDraw.Draw(base, "RGBA")
    d.rounded_rectangle((266, 1680, 814, 1760), radius=24, fill=(188, 30, 22, 238), outline=(*GOLD2, 220), width=3)
    d.text((540, 1719), "손가락 삼국지", font=F_BUTTON, fill=(255, 244, 205), anchor="mm", stroke_width=2, stroke_fill=(80, 12, 6))
    base.convert("RGB").save(OUT / "screenshot_01_keyart.png", quality=95)


def feature_graphic():
    src = Image.open(SRC / "02_battle.png")
    base = cover(src, (1024, 500)).filter(ImageFilter.GaussianBlur(12))
    base = enhance_image(base, 0.55, 1.06, 1.12).convert("RGBA")
    d = ImageDraw.Draw(base, "RGBA")
    d.rectangle((0, 0, 1024, 500), fill=(4, 8, 14, 130))
    d.polygon([(720, 0), (1024, 0), (1024, 360), (650, 300)], fill=(*GOLD, 58))
    d.polygon([(0, 260), (310, 340), (360, 500), (0, 500)], fill=(*RED, 58))
    logo_path = ASSETS / "ui" / "home_logo_samguk.png"
    if logo_path.exists():
        logo = Image.open(logo_path).convert("RGBA")
        logo.thumbnail((610, 205), Image.Resampling.LANCZOS)
        base.alpha_composite(logo, (34, 18))
    title_font = font(48, True)
    text_stroke(d, (58, 202), "여섯 성이 부딪히는", title_font, sw=4)
    text_stroke(d, (58, 258), "실시간 공성전", title_font, sw=4)
    d.text((60, 324), "장수 수집 · 포메이션 · 실시간 공성 전략", font=font(25, True), fill=(255, 226, 154), stroke_width=2, stroke_fill=(30, 12, 4))
    paste_round(base, src, (664, 24, 296, 452), radius=34, mode="cover", centering=(0.5, 0.5))
    d.rounded_rectangle((654, 14, 970, 486), radius=44, outline=(*GOLD2, 220), width=4)
    base.convert("RGB").save(OUT / "feature_graphic_1024x500.png", quality=95)


def icon():
    src = Image.open(SRC / "01_keyart.png")
    img = cover(src, (512, 512), centering=(0.5, 0.48)).convert("RGBA")
    mask = rounded_mask((512, 512), 108)
    out = Image.new("RGBA", (512, 512), (0, 0, 0, 0))
    out.paste(img, (0, 0), mask)
    d = ImageDraw.Draw(out, "RGBA")
    d.rounded_rectangle((12, 12, 500, 500), radius=108, outline=(90, 42, 10, 255), width=20)
    d.rounded_rectangle((24, 24, 488, 488), radius=94, outline=(*GOLD2, 255), width=8)
    out.save(OUT / "icon_512.png")


def main():
    for old in OUT.glob("*.png"):
        old.unlink()
    icon()
    feature_graphic()
    keyart_screenshot()
    screenshot("screenshot_02_battle.png", "02_battle.png", "대규모 전쟁", "다수의 성이 맞붙는\n실시간 공성", "병력 이동과 장수 명령이 동시에 펼쳐지는 전장", y=500, mode="contain", chip_text="실제 전투 화면")
    screenshot("screenshot_03_roster.png", "03_roster.png", "장수 편성", "10인 선봉을\n빠르게 구성", "천·지·인 포메이션과 자동 편성을 지원", y=500, mode="contain", centering=(0.5, 0.45), chip_text="수집과 편성을 한 화면에")
    screenshot("screenshot_04_aura.png", "04_aura.png", "전설 장수", "아우라가 터지는\n무장 카드", "등급, 능력치, 전투력을 크게 확인", y=500, mode="cover", chip_text="명장 수집의 손맛")
    screenshot("screenshot_05_enhance_result.png", "05_enhance_result.png", "장수 강화", "성공 순간까지\n강하게 연출", "Lv 상승과 능력치 변화를 즉시 확인", y=500, mode="cover", centering=(0.5, 0.52), chip_text="Lv 1 → Lv 2 성공")
    screenshot("screenshot_06_enhance_prepare.png", "06_enhance_prepare.png", "성장 전략", "재료와 성공률을\n보고 강화", "투입 재료에 따라 성공률이 상승", y=520, mode="contain", chip_text="성공률 90%")
    screenshot("screenshot_07_recruit.png", "07_recruit.png", "포로 회유", "적장을 설득해\n내 편으로", "전투 후 포획한 장수를 등용하는 선택", y=500, mode="cover", centering=(0.5, 0.5), chip_text="회유 · 설득 · 등용")
    screenshot("screenshot_08_council.png", "08_council.png", "전장 이벤트", "선택으로 흐름이\n바뀌는 군의", "전투 전후 상황에 맞춘 삼국지식 이벤트", y=500, mode="cover", centering=(0.5, 0.5), chip_text="전략 선택 이벤트")
    print("marketing3 exports complete")


if __name__ == "__main__":
    main()
