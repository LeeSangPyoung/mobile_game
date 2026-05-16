from __future__ import annotations

import json
import math
import re
import sys
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))

import colorfit_extra_70 as colorfit_mod
import generate_stylelocked_extra_70 as basegen


RAW_DIR = ROOT / "assets" / "generals" / "busts_extra_100"
OUT_DIR = ROOT / "assets" / "generals" / "busts_extra_100_colorfit"
TMP_DIR = ROOT / "tmp" / "extra_generals_100_stylelocked"
RAW_DIR.mkdir(parents=True, exist_ok=True)
OUT_DIR.mkdir(parents=True, exist_ok=True)
TMP_DIR.mkdir(parents=True, exist_ok=True)


General = basegen.General


ROSTER: list[General] = [
    # Wei / Jin side
    General("cao_zhen", "조진", "cao_cao", "blue_gold", "shield"),
    General("cao_xiu", "조휴", "xiahou_dun", "steel_blue", "sword"),
    General("cao_shuang", "조상", "yuan_shao", "white_gold", "diamond"),
    General("cao_fang", "조방", "sun_quan", "white_blue", "diamond"),
    General("cao_mao", "조모", "sun_ce", "red_gold", "sword"),
    General("cao_huan", "조환", "liu_bei", "green_gold", "scroll"),
    General("cao_anmin", "조안민", "cao_xing", "crimson_black", "spear"),
    General("cao_de", "조덕", "cao_cao", "dark_gold", "diamond"),
    General("cao_shuo", "조삭", "sun_quan", "blue_gold", "scroll"),
    General("cao_yu", "조우", "yuan_shao", "white_gold", "fan"),
    General("li_tong", "이통", "taishi_ci", "steel_blue", "spear"),
    General("lu_qian", "여건", "zhang_liao", "blue_gold", "shield"),
    General("zang_ba", "장패", "zhang_fei", "dark_red", "axe"),
    General("zhu_ling", "주령", "xu_huang", "steel_blue", "spear"),
    General("han_hao", "한호", "dian_wei", "crimson_black", "shield"),
    General("shi_huan", "사환", "xu_chu", "dark_gold", "spike"),
    General("lu_zhao", "노초", "xu_huang", "bronze_blue", "spear"),
    General("wang_bi", "왕필", "cao_cao", "crimson_black", "sword"),
    General("liu_ye", "유엽", "guo_jia", "white_blue", "scroll"),
    General("kuai_yue", "괴월", "zhuge_liang", "white_gold", "fan"),
    General("kuai_liang", "괴량", "zhuge_liang", "green_gold", "scroll"),
    General("jia_kui", "가규", "sima_yi", "dark_gold", "shield"),
    General("chen_qun", "진군", "guo_jia", "violet_black", "scroll"),
    General("hua_xin", "화흠", "yuan_shao", "white_gold", "diamond"),
    General("wang_lang", "왕랑", "yuan_shao", "gold_brown", "scroll"),
    General("zhong_yao", "종요", "sima_yi", "dark_gold", "diamond"),
    General("dong_zhao", "동소", "liu_bei", "green_gold", "scroll"),
    General("xin_pi", "신비", "guo_jia", "blue_gold", "scroll"),
    General("chen_tai", "진태", "zhang_liao", "steel_blue", "spear"),
    General("guo_huai", "곽회", "zhang_liao", "steel_blue", "mountain"),
    General("sun_li", "손례", "xu_huang", "bronze_blue", "shield"),
    General("niu_jin", "우금", "xu_chu", "dark_gold", "spike"),
    General("wen_pin", "문빙", "xu_huang", "blue_gold", "shield"),
    General("jiang_ji", "장제(위)", "sima_yi", "dark_gold", "scroll"),
    General("hu_zhi", "호질", "guo_jia", "steel_blue", "mountain"),
    General("zhuge_dan", "제갈탄", "zhuge_liang", "white_blue", "diamond"),
    General("sima_shi", "사마사", "sima_yi", "violet_black", "diamond"),
    General("sima_zhao", "사마소", "sima_yi", "dark_gold", "diamond"),
    General("du_yu", "두예", "zhuge_liang", "white_blue", "scroll"),
    General("yang_hu", "양호", "zhao_yun", "white_blue", "spear"),

    # Shu side
    General("zhang_song", "장송", "pang_tong", "violet_black", "scroll"),
    General("liu_zhang", "유장", "liu_bei", "green_gold", "scroll"),
    General("liu_yan", "유언", "liu_bei", "gold_brown", "scroll"),
    General("zhang_yi", "장익", "zhao_yun", "blue_gold", "spear"),
    General("fei_yi", "비의", "zhuge_liang", "white_blue", "fan"),
    General("dong_yun", "동윤", "guo_jia", "blue_gold", "scroll"),
    General("jiang_wan", "장완", "zhuge_liang", "green_gold", "scroll"),
    General("huang_hao", "황호", "pang_tong", "yellow_tao", "moon"),
    General("chen_dao", "진도", "zhao_yun", "white_blue", "spear"),
    General("wang_lian", "왕련", "liu_bei", "green_gold", "scroll"),
    General("qiao_zhou", "초주", "zhuge_liang", "white_gold", "fan"),
    General("yi_ji", "이적", "liu_bei", "green_gold", "scroll"),
    General("sun_qian", "손건", "liu_bei", "white_gold", "scroll"),
    General("mi_fang", "미방", "sun_quan", "red_gold", "shield"),
    General("fu_shi_ren", "부사인", "taishi_ci", "dark_red", "sword"),
    General("wu_ban", "오반", "ma_chao", "white_blue", "spear"),
    General("wu_lan", "오란", "zhang_fei", "dark_red", "axe"),
    General("lei_tong", "뇌동", "zhang_fei", "crimson_black", "spear"),
    General("zhang_ni", "장억", "zhao_yun", "blue_gold", "spear"),
    General("gao_xiang", "고상", "huang_zhong", "gold_brown", "bow"),
    General("ma_zhong_shu", "마충(촉)", "zhao_yun", "blue_gold", "spear"),
    General("wang_fu", "왕보", "guan_yu", "green_gold", "scroll"),
    General("zhao_lei", "조뢰", "guan_yu", "green_gold", "spear"),
    General("huang_chengyan", "황승언", "zhuge_liang", "white_gold", "fan"),
    General("li_hui", "이회", "liu_bei", "green_gold", "scroll"),
    General("chen_shi", "진식", "zhang_fei", "dark_red", "shield"),
    General("xiang_chong", "향충", "zhao_yun", "white_blue", "shield"),
    General("xiang_lang", "향랑", "zhuge_liang", "white_blue", "scroll"),
    General("liu_shan", "유선", "liu_bei", "green_gold", "diamond"),
    General("yan_yu", "염우", "ma_chao", "gold_brown", "spear"),

    # Wu side
    General("lu_meng", "여몽", "gan_ning", "teal_gold", "spear"),
    General("zhuge_jin", "제갈근", "zhuge_liang", "white_blue", "fan"),
    General("zhuge_ke", "제갈각", "lu_xun", "teal_gold", "scroll"),
    General("quan_cong", "전종", "sun_quan", "blue_gold", "spear"),
    General("bu_zhi", "보즐", "zhou_yu", "white_red", "scroll"),
    General("kan_ze", "감택", "guo_jia", "blue_gold", "scroll"),
    General("gu_yong", "고옹", "zhuge_liang", "white_gold", "scroll"),
    General("zhang_wen_wu", "장온", "zhou_yu", "white_red", "fan"),
    General("sun_shao", "손소", "sun_quan", "blue_gold", "sword"),
    General("sun_xiu", "손휴", "sun_quan", "white_blue", "diamond"),
    General("sun_liang", "손량", "sun_quan", "white_gold", "diamond"),
    General("sun_hao", "손호", "sun_ce", "red_gold", "sword"),
    General("sun_deng", "손등", "sun_quan", "white_blue", "diamond"),
    General("sun_he", "손화", "sun_quan", "red_gold", "scroll"),
    General("sun_ben", "손분", "sun_ce", "red_gold", "spear"),
    General("sun_fu", "손보", "sun_ce", "red_gold", "sword"),
    General("sun_yi", "손익", "sun_ce", "red_gold", "spear"),
    General("sun_kuang", "손광", "sun_quan", "white_gold", "diamond"),
    General("zhou_fang", "주방", "taishi_ci", "blue_gold", "shield"),
    General("he_qi", "하제", "gan_ning", "teal_gold", "spear"),
    General("lu_fan", "여범", "zhou_yu", "white_red", "fan"),
    General("jiang_qin", "장흠", "gan_ning", "blue_gold", "spear"),
    General("pan_zhang", "반장", "huang_gai", "gold_brown", "sword"),
    General("ma_zhong_wu", "마충(오)", "taishi_ci", "steel_blue", "spear"),
    General("dong_xi", "동습", "gan_ning", "dark_red", "axe"),
    General("ling_cao", "능조", "gan_ning", "blue_gold", "spear"),
    General("sun_jun", "손준", "sun_ce", "red_gold", "sword"),
    General("sun_chen", "손침", "sun_ce", "dark_red", "diamond"),
    General("liu_zan", "유찬", "gan_ning", "teal_gold", "spear"),
    General("xu_kun", "서곤", "sun_ce", "red_gold", "spear"),
]


BASE_GROUPS: dict[str, list[str]] = {
    "strategist": [
        "zhuge_liang",
        "guo_jia",
        "sima_yi",
        "pang_tong",
        "zhou_yu",
        "liu_bei",
        "sun_quan",
        "yuan_shao",
        "lu_xun",
        "cao_cao",
    ],
    "duelist": [
        "zhao_yun",
        "ma_chao",
        "taishi_ci",
        "sun_ce",
        "gan_ning",
        "guan_yu",
        "zhang_liao",
        "xiahou_dun",
        "yan_liang",
        "huang_gai",
    ],
    "heavy": [
        "zhang_fei",
        "xu_chu",
        "dian_wei",
        "xu_huang",
        "wen_chou",
        "meng_huo",
        "dong_zhuo",
        "lu_bu",
        "huang_zhong",
        "cao_xing",
    ],
}
BASE_TO_GROUP = {base: group for group, bases in BASE_GROUPS.items() for base in bases}
FALLBACK_BASES = [base for bases in BASE_GROUPS.values() for base in bases]
PALETTE_POOL = [
    "blue_gold",
    "steel_blue",
    "bronze_blue",
    "crimson_black",
    "dark_red",
    "red_gold",
    "violet_black",
    "dark_gold",
    "white_blue",
    "white_gold",
    "gold_white",
    "green_gold",
    "teal_gold",
    "gold_brown",
    "white_red",
    "yellow_tao",
]
EMBLEM_POOL = [
    "shield",
    "spear",
    "sword",
    "diamond",
    "scroll",
    "fan",
    "axe",
    "spike",
    "bow",
    "moon",
    "mountain",
    "flame",
    "tiger",
    "horse",
]
FORCED_VISUALS: dict[str, tuple[str, str, str]] = {
    "sima_shi": ("sima_yi", "violet_black", "diamond"),
    "sima_zhao": ("yuan_shao", "dark_gold", "diamond"),
}


def rotated(items: list[str], seed: int) -> list[str]:
    if not items:
        return []
    start = seed % len(items)
    return items[start:] + items[:start]


def unique_order(items: list[str]) -> list[str]:
    out = []
    seen = set()
    for item in items:
        if item not in seen:
            seen.add(item)
            out.append(item)
    return out


def diversified_roster() -> list[General]:
    base_counts: dict[str, int] = {}
    used_pairs: set[tuple[str, str]] = set()
    out: list[General] = []
    last_base = ""

    for index, g in enumerate(ROSTER):
        seed = basegen.stable_int(f"diversify:{g.slug}")
        group = BASE_TO_GROUP.get(g.base, "duelist")
        base_candidates = unique_order([g.base] + rotated(BASE_GROUPS[group], seed) + rotated(FALLBACK_BASES, seed // 7))
        palette_candidates = unique_order([g.palette] + rotated(PALETTE_POOL, seed // 13))
        emblem_candidates = unique_order([g.emblem] + rotated(EMBLEM_POOL, seed // 17))

        best: tuple[int, str, str, str] | None = None
        for base in base_candidates:
            for palette in palette_candidates:
                for emblem in emblem_candidates[:4]:
                    pair = (base, palette)
                    score = 0
                    if pair in used_pairs:
                        score += 1000
                    if base_counts.get(base, 0) >= 4:
                        score += 500
                    if base == last_base:
                        score += 120
                    score += base_counts.get(base, 0) * 20
                    if base != g.base:
                        score += 5
                    if palette != g.palette:
                        score += 3
                    if emblem != g.emblem:
                        score += 1
                    # Neighboring imperial-family rows often sit together in the
                    # gallery; make them vary more aggressively.
                    if index and out[-1].palette == palette:
                        score += 18
                    candidate = (score, base, palette, emblem)
                    if best is None or candidate < best:
                        best = candidate
        assert best is not None
        _, base, palette, emblem = best
        base_counts[base] = base_counts.get(base, 0) + 1
        used_pairs.add((base, palette))
        last_base = base
        out.append(General(g.slug, g.ko, base, palette, emblem))
    out = [
        General(item.slug, item.ko, *FORCED_VISUALS[item.slug])
        if item.slug in FORCED_VISUALS
        else item
        for item in out
    ]
    return out


def manifest_item(g: General) -> dict[str, str]:
    return {"slug": g.slug, "ko": g.ko, "base": g.base, "palette": g.palette, "emblem": g.emblem}


def alpha_bbox(img: Image.Image) -> tuple[int, int, int, int]:
    return img.getchannel("A").getbbox() or (0, 0, img.width, img.height)


def make_general(g: General) -> Image.Image:
    seed = basegen.stable_int(f"extra100:{g.slug}")
    img = basegen.load_base(g.base)
    img = basegen.recolor(img, basegen.PALETTES[g.palette], seed)
    img = basegen.cover_textish_badges(img, seed, g.emblem)
    img = basegen.adjust_layout(img, seed)
    return img


def write_gallery(path: Path, title: str, asset_dir: str, manifest: list[dict[str, str]]) -> None:
    rows = "\n".join(f"  ['{m['slug']}', '{m['ko']}', '{m['base']}']," for m in manifest)
    html = f"""<!DOCTYPE html>
<html lang="ko">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>{title}</title>
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
  .base {{ color: #a98a50; font-size: 11px; }}
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
<h1>{title}</h1>
<p class="sub">기존 100명과 중복되지 않는 전신 후보입니다. 얼굴/피부/금장 보호 후 색감 보정을 적용했습니다.</p>
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

function card([id, name, base], index) {{
  const file = `${{id}}.png`;
  const card = document.createElement('section');
  card.className = 'card';
  card.dataset.key = `${{id}} ${{name}} ${{base}}`.toLowerCase();
  card.innerHTML = `
    <div class="name">
      <span>${{index + 1}}. ${{name}}</span>
      <small>${{file}}</small>
    </div>
    <div class="art"><img src="assets/generals/{asset_dir}/${{file}}?v=extra100-20260511" alt="${{name}} 전신"></div>
    <div class="file">{asset_dir}/${{file}} <span class="base">base: ${{base}}</span></div>
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
    path.write_text(html, encoding="utf-8")


def make_contact_sheet(manifest: list[dict[str, str]]) -> None:
    card_w, art_h, label_h = 250, 310, 40
    cols = 10
    rows = math.ceil(len(manifest) / cols)
    sheet = Image.new("RGBA", (cols * card_w, rows * (art_h + label_h)), (18, 11, 7, 255))
    draw = ImageDraw.Draw(sheet, "RGBA")
    try:
        font_big = ImageFont.truetype("/System/Library/Fonts/AppleSDGothicNeo.ttc", 20)
        font_small = ImageFont.truetype("/System/Library/Fonts/AppleSDGothicNeo.ttc", 13)
    except OSError:
        font_big = ImageFont.load_default()
        font_small = ImageFont.load_default()

    for idx, item in enumerate(manifest):
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
        img = Image.open(OUT_DIR / f"{item['slug']}.png").convert("RGBA")
        crop = img.crop(alpha_bbox(img))
        crop.thumbnail((card_w - 18, art_h - 12), Image.Resampling.LANCZOS)
        bg.alpha_composite(crop, ((card_w - crop.width) // 2, art_h - crop.height - 4))
        sheet.alpha_composite(bg, (x0, y0))
        draw.rectangle((x0, y0 + art_h, x0 + card_w, y0 + art_h + label_h), fill=(18, 10, 6, 255))
        draw.text((x0 + 10, y0 + art_h + 8), item["ko"], fill=(255, 226, 116, 255), font=font_big)
        draw.text((x0 + 82, y0 + art_h + 13), f"{item['slug']}.png", fill=(174, 139, 78, 255), font=font_small)
        draw.rectangle((x0, y0, x0 + card_w, y0 + art_h + label_h), outline=(128, 86, 23, 255), width=1)
    sheet.save(TMP_DIR / "extra_100_contact_sheet_colorfit.png")


def base_30_manifest() -> list[dict[str, str]]:
    html = (ROOT / "busts_gallery.html").read_text(encoding="utf-8")
    rows = re.findall(r"\['([^']+)',\s*'([^']+)'\]", html)
    return [{"slug": slug, "ko": ko, "base": "original"} for slug, ko in rows]


def write_200_gallery(extra100: list[dict[str, str]]) -> None:
    base30 = base_30_manifest()
    extra70 = json.loads((ROOT / "assets" / "generals" / "busts_extra_70_colorfit" / "manifest.json").read_text(encoding="utf-8"))
    combined = (
        [{"group": "기존 30", "asset_dir": "busts", "palette": "original", "emblem": "original", **m} for m in base30]
        + [{"group": "추가 70", "asset_dir": "busts_extra_70_colorfit", **m} for m in extra70]
        + [{"group": "추가 100", "asset_dir": "busts_extra_100_colorfit", **m} for m in extra100]
    )
    rows = "\n".join(
        f"  {{slug: '{m['slug']}', ko: '{m['ko']}', group: '{m['group']}', assetDir: '{m['asset_dir']}', sourceBase: '{m['base']}', palette: '{m['palette']}', emblem: '{m['emblem']}'}},"
        for m in combined
    )
    html = f"""<!DOCTYPE html>
<html lang="ko">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>삼국지 장수 200명 전신 후보 검수</title>
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
  .warning {{
    margin: 0 0 18px;
    padding: 12px 14px;
    border: 1px solid #8f6422;
    border-radius: 8px;
    background: #21170e;
    color: #ffd978;
    font-size: 14px;
    line-height: 1.45;
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
    grid-template-columns: repeat(auto-fill, minmax(230px, 1fr));
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
  .tag {{
    margin-left: 8px;
    color: #8fd48a;
    font-size: 11px;
    font-weight: 800;
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
  .source {{
    display: block;
    margin-top: 4px;
    color: #a98a50;
    font-size: 11px;
    line-height: 1.35;
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
<h1>삼국지 장수 200명 전신 후보 검수</h1>
<p class="sub">기존 30명 + 추가 70명 + 추가 100명입니다. 전신 이미지만 모아 검수합니다.</p>
<p class="warning">주의: 추가 장수는 신규 원화 완성본이 아니라 기존 원본을 기반으로 만든 후보입니다. 각 카드 하단에 source base / palette / emblem을 표시해 어떤 원본에서 파생됐는지 숨기지 않습니다.</p>
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

function card(item, index) {{
  const file = `${{item.slug}}.png`;
  const card = document.createElement('section');
  card.className = 'card';
  card.dataset.key = `${{item.slug}} ${{item.ko}} ${{item.group}} ${{item.sourceBase}} ${{item.palette}}`.toLowerCase();
  card.innerHTML = `
    <div class="name">
      <span>${{index + 1}}. ${{item.ko}} <span class="tag">${{item.group}}</span></span>
      <small>${{file}}</small>
    </div>
    <div class="art"><img src="assets/generals/${{item.assetDir}}/${{file}}?v=roster200-20260511" alt="${{item.ko}} 전신"></div>
    <div class="file">
      ${{item.assetDir}}/${{file}}
      <span class="source">source: ${{item.sourceBase}} / palette: ${{item.palette}} / emblem: ${{item.emblem}}</span>
    </div>
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
    (ROOT / "generals_200_gallery.html").write_text(html, encoding="utf-8")


def current_slugs() -> set[str]:
    base_slugs = {p.stem for p in (ROOT / "assets" / "generals" / "busts").glob("*.png")}
    extra70 = json.loads((ROOT / "assets" / "generals" / "busts_extra_70" / "manifest.json").read_text(encoding="utf-8"))
    return base_slugs | {m["slug"] for m in extra70}


def main() -> None:
    if len(ROSTER) != 100 or len({g.slug for g in ROSTER}) != 100:
        raise SystemExit("Roster must contain exactly 100 unique generals")
    roster = diversified_roster()
    duplicates = sorted({g.slug for g in roster} & current_slugs())
    if duplicates:
        raise SystemExit(f"Roster duplicates current generals: {duplicates}")
    repeated_pairs = sorted(
        pair for pair in {(g.base, g.palette) for g in roster}
        if sum(1 for item in roster if (item.base, item.palette) == pair) > 1
    )
    if repeated_pairs:
        raise SystemExit(f"Visual base/palette duplicates remain: {repeated_pairs[:10]}")
    base_overuse = sorted(
        (base, sum(1 for item in roster if item.base == base))
        for base in {g.base for g in roster}
        if sum(1 for item in roster if item.base == base) > 4
    )
    if base_overuse:
        raise SystemExit(f"Base overuse remains: {base_overuse}")
    missing_bases = sorted({g.base for g in roster} - {p.stem for p in (ROOT / "assets" / "generals" / "busts").glob("*.png")})
    if missing_bases:
        raise SystemExit(f"Missing base busts: {missing_bases}")

    manifest = []
    for g in roster:
        raw = make_general(g)
        raw.save(RAW_DIR / f"{g.slug}.png")
        colorfit_mod.colorfit(raw).save(OUT_DIR / f"{g.slug}.png")
        manifest.append(manifest_item(g))

    text = json.dumps(manifest, ensure_ascii=False, indent=2)
    (RAW_DIR / "manifest.json").write_text(text, encoding="utf-8")
    (OUT_DIR / "manifest.json").write_text(text, encoding="utf-8")
    write_gallery(ROOT / "extra_100_busts_gallery.html", "추가 장수 100명 전신 후보", "busts_extra_100", manifest)
    write_gallery(ROOT / "extra_100_busts_gallery_colorfit.html", "추가 장수 100명 전신 후보 - 색감 보정", "busts_extra_100_colorfit", manifest)
    make_contact_sheet(manifest)
    write_200_gallery(manifest)
    print(f"generated {len(manifest)} busts -> {OUT_DIR}")
    print(ROOT / "extra_100_busts_gallery_colorfit.html")
    print(ROOT / "generals_200_gallery.html")
    print(TMP_DIR / "extra_100_contact_sheet_colorfit.png")


if __name__ == "__main__":
    main()
