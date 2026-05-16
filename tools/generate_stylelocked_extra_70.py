from __future__ import annotations

import hashlib
import json
import math
import colorsys
from dataclasses import dataclass
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont


ROOT = Path(__file__).resolve().parents[1]
BASE_DIR = ROOT / "assets" / "generals" / "busts"
OUT_DIR = ROOT / "assets" / "generals" / "busts_extra_70"
TMP_DIR = ROOT / "tmp" / "extra_generals_70_stylelocked"
OUT_DIR.mkdir(parents=True, exist_ok=True)
TMP_DIR.mkdir(parents=True, exist_ok=True)


@dataclass(frozen=True)
class General:
    slug: str
    ko: str
    base: str
    palette: str
    emblem: str


ROSTER: list[General] = [
    General("hua_xiong", "화웅", "zhang_fei", "crimson_black", "flame"),
    General("gao_shun", "고순", "zhang_liao", "steel_blue", "spear"),
    General("chen_gong", "진궁", "guo_jia", "violet_black", "moon"),
    General("li_ru", "이유", "sima_yi", "dark_gold", "diamond"),
    General("li_jue", "이각", "yan_liang", "crimson_black", "axe"),
    General("guo_si", "곽사", "wen_chou", "dark_red", "spike"),
    General("zhang_ji", "장제", "xu_huang", "bronze_blue", "shield"),
    General("zhang_xiu", "장수", "zhao_yun", "teal_gold", "spear"),
    General("jia_xu", "가후", "pang_tong", "violet_black", "moon"),
    General("xun_yu", "순욱", "zhuge_liang", "white_blue", "fan"),
    General("xun_you", "순유", "guo_jia", "blue_gold", "scroll"),
    General("cheng_yu", "정욱", "sima_yi", "dark_gold", "diamond"),
    General("cao_ren", "조인", "xiahou_dun", "blue_gold", "shield"),
    General("cao_hong", "조홍", "xu_huang", "steel_blue", "spear"),
    General("cao_pi", "조비", "sun_quan", "red_gold", "diamond"),
    General("cao_zhang", "조창", "ma_chao", "gold_white", "tiger"),
    General("cao_zhi", "조식", "zhou_yu", "white_red", "scroll"),
    General("cao_ang", "조앙", "zhao_yun", "white_blue", "spear"),
    General("cao_chun", "조순", "zhang_liao", "steel_blue", "shield"),
    General("cao_rui", "조예", "yuan_shao", "white_gold", "diamond"),
    General("xiahou_yuan", "하후연", "huang_zhong", "gold_brown", "bow"),
    General("xiahou_ba", "하후패", "ma_chao", "white_blue", "spear"),
    General("man_chong", "만총", "xu_huang", "bronze_blue", "shield"),
    General("wang_shuang", "왕쌍", "xu_chu", "dark_gold", "spike"),
    General("deng_ai", "등애", "zhang_liao", "steel_blue", "mountain"),
    General("zhong_hui", "종회", "guo_jia", "violet_black", "diamond"),
    General("wen_yang", "문앙", "zhao_yun", "white_blue", "spear"),
    General("guanqiu_jian", "관구검", "xiahou_dun", "blue_gold", "shield"),
    General("wen_qin", "문흠", "yan_liang", "crimson_black", "axe"),
    General("wei_yan", "위연", "zhang_fei", "dark_red", "fang"),
    General("jiang_wei", "강유", "zhao_yun", "white_blue", "spear"),
    General("ma_dai", "마대", "ma_chao", "white_blue", "horse"),
    General("ma_su", "마속", "lu_xun", "teal_gold", "scroll"),
    General("fa_zheng", "법정", "sima_yi", "violet_black", "moon"),
    General("ma_liang", "마량", "zhuge_liang", "white_blue", "fan"),
    General("jian_yong", "간옹", "liu_bei", "green_gold", "scroll"),
    General("mi_zhu", "미축", "sun_quan", "white_gold", "diamond"),
    General("guan_ping", "관평", "guan_yu", "green_gold", "spear"),
    General("guan_xing", "관흥", "guan_yu", "teal_gold", "spear"),
    General("zhang_bao", "장포", "zhang_fei", "dark_red", "fang"),
    General("zhou_cang", "주창", "wen_chou", "dark_red", "axe"),
    General("liao_hua", "요화", "liu_bei", "green_gold", "shield"),
    General("wang_ping", "왕평", "zhang_liao", "steel_blue", "mountain"),
    General("yan_yan", "엄안", "huang_zhong", "gold_brown", "bow"),
    General("wu_yi", "오의", "zhao_yun", "blue_gold", "spear"),
    General("li_yan", "이엄", "xu_huang", "bronze_blue", "shield"),
    General("meng_da", "맹달", "sun_ce", "red_gold", "spear"),
    General("huang_quan", "황권", "zhuge_liang", "white_gold", "scroll"),
    General("liu_feng", "유봉", "liu_bei", "green_gold", "sword"),
    General("sun_jian", "손견", "sun_ce", "red_gold", "tiger"),
    General("lu_su", "노숙", "zhou_yu", "white_red", "fan"),
    General("zhang_zhao", "장소", "zhuge_liang", "white_gold", "scroll"),
    General("zhang_hong", "장굉", "guo_jia", "blue_gold", "scroll"),
    General("cheng_pu", "정보", "huang_gai", "gold_brown", "shield"),
    General("han_dang", "한당", "taishi_ci", "blue_gold", "bow"),
    General("zu_mao", "조무", "sun_ce", "red_gold", "sword"),
    General("ling_tong", "능통", "gan_ning", "teal_gold", "spear"),
    General("zhou_tai", "주태", "taishi_ci", "dark_red", "shield"),
    General("ding_feng", "정봉", "xu_huang", "steel_blue", "axe"),
    General("xu_sheng", "서성", "sun_ce", "red_gold", "spear"),
    General("zhu_huan", "주환", "sun_quan", "red_gold", "shield"),
    General("zhu_zhi", "주치", "huang_gai", "gold_brown", "shield"),
    General("zhu_ran", "주연", "lu_xun", "teal_gold", "flame"),
    General("lu_kang", "육항", "lu_xun", "teal_gold", "scroll"),
    General("zhang_ren", "장임", "huang_zhong", "gold_brown", "bow"),
    General("ji_ling", "기령", "yan_liang", "crimson_black", "halberd"),
    General("gongsun_zan", "공손찬", "ma_chao", "white_blue", "horse"),
    General("ma_teng", "마등", "ma_chao", "gold_white", "horse"),
    General("han_sui", "한수", "yuan_shao", "gold_brown", "moon"),
    General("zhang_jiao", "장각", "pang_tong", "yellow_tao", "sun"),
]


PALETTES: dict[str, dict[str, tuple[int, int, int]]] = {
    "blue_gold": {"blue": (34, 73, 126), "red": (142, 44, 32), "green": (42, 92, 78), "white": (205, 210, 214)},
    "steel_blue": {"blue": (52, 80, 116), "red": (104, 40, 38), "green": (50, 82, 82), "white": (188, 195, 200)},
    "bronze_blue": {"blue": (48, 67, 94), "red": (126, 59, 36), "green": (69, 91, 73), "white": (188, 181, 162)},
    "crimson_black": {"blue": (42, 43, 55), "red": (126, 34, 29), "green": (70, 67, 47), "white": (172, 164, 150)},
    "dark_red": {"blue": (55, 45, 52), "red": (150, 41, 30), "green": (80, 70, 48), "white": (181, 170, 152)},
    "red_gold": {"blue": (54, 51, 70), "red": (165, 45, 32), "green": (84, 77, 47), "white": (213, 203, 172)},
    "violet_black": {"blue": (62, 47, 103), "red": (111, 44, 84), "green": (56, 70, 78), "white": (183, 178, 198)},
    "dark_gold": {"blue": (57, 55, 68), "red": (105, 55, 35), "green": (79, 75, 45), "white": (184, 174, 136)},
    "white_blue": {"blue": (55, 111, 177), "red": (142, 42, 35), "green": (60, 110, 95), "white": (226, 230, 231)},
    "white_gold": {"blue": (71, 90, 118), "red": (145, 52, 34), "green": (90, 98, 70), "white": (228, 221, 199)},
    "gold_white": {"blue": (80, 96, 118), "red": (146, 62, 35), "green": (95, 98, 61), "white": (217, 200, 145)},
    "green_gold": {"blue": (45, 80, 82), "red": (139, 44, 33), "green": (55, 113, 76), "white": (204, 211, 187)},
    "teal_gold": {"blue": (40, 110, 116), "red": (147, 49, 36), "green": (44, 125, 93), "white": (202, 216, 203)},
    "gold_brown": {"blue": (76, 65, 55), "red": (134, 58, 33), "green": (94, 86, 48), "white": (203, 184, 130)},
    "white_red": {"blue": (70, 77, 105), "red": (174, 52, 38), "green": (85, 93, 73), "white": (229, 218, 198)},
    "yellow_tao": {"blue": (79, 70, 53), "red": (151, 60, 31), "green": (106, 92, 44), "white": (218, 188, 83)},
}


def stable_int(text: str) -> int:
    return int(hashlib.sha256(text.encode("utf-8")).hexdigest()[:12], 16)


def load_base(slug: str) -> Image.Image:
    return Image.open(BASE_DIR / f"{slug}.png").convert("RGBA")


def classify(r: int, g: int, b: int) -> str | None:
    # Protect the production set's most important invariants: skin/face/hands
    # and gold hardware. The previous pass let these fall into "red", which made
    # faces muddy and erased the native gold-trim language.
    h, s, v = colorsys.rgb_to_hsv(r / 255, g / 255, b / 255)
    hue = h * 360
    lum = 0.299 * r + 0.587 * g + 0.114 * b
    if 12 <= hue <= 42 and 0.18 <= s <= 0.78 and 0.28 <= v <= 0.96 and r > g > b and lum > 78:
        return None
    if r > 120 and 58 < g < 190 and 28 < b < 150 and r > g * 1.03 and g > b * 1.05 and lum > 78:
        return None
    if 32 <= hue <= 56 and s > 0.32 and v > 0.28 and r > g > b:
        return None

    if b > 72 and b > r * 1.08 and b > g * 0.88:
        return "blue"
    if r > 82 and r > g * 1.16 and r > b * 1.12 and g < 120:
        return "red"
    if g > 68 and g > r * 0.82 and g > b * 0.82 and (g - min(r, b)) > 16:
        return "green"
    if r > 145 and g > 135 and b > 115 and abs(r - g) < 70 and abs(g - b) < 80:
        return "white"
    return None


def recolor(img: Image.Image, palette: dict[str, tuple[int, int, int]], seed: int) -> Image.Image:
    out = img.copy()
    px = out.load()
    # Slightly vary strength, but keep the original render strongly intact.
    strength_base = 0.42 + (seed % 11) * 0.012
    for y in range(out.height):
        for x in range(out.width):
            r, g, b, a = px[x, y]
            if a < 8:
                continue
            kind = classify(r, g, b)
            if not kind:
                continue
            tr, tg, tb = palette[kind]
            lum = max(0.22, min(1.28, (0.299 * r + 0.587 * g + 0.114 * b) / 150))
            strength = strength_base
            if kind == "white":
                strength *= 0.62
            nr = int(r * (1 - strength) + min(255, tr * lum) * strength)
            ng = int(g * (1 - strength) + min(255, tg * lum) * strength)
            nb = int(b * (1 - strength) + min(255, tb * lum) * strength)
            px[x, y] = (nr, ng, nb, a)
    return out


def alpha_bbox(img: Image.Image) -> tuple[int, int, int, int]:
    return img.getchannel("A").getbbox() or (0, 0, img.width, img.height)


def draw_emblem(draw: ImageDraw.ImageDraw, center: tuple[int, int], emblem: str, seed: int, radius: int) -> None:
    cx, cy = center
    gold = (236, 174, 45, 245)
    gold_hi = (255, 224, 95, 210)
    dark = (59, 42, 29, 235)
    red = (155, 35, 28, 230)
    blue = (38, 90, 150, 230)
    draw.ellipse((cx - radius, cy - radius, cx + radius, cy + radius), fill=dark, outline=gold, width=4)
    r = radius - 10
    if emblem in {"spear", "halberd"}:
        draw.line((cx, cy - r, cx, cy + r), fill=gold, width=5)
        draw.polygon([(cx, cy - r - 7), (cx + 8, cy - r + 8), (cx, cy - r + 4), (cx - 8, cy - r + 8)], fill=gold_hi)
    elif emblem in {"axe", "spike", "fang"}:
        draw.polygon([(cx - r, cy - 4), (cx + 4, cy - r), (cx + r, cy - 2), (cx + 3, cy + r)], fill=gold)
        draw.line((cx - r + 3, cy - 3, cx + r - 3, cy - 1), fill=gold_hi, width=2)
    elif emblem == "shield":
        draw.polygon([(cx, cy - r), (cx + r, cy - 3), (cx + r // 2, cy + r), (cx, cy + r + 4), (cx - r // 2, cy + r), (cx - r, cy - 3)], fill=gold)
        draw.polygon([(cx, cy - r + 7), (cx + r - 8, cy), (cx, cy + r - 4), (cx - r + 8, cy)], fill=blue)
    elif emblem == "bow":
        draw.arc((cx - r, cy - r, cx + r, cy + r), 105, 255, fill=gold, width=5)
        draw.line((cx - r // 2, cy - r + 2, cx - r // 2, cy + r - 2), fill=gold_hi, width=2)
    elif emblem == "fan":
        for i in range(-2, 3):
            angle = -70 + i * 35
            ex = cx + int(math.cos(math.radians(angle)) * r)
            ey = cy + int(math.sin(math.radians(angle)) * r)
            draw.polygon([(cx, cy + r // 2), (ex - 5, ey), (ex + 5, ey)], fill=(232, 221, 193, 235), outline=gold)
    elif emblem == "scroll":
        draw.rounded_rectangle((cx - r, cy - r // 2, cx + r, cy + r // 2), radius=6, fill=(224, 203, 151, 235), outline=gold, width=3)
        draw.line((cx - r + 8, cy, cx + r - 8, cy), fill=dark, width=2)
    elif emblem in {"moon", "sun"}:
        if emblem == "sun":
            for a in range(0, 360, 45):
                ex = cx + int(math.cos(math.radians(a)) * (r + 4))
                ey = cy + int(math.sin(math.radians(a)) * (r + 4))
                draw.line((cx, cy, ex, ey), fill=gold_hi, width=3)
            draw.ellipse((cx - r // 2, cy - r // 2, cx + r // 2, cy + r // 2), fill=gold)
        else:
            draw.ellipse((cx - r, cy - r, cx + r, cy + r), fill=gold)
            draw.ellipse((cx - r // 2, cy - r, cx + r + 5, cy + r), fill=dark)
    elif emblem == "horse":
        draw.polygon([(cx - r, cy + r // 3), (cx - r // 2, cy - r), (cx + r, cy - r // 4), (cx + r // 4, cy + r)], fill=gold)
    elif emblem == "tiger":
        draw.polygon([(cx, cy - r), (cx + r, cy - 2), (cx + r // 3, cy + r), (cx, cy + r // 2), (cx - r // 3, cy + r), (cx - r, cy - 2)], fill=gold)
        draw.ellipse((cx - 4, cy - 1, cx + 4, cy + 7), fill=red)
    elif emblem == "flame":
        pts = [(cx, cy - r), (cx + r // 2, cy - 3), (cx + r // 5, cy - 3), (cx + r - 2, cy + r), (cx, cy + r // 2), (cx - r + 2, cy + r), (cx - r // 5, cy - 3), (cx - r // 2, cy - 3)]
        draw.polygon(pts, fill=gold)
        draw.line(pts + [pts[0]], fill=gold_hi, width=2)
    elif emblem == "mountain":
        draw.polygon([(cx - r, cy + r), (cx - r // 2, cy - r // 2), (cx, cy + r // 4), (cx + r // 2, cy - r), (cx + r, cy + r)], fill=gold)
    else:
        draw.polygon([(cx, cy - r), (cx + r, cy), (cx, cy + r), (cx - r, cy)], fill=gold)
        draw.polygon([(cx, cy - r // 2), (cx + r // 2, cy), (cx, cy + r // 2), (cx - r // 2, cy)], fill=red)


def cover_textish_badges(img: Image.Image, seed: int, emblem: str) -> Image.Image:
    # Keep the existing folder style. Earlier large pasted emblems made the batch
    # feel less native, so this pass uses only tiny integrated accents.
    out = img.copy()
    draw = ImageDraw.Draw(out, "RGBA")
    x0, y0, x1, y1 = alpha_bbox(out)
    w, h = x1 - x0, y1 - y0
    # Small forehead gem for some helmeted characters, placed like the source set's
    # existing jewel language rather than as a new badge.
    if seed % 5 in {0, 2}:
        cx = int(x0 + w * (0.50 + ((seed % 7) - 3) * 0.004))
        cy = int(y0 + h * 0.09)
        r = int(max(10, min(17, w * 0.026)))
        draw.polygon([(cx, cy - r), (cx + r, cy), (cx, cy + r), (cx - r, cy)], fill=(139, 83, 22, 235), outline=(245, 184, 52, 245))
        inner = [(cx, cy - r + 6), (cx + r - 6, cy), (cx, cy + r - 6), (cx - r + 6, cy)]
        jewel = (160 + seed % 50, 30 + seed % 35, 30 + seed % 20, 235)
        draw.polygon(inner, fill=jewel, outline=(255, 218, 93, 190))
    # A couple of tiny tassel/rivet accents on some variants. These are small
    # enough that they read as the original armor hardware.
    if seed % 6 == 0:
        cx = int(x0 + w * 0.50)
        cy = int(y0 + h * 0.49)
        for dx in (-11, 11):
            draw.ellipse((cx + dx - 4, cy - 4, cx + dx + 4, cy + 4), fill=(225, 162, 43, 220), outline=(112, 70, 22, 190), width=1)
    return out


def adjust_layout(img: Image.Image, seed: int) -> Image.Image:
    # Tiny translation/scale only; enough to avoid clones, small enough to keep exact production grammar.
    x0, y0, x1, y1 = alpha_bbox(img)
    crop = img.crop((x0, y0, x1, y1))
    scale = 0.985 + (seed % 7) * 0.005
    nw, nh = int(crop.width * scale), int(crop.height * scale)
    crop = crop.resize((nw, nh), Image.Resampling.LANCZOS)
    out = Image.new("RGBA", (640, 768), (0, 0, 0, 0))
    dx = ((seed % 9) - 4) * 2
    dy = ((seed // 9) % 5 - 2) * 2
    x = (640 - nw) // 2 + dx
    y = 768 - nh - max(14, 768 - y1) + dy
    x = max(-4, min(640 - nw + 4, x))
    y = max(0, min(768 - nh, y))
    out.alpha_composite(crop, (x, y))
    return out


def make_general(g: General) -> Image.Image:
    seed = stable_int(g.slug)
    img = load_base(g.base)
    img = recolor(img, PALETTES[g.palette], seed)
    img = cover_textish_badges(img, seed, g.emblem)
    img = adjust_layout(img, seed)
    return img


def build_gallery() -> None:
    rows = "\n".join(
        f"  ['{g.slug}', '{g.ko}', '{g.base}']," for g in ROSTER
    )
    html = f"""<!DOCTYPE html>
<html lang="ko">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>추가 장수 70명 전신 후보</title>
<style>
  * {{ box-sizing: border-box; }}
  body {{
    margin: 0;
    padding: 28px;
    background: #17110b;
    color: #f7d56e;
    font-family: -apple-system, BlinkMacSystemFont, "Apple SD Gothic Neo", sans-serif;
  }}
  h1 {{ margin: 0 0 8px; font-size: 30px; }}
  .sub {{ margin: 0 0 22px; color: #c5a86b; font-size: 15px; }}
  .toolbar {{
    position: sticky; top: 0; z-index: 2;
    display: flex; gap: 10px; align-items: center;
    padding: 12px 0 16px;
    background: linear-gradient(180deg, #17110b 70%, rgba(23,17,11,0));
  }}
  input {{
    width: min(420px, 100%); height: 40px; padding: 0 14px;
    border: 1px solid #7b5724; border-radius: 8px;
    background: #24190f; color: #ffe188; font-size: 15px; outline: none;
  }}
  .count, .audit {{ color: #a98a50; font-size: 14px; white-space: nowrap; }}
  .audit {{ margin-left: auto; font-weight: 800; }}
  .audit.ok {{ color: #8fd48a; }}
  .audit.bad {{ color: #ff8f75; }}
  .grid {{
    display: grid;
    grid-template-columns: repeat(auto-fill, minmax(250px, 1fr));
    gap: 16px;
  }}
  .card {{
    min-width: 0;
    border: 1px solid #79551f;
    border-radius: 8px;
    overflow: hidden;
    background: linear-gradient(180deg, #24190f, #110b07);
  }}
  .name {{
    display: flex;
    justify-content: space-between;
    gap: 10px;
    align-items: baseline;
    padding: 11px 12px;
    border-bottom: 1px solid #664719;
    color: #ffe188;
    font-size: 17px;
    font-weight: 800;
  }}
  .name small {{
    min-width: 0;
    color: #a98a50;
    font-size: 12px;
    font-weight: 700;
    text-align: right;
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
  }}
  .art {{
    height: 330px;
    display: flex;
    align-items: flex-end;
    justify-content: center;
    padding: 14px;
    background:
      linear-gradient(90deg, rgba(255,255,255,0.035) 1px, transparent 1px),
      linear-gradient(rgba(255,255,255,0.035) 1px, transparent 1px),
      radial-gradient(circle at 50% 18%, rgba(255,212,91,0.16), transparent 44%),
      #21170e;
    background-size: 28px 28px, 28px 28px, 100% 100%, 100% 100%;
  }}
  img {{
    display: block;
    max-width: 100%;
    max-height: 100%;
    object-fit: contain;
    filter: drop-shadow(0 14px 16px rgba(0,0,0,0.62));
  }}
  .file {{
    padding: 8px 10px 10px;
    border-top: 1px solid #3d2a12;
    color: #f7d56e;
    font-size: 12px;
    word-break: break-all;
  }}
  .base {{
    color: #a98a50;
    font-size: 11px;
  }}
  .missing .art {{
    align-items: center;
    color: #ff9a7a;
    font-size: 13px;
    font-weight: 800;
  }}
  @media (max-width: 720px) {{
    body {{ padding: 18px; }}
    h1 {{ font-size: 24px; }}
    .toolbar {{ align-items: flex-start; flex-direction: column; }}
    .audit {{ margin-left: 0; }}
    .grid {{ grid-template-columns: repeat(auto-fill, minmax(170px, 1fr)); }}
    .art {{ height: 260px; }}
  }}
</style>
</head>
<body>
<h1>추가 장수 70명 전신 후보</h1>
<p class="sub">기존 busts 에셋 문법을 유지한 스타일 잠금 후보입니다. 기존 34명 파일명과 중복되지 않게 생성했습니다.</p>
<div class="toolbar">
  <input id="search" type="search" placeholder="이름 또는 파일명 검색">
  <div class="count" id="count"></div>
  <div class="audit" id="audit">검수 중...</div>
</div>
<main class="grid" id="grid"></main>
<script>
const generals = [
{rows}
];
const grid = document.getElementById('grid');
const count = document.getElementById('count');
const search = document.getElementById('search');
const audit = document.getElementById('audit');
let loaded = 0;
let failed = 0;

function card([id, name, base]) {{
  const file = `${{id}}.png`;
  const card = document.createElement('section');
  card.className = 'card';
  card.dataset.key = `${{id}} ${{name}} ${{base}}`.toLowerCase();
  card.innerHTML = `
    <div class="name">
      <span>${{name}}</span>
      <small>${{file}}</small>
    </div>
    <div class="art"><img src="assets/generals/busts_extra_70/${{file}}" alt="${{name}} 전신"></div>
    <div class="file">busts_extra_70/${{file}} <span class="base">base: ${{base}}</span></div>
  `;
  return card;
}}

const cards = generals.map(card);
cards.forEach(card => grid.appendChild(card));

function updateAudit() {{
  const checked = loaded + failed;
  audit.textContent = failed
    ? `이미지 ${{checked}}/${{generals.length}}, 누락 ${{failed}}`
    : `이미지 ${{checked}}/${{generals.length}}`;
  audit.className = `audit ${{checked === generals.length && !failed ? 'ok' : failed ? 'bad' : ''}}`;
}}

grid.querySelectorAll('img').forEach(img => {{
  img.addEventListener('load', () => {{ loaded++; updateAudit(); }});
  img.addEventListener('error', () => {{
    failed++;
    const card = img.closest('.card');
    card.classList.add('missing');
    img.closest('.art').textContent = '이미지 누락';
    updateAudit();
  }});
}});
updateAudit();

function filterCards() {{
  const q = search.value.trim().toLowerCase();
  let shown = 0;
  cards.forEach(card => {{
    const ok = !q || card.dataset.key.includes(q);
    card.style.display = ok ? '' : 'none';
    if (ok) shown++;
  }});
  count.textContent = `${{shown}} / ${{generals.length}}`;
}}
search.addEventListener('input', filterCards);
filterCards();
</script>
</body>
</html>
"""
    (ROOT / "extra_70_busts_gallery.html").write_text(html, encoding="utf-8")


def make_contact_sheet() -> None:
    card_w, art_h, label_h = 250, 310, 40
    cols = 10
    rows = math.ceil(len(ROSTER) / cols)
    sheet = Image.new("RGBA", (cols * card_w, rows * (art_h + label_h)), (18, 11, 7, 255))
    draw = ImageDraw.Draw(sheet, "RGBA")
    try:
        font_big = ImageFont.truetype("/System/Library/Fonts/AppleSDGothicNeo.ttc", 20)
        font_small = ImageFont.truetype("/System/Library/Fonts/AppleSDGothicNeo.ttc", 13)
    except OSError:
        font_big = ImageFont.load_default()
        font_small = ImageFont.load_default()
    for idx, g in enumerate(ROSTER):
        col = idx % cols
        row = idx // cols
        x0 = col * card_w
        y0 = row * (art_h + label_h)
        bg = Image.new("RGBA", (card_w, art_h), (31, 21, 12, 255))
        d = ImageDraw.Draw(bg, "RGBA")
        for gx in range(0, card_w, 28):
            d.line((gx, 0, gx, art_h), fill=(255, 255, 255, 12), width=1)
        for gy in range(0, art_h, 28):
            d.line((0, gy, card_w, gy), fill=(255, 255, 255, 12), width=1)
        img = Image.open(OUT_DIR / f"{g.slug}.png").convert("RGBA")
        bbox = alpha_bbox(img)
        crop = img.crop(bbox)
        crop.thumbnail((card_w - 18, art_h - 12), Image.Resampling.LANCZOS)
        bg.alpha_composite(crop, ((card_w - crop.width) // 2, art_h - crop.height - 4))
        sheet.alpha_composite(bg, (x0, y0))
        draw.rectangle((x0, y0 + art_h, x0 + card_w, y0 + art_h + label_h), fill=(18, 10, 6, 255))
        draw.text((x0 + 10, y0 + art_h + 8), g.ko, fill=(255, 226, 116, 255), font=font_big)
        draw.text((x0 + 72, y0 + art_h + 13), f"{g.slug}.png", fill=(174, 139, 78, 255), font=font_small)
        draw.rectangle((x0, y0, x0 + card_w, y0 + art_h + label_h), outline=(128, 86, 23, 255), width=1)
    sheet.save(TMP_DIR / "extra_70_contact_sheet.png")


def main() -> None:
    existing = {path.stem for path in BASE_DIR.glob("*.png")}
    duplicates = sorted({g.slug for g in ROSTER} & existing)
    if duplicates:
        raise SystemExit(f"Roster duplicates existing busts: {duplicates}")
    if len({g.slug for g in ROSTER}) != 70 or len(ROSTER) != 70:
        raise SystemExit("Roster must contain exactly 70 unique generals")
    manifest = []
    for g in ROSTER:
        img = make_general(g)
        out = OUT_DIR / f"{g.slug}.png"
        img.save(out)
        manifest.append({"slug": g.slug, "ko": g.ko, "base": g.base, "palette": g.palette, "emblem": g.emblem})
    (OUT_DIR / "manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    build_gallery()
    make_contact_sheet()
    print(f"generated {len(ROSTER)} busts -> {OUT_DIR}")
    print(ROOT / "extra_70_busts_gallery.html")
    print(TMP_DIR / "extra_70_contact_sheet.png")


if __name__ == "__main__":
    main()
