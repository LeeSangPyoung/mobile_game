from pathlib import Path
from PIL import Image, ImageDraw, ImageFont, ImageFilter, ImageOps

ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "marketing" / "source" / "current_raw"
OUT = ROOT / "marketing" / "exports"
ASSETS = ROOT / "assets"

W, H = 1080, 1920
PHONE_W, PHONE_H = 720, 1279


def font(size, bold=False):
    candidates = [
        Path("C:/Windows/Fonts/malgunbd.ttf" if bold else "C:/Windows/Fonts/malgun.ttf"),
        Path("C:/Windows/Fonts/NotoSansKR-Bold.otf" if bold else "C:/Windows/Fonts/NotoSansKR-Regular.otf"),
        Path("C:/Windows/Fonts/arialbd.ttf" if bold else "C:/Windows/Fonts/arial.ttf"),
    ]
    for p in candidates:
        if p.exists():
            return ImageFont.truetype(str(p), size)
    return ImageFont.load_default()


FONT_TITLE = font(76, True)
FONT_SUB = font(32, True)
FONT_BADGE = font(26, True)
FONT_SMALL = font(22, True)


def raw_name(preferred, fallback):
    return preferred if (RAW / preferred).exists() else fallback


def cover(img, size, centering=(0.5, 0.5)):
    return ImageOps.fit(img.convert("RGB"), size, method=Image.Resampling.LANCZOS, centering=centering)


def rounded_mask(size, radius):
    mask = Image.new("L", size, 0)
    d = ImageDraw.Draw(mask)
    d.rounded_rectangle((0, 0, size[0] - 1, size[1] - 1), radius=radius, fill=255)
    return mask


def paste_round(base, img, box, radius, centering=(0.5, 0.5)):
    x, y, w, h = box
    src = cover(img, (w, h), centering=centering).convert("RGBA")
    mask = rounded_mask((w, h), radius)
    base.paste(src, (x, y), mask)


def paste_contain_round(base, img, box, radius, bg=(8, 13, 22, 255)):
    x, y, w, h = box
    src = img.convert("RGBA").copy()
    src.thumbnail((w, h), Image.Resampling.LANCZOS)
    panel = Image.new("RGBA", (w, h), bg)
    panel.alpha_composite(src, ((w - src.width) // 2, (h - src.height) // 2))
    mask = rounded_mask((w, h), radius)
    base.paste(panel, (x, y), mask)


def paste_crop_round(base, img, crop_box, box, radius):
    crop = img.convert("RGB").crop(crop_box)
    paste_round(base, crop, box, radius)


def paste_crop_contain_round(base, img, crop_box, box, radius, bg=(8, 13, 22, 255)):
    x, y, w, h = box
    crop = img.convert("RGBA").crop(crop_box)
    crop.thumbnail((w, h), Image.Resampling.LANCZOS)
    panel = Image.new("RGBA", (w, h), bg)
    panel.alpha_composite(crop, ((w - crop.width) // 2, (h - crop.height) // 2))
    mask = rounded_mask((w, h), radius)
    base.paste(panel, (x, y), mask)


def text_with_stroke(draw, xy, text, fnt, fill, stroke=(34, 14, 6), sw=4, anchor=None):
    draw.text(xy, text, font=fnt, fill=fill, stroke_width=sw, stroke_fill=stroke, anchor=anchor)


def make_bg(src, accent=(214, 162, 67)):
    bg = cover(src, (W, H)).filter(ImageFilter.GaussianBlur(18))
    bg = ImageEnhanceSafe(bg, 0.78, 1.12)
    overlay = Image.new("RGBA", (W, H), (4, 8, 14, 168))
    bg = Image.alpha_composite(bg.convert("RGBA"), overlay)
    d = ImageDraw.Draw(bg, "RGBA")
    d.rectangle((0, 0, W, H), fill=(0, 0, 0, 30))
    d.polygon([(W - 350, 0), (W, 0), (W, 410), (W - 470, 310)], fill=(*accent, 50))
    d.polygon([(0, H - 430), (360, H - 250), (245, H), (0, H)], fill=(130, 24, 18, 44))
    d.polygon([(W - 220, H), (W, H - 180), (W, H)], fill=(86, 97, 112, 34))
    return bg


def ImageEnhanceSafe(img, brightness, saturation):
    from PIL import ImageEnhance

    img = ImageEnhance.Brightness(img).enhance(brightness)
    img = ImageEnhance.Color(img).enhance(saturation)
    img = ImageEnhance.Contrast(img).enhance(1.08)
    return img


def draw_phone(base, shot, y=500, centering=(0.5, 0.5), contain_image=False):
    x = (W - PHONE_W) // 2
    shadow = Image.new("RGBA", (PHONE_W + 70, PHONE_H + 70), (0, 0, 0, 0))
    sd = ImageDraw.Draw(shadow, "RGBA")
    sd.rounded_rectangle((35, 35, PHONE_W + 35, PHONE_H + 35), radius=54, fill=(0, 0, 0, 128))
    shadow = shadow.filter(ImageFilter.GaussianBlur(20))
    base.alpha_composite(shadow, (x - 35, y - 20))

    d = ImageDraw.Draw(base, "RGBA")
    d.rounded_rectangle((x - 10, y - 10, x + PHONE_W + 10, y + PHONE_H + 10), radius=58, fill=(9, 14, 22, 255), outline=(242, 211, 137, 210), width=5)
    d.rounded_rectangle((x - 2, y - 2, x + PHONE_W + 2, y + PHONE_H + 2), radius=46, outline=(86, 97, 112, 180), width=3)
    if contain_image:
        paste_contain_round(base, shot, (x, y, PHONE_W, PHONE_H), 42)
    else:
        paste_round(base, shot, (x, y, PHONE_W, PHONE_H), 42, centering=centering)
    return x, y


def draw_copy(base, eyebrow, title, sub):
    d = ImageDraw.Draw(base, "RGBA")
    d.rounded_rectangle((64, 58, 64 + d.textlength(eyebrow, font=FONT_BADGE) + 48, 108), radius=25, fill=(10, 16, 26, 205), outline=(255, 214, 109, 190), width=2)
    d.text((88, 72), eyebrow, font=FONT_BADGE, fill=(255, 217, 126), stroke_width=1, stroke_fill=(35, 16, 6))
    lines = title.split("\n")
    y = 142
    for line in lines:
        text_with_stroke(d, (64, y), line, FONT_TITLE, (255, 241, 194), sw=5)
        y += 82
    d.text((66, y + 12), sub, font=FONT_SUB, fill=(255, 233, 175), stroke_width=3, stroke_fill=(23, 10, 4))


def screenshot(name, raw_name, eyebrow, title, sub, phone_y=520):
    src = Image.open(RAW / raw_name)
    base = make_bg(src)
    d = ImageDraw.Draw(base, "RGBA")
    d.rounded_rectangle((34, 34, W - 34, H - 34), radius=38, outline=(214, 162, 67, 90), width=2)
    draw_copy(base, eyebrow, title, sub)
    is_manual_battle = raw_name == "raw_battle_manual.png"
    phone_center = (0.5, 0.5)
    draw_phone(base, src, y=phone_y, centering=phone_center, contain_image=is_manual_battle)
    base.convert("RGB").save(OUT / name, quality=95)


def draw_panel_label(draw, xy, text):
    x, y = xy
    w = int(draw.textlength(text, font=FONT_SMALL)) + 36
    draw.rounded_rectangle((x, y, x + w, y + 38), radius=18, fill=(9, 14, 22, 225), outline=(255, 214, 109, 210), width=2)
    draw.text((x + 18, y + 8), text, font=FONT_SMALL, fill=(255, 232, 165), stroke_width=1, stroke_fill=(34, 14, 6))


def enhance_collage():
    prepare = Image.open(RAW / "raw_enhance.png")
    result = Image.open(RAW / "raw_enhance_result.png")
    base = make_bg(result)
    d = ImageDraw.Draw(base, "RGBA")
    d.rounded_rectangle((34, 34, W - 34, H - 34), radius=38, outline=(214, 162, 67, 90), width=2)
    draw_copy(base, "장수 강화", "준비부터 성공까지\n한눈에 성장", "재료 선택, 성공률, 능력치 상승을 한 장에")

    x = (W - PHONE_W) // 2
    y = 510
    shadow = Image.new("RGBA", (PHONE_W + 70, PHONE_H + 70), (0, 0, 0, 0))
    sd = ImageDraw.Draw(shadow, "RGBA")
    sd.rounded_rectangle((35, 35, PHONE_W + 35, PHONE_H + 35), radius=54, fill=(0, 0, 0, 132))
    shadow = shadow.filter(ImageFilter.GaussianBlur(20))
    base.alpha_composite(shadow, (x - 35, y - 20))

    d.rounded_rectangle((x - 10, y - 10, x + PHONE_W + 10, y + PHONE_H + 10), radius=58, fill=(8, 12, 20, 255), outline=(242, 211, 137, 220), width=5)
    d.rounded_rectangle((x + 12, y + 12, x + PHONE_W - 12, y + PHONE_H - 12), radius=42, fill=(5, 10, 17, 255), outline=(86, 97, 112, 180), width=2)

    paste_crop_contain_round(base, result, (58, 22, 442, 605), (x + 34, y + 34, 314, 640), 28)
    paste_crop_contain_round(base, prepare, (46, 128, 456, 815), (x + 374, y + 34, 300, 640), 28)
    paste_crop_round(base, result, (60, 608, 438, 850), (x + 42, y + 720, 636, 420), 28)

    for bx, by, bw, bh in [
        (x + 34, y + 34, 314, 640),
        (x + 374, y + 34, 300, 640),
        (x + 42, y + 720, 636, 420),
    ]:
        d.rounded_rectangle((bx, by, bx + bw, by + bh), radius=26, outline=(255, 214, 109, 185), width=3)

    draw_panel_label(d, (x + 50, y + 50), "강화 카드")
    draw_panel_label(d, (x + 392, y + 52), "재료 · 성공률")
    draw_panel_label(d, (x + 64, y + 742), "성공 결과")
    base.convert("RGB").save(OUT / "screenshot_03_general_enhance.png", quality=95)


def feature_graphic():
    battle_raw = raw_name("raw_battle_manual.png", "raw_battle.png")
    bg_src = Image.open(RAW / battle_raw)
    base = cover(bg_src, (1024, 500)).filter(ImageFilter.GaussianBlur(10)).convert("RGBA")
    base = ImageEnhanceSafe(base.convert("RGB"), 0.72, 1.1).convert("RGBA")
    d = ImageDraw.Draw(base, "RGBA")
    d.rectangle((0, 0, 1024, 500), fill=(4, 8, 14, 138))
    d.polygon([(720, 0), (1024, 0), (1024, 360), (650, 300)], fill=(214, 162, 67, 54))
    d.polygon([(0, 260), (310, 340), (360, 500), (0, 500)], fill=(155, 24, 18, 44))

    logo = Image.open(ASSETS / "ui" / "home_logo_samguk.png").convert("RGBA")
    logo.thumbnail((470, 150), Image.Resampling.LANCZOS)
    base.alpha_composite(logo, (54, 42))

    raw_stage = Image.open(RAW / battle_raw)
    paste_round(base, raw_stage, (620, 26, 320, 448), 36)
    d.rounded_rectangle((610, 16, 950, 484), radius=46, outline=(255, 214, 109, 210), width=4)

    title_font = font(54, True)
    sub_font = font(27, True)
    text_with_stroke(d, (58, 210), "여섯 성이 부딪히는 전장", title_font, (255, 241, 194), sw=4)
    d.text((60, 286), "장수 수집 · 포메이션 · 실시간 공성 전략", font=sub_font, fill=(255, 226, 154), stroke_width=2, stroke_fill=(30, 12, 4))
    d.rounded_rectangle((58, 354, 500, 424), radius=20, fill=(188, 30, 22, 235), outline=(255, 214, 109, 210), width=3)
    d.text((94, 371), "손가락 삼국지", font=font(34, True), fill=(255, 244, 200), stroke_width=2, stroke_fill=(80, 12, 6))
    base.convert("RGB").save(OUT / "feature_graphic_1024x500.png", quality=95)


def icon():
    src = Image.open(ASSETS / "icons" / "android_launcher_icon_1024.png").convert("RGBA")
    img = cover(src, (512, 512)).convert("RGBA")
    mask = rounded_mask((512, 512), 110)
    out = Image.new("RGBA", (512, 512), (0, 0, 0, 0))
    out.paste(img, (0, 0), mask)
    out.save(OUT / "icon_512.png")


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    for old in OUT.glob("screenshot_*.png"):
        old.unlink()
    icon()
    feature_graphic()
    battle_raw = raw_name("raw_battle_manual.png", "raw_battle.png")
    screenshot("screenshot_01_six_castle_war.png", battle_raw, "대규모 전쟁", "복잡한 성 전투\n실시간 공성", "다수의 성과 병력이 동시에 움직이는 전략 전투")
    screenshot("screenshot_02_legend_aura.png", "raw_aura.png", "전설 장수", "아우라가 터지는\n무장 카드", "별 등급과 전투력으로 명장을 수집")
    enhance_collage()
    screenshot("screenshot_04_fast_sortie.png", "raw_deploy.png", "10인 편성", "선봉과 포메이션을\n즉시 조정", "자동 편성과 직접 선택을 모두 지원")
    screenshot("screenshot_05_recruit_prisoner.png", "raw_prisoner.png", "포로 등용", "적장을 설득해\n내 장수로", "전투 후 포획한 명장을 영입")
    screenshot("screenshot_06_upgrade_power.png", "raw_upgrade.png", "전투력 관리", "성·병력 능력을\n꾸준히 강화", "골드 투자로 다음 전장을 준비")
    screenshot("screenshot_07_chapter_map.png", "raw_stage_ch1.png", "챕터 정복", "스테이지를 골라\n천하로 진군", "관문을 따라 영토를 넓히는 진행")


if __name__ == "__main__":
    main()
