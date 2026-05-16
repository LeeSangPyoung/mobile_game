from __future__ import annotations

import ast
import json
import re
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
ROSTER_JS = ROOT / "assets" / "generals" / "roster_200.js"
BASE_GALLERY = ROOT / "busts_gallery.html"
OUT_DIR = ROOT / "tmp" / "real_generals_170"
RAW_DIR = OUT_DIR / "raw" / "busts"
FINAL_DIR = ROOT / "assets" / "generals" / "busts_real_170"


WEI = {
    "zhang_he", "yu_jin", "yue_jin", "li_dian", "cao_ren", "cao_hong", "cao_pi", "cao_zhi",
    "cao_zhang", "cao_ang", "cao_rui", "cao_shuang", "cao_zhen", "cao_xiu", "xiahou_yuan",
    "xiahou_ba", "cheng_yu", "xun_yu", "xun_you", "jia_xu", "man_chong", "zhong_yao",
    "deng_ai", "zhong_hui", "guo_huai", "wang_ping", "wen_pin", "zang_ba", "li_tong",
    "han_hao", "lu_qian", "mao_jie", "liu_ye", "kuai_yue", "kuai_liang", "cai_mao", "zhang_yun",
}
WU = {
    "xu_sheng", "ding_feng", "han_dang", "cheng_pu", "zhou_tai", "jiang_qin", "ling_tong",
    "lu_su", "zhang_zhao", "zhang_hong", "zhu_zhi", "zhu_huan", "zhu_ran", "bu_zhi",
    "kan_ze", "yu_fan", "he_qi", "pan_zhang", "ma_zhong_wu", "quan_cong", "sun_jian",
    "sun_shao", "sun_huan", "sun_luban", "sun_luyu", "daqiao", "xiaoqiao", "lian_shi",
}
SHU = {
    "guan_ping", "guan_xing", "guan_suo", "guan_yinping", "zhang_bao", "liu_shan", "liu_feng",
    "ma_su", "ma_liang", "jiang_wei", "wei_yan", "fa_zheng", "jian_yong", "mi_zhu", "mi_fang",
    "sun_qian", "liao_hua", "zhou_cang", "ma_dai", "yan_yan", "li_yan", "fei_yi", "dong_yun",
    "jiang_wan", "huang_quan", "chen_dao", "fu_shi_ren", "meng_da", "zhang_song", "li_hui",
    "huo_jun", "sha_moke", "zhuge_zhan", "zhuge_jin", "zhuge_dan", "zhang_yi_shu", "dong_jue",
}
NORTHERN = {
    "yuan_tan", "yuan_xi", "yuan_shang", "tian_feng", "ju_shou", "shen_pei", "feng_ji",
    "guo_tu", "xin_ping", "xin_pi", "gao_lan", "zhang_bu", "gongsun_zan", "gongsun_du",
    "gongsun_kang", "gongsun_yuan", "liu_biao", "liu_zhang", "liu_yao", "liu_yu", "tao_qian",
    "kong_rong", "zhang_lu", "zhang_ren", "yan_pu", "ma_teng", "han_sui", "cheng_yin",
    "liang_xing", "hou_xuan", "cheng_gongying",
}
COURT_AND_REBELS = {
    "dong_cheng", "he_jin", "zhang_rang", "emperor_xian", "wang_yun", "diao_chan", "li_jue",
    "guo_si", "fan_chou", "zhang_ji", "zhang_xiu", "hu_che_er", "zou_shi", "hua_xiong",
    "li_ru", "yuan_shu", "ji_ling", "liu_xun", "chen_lan", "lei_bo", "zhang_xun",
    "qiao_rui", "han_xian", "yang_feng", "hua_tuo", "zuo_ci", "yu_ji", "zhang_jiao",
    "zhang_bao_yellow", "zhang_liang_yellow", "bo_cai", "cheng_yuanzhi", "deng_mao",
    "guan_hai", "pei_yuanshao", "zhang_man_cheng", "han_zhong",
}


BODY_TYPES = [
    "short square Roblox-like commander with huge boots and compact torso",
    "broad heavy infantry bruiser with barrel chest and thick arms",
    "lean spear officer with long vertical weapon silhouette",
    "older strategist with narrow shoulders, long sleeves, and scroll pouch",
    "young noble officer with clean face, slim waist, and oversized shoulder guards",
    "frontier cavalry archer with quiver, layered fur collar, and asymmetrical armor",
    "court official general with tall ceremonial headpiece and robe armor",
    "masked or scarred veteran with one exposed eye and heavy brow",
    "wild rebel warlord with rough hair, uneven pauldrons, and aggressive stance",
    "elegant fan-bearing tactician with cape panels and calm expression",
]
WEAPONS = [
    "single broad dao sword",
    "crescent halberd",
    "long spear with tassel",
    "heavy mace",
    "rectangular command tablet",
    "folding war fan",
    "bow with quiver",
    "pair of short axes",
    "tower shield and short sword",
    "scroll case and ritual staff",
    "hooked polearm",
    "curved saber held low",
]
FACE_TRAITS = [
    "thin moustache and pointed chin beard",
    "wide jaw with thick boxed beard",
    "clean-shaven young face with sharp eyebrows",
    "long white beard and stern eyes",
    "rounder face with small moustache and wary eyes",
    "scar over one cheek with clenched expression",
    "heavy sideburns and short braided beard",
    "long narrow face with scholar moustache",
    "shouting mouth with thick black beard",
    "calm half-smile with narrow eyes",
]
HELMETS = [
    "low gold crown with red jewel",
    "tall black lacquer hat with gold rails",
    "blue-plumed metal helmet",
    "fur-trimmed northern helmet",
    "flat court cap with bead fringe",
    "spiked rebel headband",
    "white scholar turban with gold clasp",
    "rounded heavy helm with cheek guards",
    "open hair topknot with small diadem",
    "winged side ornaments on the helmet",
]
PALETTES = {
    "wei": ["deep navy, gunmetal, bright gold, small royal blue gems", "black lacquer, cobalt cloth, polished gold trim", "silver-blue armor, dark cape, restrained red cords"],
    "wu": ["red lacquer, ivory cloth, bright gold trim, blue gem accents", "teal blue cape, dark bronze armor, gold trim", "warm crimson armor with white robe panels"],
    "shu": ["green cloak, black armor, gold trim, cream cloth", "white and blue armor with gold trim", "deep red cloth, dark armor, gold ornaments"],
    "northern": ["sand gold, dark leather, weathered bronze, muted red cords", "black armor, ochre cape, gold trim", "blue-gray steel with fur and brown leather"],
    "rebel": ["black and crimson armor, harsh gold spikes, smoky dark cloth", "yellow ochre cloth, dark iron armor, rough gold plates", "purple-black robe armor with gold talismans"],
}


def stable_int(text: str) -> int:
    value = 0
    for ch in text:
        value = (value * 131 + ord(ch)) % 1_000_000_007
    return value


def pick(items: list[str], seed: int, offset: int = 0) -> str:
    return items[(seed + offset) % len(items)]


def load_roster() -> list[tuple[str, str]]:
    text = ROSTER_JS.read_text(encoding="utf-8")
    start = text.index("[")
    end = text.rindex("]") + 1
    data = ast.literal_eval(text[start:end])
    return [(row[0], row[1]) for row in data]


def approved_base_ids() -> set[str]:
    html = BASE_GALLERY.read_text(encoding="utf-8")
    return {m.group(1) for m in re.finditer(r"\['([^']+)',\s*'[^']+'\]", html)}


def faction(slug: str) -> str:
    if slug in WEI:
        return "wei"
    if slug in WU:
        return "wu"
    if slug in SHU:
        return "shu"
    if slug in NORTHERN:
        return "northern"
    if slug in COURT_AND_REBELS:
        return "rebel"
    return "northern"


def design_spec(slug: str, name: str, index: int) -> dict[str, str]:
    seed = stable_int(slug)
    fac = faction(slug)
    body = pick(BODY_TYPES, seed, index)
    weapon = pick(WEAPONS, seed // 7, index * 2)
    face = pick(FACE_TRAITS, seed // 11, index * 3)
    helmet = pick(HELMETS, seed // 13, index * 5)
    palette = pick(PALETTES[fac], seed // 17, index)
    if slug in {"daqiao", "xiaoqiao", "lian_shi", "diao_chan", "sun_luban", "sun_luyu", "guan_yinping", "zou_shi"}:
        body = "compact heroic female general with blocky game proportions, armored dress panels, and oversized boots"
        weapon = pick(["folding war fan", "slender sword", "ritual staff", "short spear with tassel"], seed, index)
        face = pick(["calm confident eyes", "fierce battle-ready expression", "elegant stern expression"], seed, index)
        helmet = pick(["gold hair ornament with side ribbons", "small crown with jewel", "white-plumed circlet", "red lacquer hairpiece"], seed, index)
    if slug in {"hua_tuo", "zuo_ci", "yu_ji"}:
        body = "elder mystic healer silhouette with robe armor, chunky boots, and small talisman accessories"
        weapon = "wooden staff with gold medical charm"
        face = "elder face with long white beard and sharp eyebrows"
        helmet = "simple cloth cap with gold charm"
    if slug in {"emperor_xian", "wang_yun", "he_jin", "zhang_rang"}:
        body = "court official commander with ceremonial robe armor and compact toy-like proportions"
        weapon = "rectangular command tablet"
        helmet = "flat court cap with bead fringe"
    return {
        "faction": fac,
        "body": body,
        "weapon": weapon,
        "face": face,
        "helmet": helmet,
        "palette": palette,
    }


def prompt(slug: str, name: str, spec: dict[str, str]) -> str:
    return f"""Use case: stylized-concept
Asset type: full-body transparent-background game character source, later chroma-keyed.
Primary request: Create ONE original full-body Three Kingdoms general character cutout for {name} ({slug}).
Style lock: match the user's approved 30-character game style: chunky SD / Roblox-like heroic proportions, short legs with huge boots, large head and hands, readable toy-figure silhouette, polished 3D cartoon render, glossy gold trim, dark lacquered armor panels, clean mobile RPG collectible look.
New-design rule: this must be a new character design, not a recolor, not a traced pose, not a copied armor layout, not a copied face, and not a kitbash of any existing sample. Make the silhouette recognizable before color is considered.
Character design: {spec['body']}; {spec['face']}; {spec['helmet']}; carries {spec['weapon']}.
Faction/color direction: {spec['palette']}.
Composition: centered full body from head to boots, three-quarter front view, feet visible, weapon fully inside frame, same scale and camera as the reference game busts.
Backdrop: perfectly flat solid #00ff00 chroma-key background only.
Constraints: no text, no labels, no watermark, no cropped limbs, no environmental floor, no cast shadow, no gradient, no green on the character, no photorealism, no anime thin-body proportions, no tall realistic human proportions.
Quality target: clean face, crisp eyes, simple bold shapes, strong armor readability at small gallery size."""


def write_board(jobs: list[dict[str, object]]) -> None:
    rows = "\n".join(
        f"  {{slug: '{job['slug']}', ko: '{job['ko']}', faction: '{job['design']['faction']}', body: {json.dumps(job['design']['body'], ensure_ascii=False)}, weapon: {json.dumps(job['design']['weapon'], ensure_ascii=False)}, palette: {json.dumps(job['design']['palette'], ensure_ascii=False)}, out: '{job['out']}'}},"
        for job in jobs
    )
    html = f"""<!DOCTYPE html>
<html lang="ko">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>진짜 신규 장수 170명 제작 큐</title>
<style>
  * {{ box-sizing: border-box; }}
  body {{ margin: 0; padding: 28px; background: #17110b; color: #f7d56e; font-family: -apple-system, BlinkMacSystemFont, "Apple SD Gothic Neo", sans-serif; }}
  h1 {{ margin: 0 0 8px; font-size: 30px; }}
  .sub {{ margin: 0 0 18px; color: #c5a86b; line-height: 1.45; }}
  .warning {{ margin: 0 0 18px; padding: 12px 14px; border: 1px solid #8f6422; border-radius: 8px; background: #21170e; color: #ffd978; line-height: 1.45; }}
  .toolbar {{ position: sticky; top: 0; z-index: 2; display: flex; gap: 10px; align-items: center; padding: 12px 0 16px; background: linear-gradient(180deg, #17110b 70%, rgba(23,17,11,0)); }}
  input {{ width: min(420px, 100%); height: 40px; padding: 0 14px; border: 1px solid #7b5724; border-radius: 8px; background: #24190f; color: #ffe188; font-size: 15px; outline: none; }}
  .count {{ color: #a98a50; font-weight: 800; }}
  .grid {{ display: grid; grid-template-columns: repeat(auto-fill, minmax(320px, 1fr)); gap: 14px; }}
  .card {{ border: 1px solid #79551f; border-radius: 8px; overflow: hidden; background: linear-gradient(180deg, #24190f, #110b07); }}
  .name {{ display: flex; justify-content: space-between; gap: 10px; padding: 11px 12px; border-bottom: 1px solid #664719; color: #ffe188; font-size: 17px; font-weight: 800; }}
  .tag {{ color: #8fd48a; font-size: 12px; font-weight: 900; }}
  .body {{ padding: 11px 12px; color: #d7be79; font-size: 13px; line-height: 1.45; }}
  .path {{ padding: 8px 12px 11px; border-top: 1px solid #3d2a12; color: #a98a50; font-size: 12px; word-break: break-all; }}
</style>
</head>
<body>
<h1>진짜 신규 장수 170명 제작 큐</h1>
<p class="sub">기존 30명은 유지하고, 나머지 170명은 복제/색변경 후보가 아니라 새 렌더가 필요한 대상으로 관리합니다.</p>
<p class="warning">이 페이지는 완성 갤러리가 아닙니다. 각 카드의 body/weapon/palette가 실제 이미지 생성 프롬프트에 들어가며, 기존 원본을 베이스로 복사하지 않는 것이 통과 기준입니다.</p>
<div class="toolbar"><input id="search" type="search" placeholder="이름, 파일명, 무기, 진영 검색"><div class="count" id="count"></div></div>
<main class="grid" id="grid"></main>
<script>
const jobs = [
{rows}
];
const grid = document.getElementById('grid');
const search = document.getElementById('search');
const count = document.getElementById('count');
function card(job, index) {{
  const el = document.createElement('section');
  el.className = 'card';
  el.dataset.key = `${{job.slug}} ${{job.ko}} ${{job.faction}} ${{job.body}} ${{job.weapon}} ${{job.palette}}`.toLowerCase();
  el.innerHTML = `
    <div class="name"><span>${{index + 1}}. ${{job.ko}}</span><span class="tag">${{job.faction}}</span></div>
    <div class="body"><b>body</b>: ${{job.body}}<br><b>weapon</b>: ${{job.weapon}}<br><b>palette</b>: ${{job.palette}}</div>
    <div class="path">${{job.out}}</div>
  `;
  return el;
}}
const cards = jobs.map(card);
cards.forEach(el => grid.appendChild(el));
function filter() {{
  const q = search.value.trim().toLowerCase();
  let shown = 0;
  cards.forEach(el => {{
    const ok = !q || el.dataset.key.includes(q);
    el.style.display = ok ? '' : 'none';
    if (ok) shown++;
  }});
  count.textContent = `${{shown}} / ${{jobs.length}}`;
}}
search.addEventListener('input', filter);
filter();
</script>
</body>
</html>
"""
    (ROOT / "real_generals_170_production_board.html").write_text(html, encoding="utf-8")


def write_real_200_gallery(jobs: list[dict[str, object]]) -> None:
    approved = []
    names = dict(load_roster())
    for slug in sorted(approved_base_ids(), key=lambda value: [item[0] for item in load_roster()].index(value)):
        approved.append({
            "slug": slug,
            "ko": names.get(slug, slug),
            "group": "기존 승인 30",
            "asset_dir": "busts",
            "status": "done",
            "body": "approved original",
            "weapon": "approved original",
            "palette": "approved original",
        })
    queued = [
        {
            "slug": str(job["slug"]),
            "ko": str(job["ko"]),
            "group": "신규 렌더 170",
            "asset_dir": "busts_real_170",
            "status": "render_pending",
            "body": str(job["design"]["body"]),
            "weapon": str(job["design"]["weapon"]),
            "palette": str(job["design"]["palette"]),
        }
        for job in jobs
    ]
    rows = "\n".join(
        f"  {{slug: '{item['slug']}', ko: '{item['ko']}', group: '{item['group']}', assetDir: '{item['asset_dir']}', status: '{item['status']}', body: {json.dumps(item['body'], ensure_ascii=False)}, weapon: {json.dumps(item['weapon'], ensure_ascii=False)}, palette: {json.dumps(item['palette'], ensure_ascii=False)}}},"
        for item in approved + queued
    )
    html = f"""<!DOCTYPE html>
<html lang="ko">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>진짜 신규 기준 200명 전신 갤러리</title>
<style>
  * {{ box-sizing: border-box; }}
  body {{ margin: 0; padding: 28px; background: #17110b; color: #f7d56e; font-family: -apple-system, BlinkMacSystemFont, "Apple SD Gothic Neo", sans-serif; }}
  h1 {{ margin: 0 0 8px; font-size: 30px; }}
  .sub {{ margin: 0 0 18px; color: #c5a86b; line-height: 1.45; }}
  .warning {{ margin: 0 0 18px; padding: 12px 14px; border: 1px solid #8f6422; border-radius: 8px; background: #21170e; color: #ffd978; line-height: 1.45; }}
  .toolbar {{ position: sticky; top: 0; z-index: 2; display: flex; gap: 10px; align-items: center; padding: 12px 0 16px; background: linear-gradient(180deg, #17110b 70%, rgba(23,17,11,0)); }}
  input {{ width: min(420px, 100%); height: 40px; padding: 0 14px; border: 1px solid #7b5724; border-radius: 8px; background: #24190f; color: #ffe188; font-size: 15px; outline: none; }}
  .count, .audit {{ color: #a98a50; font-size: 14px; white-space: nowrap; }}
  .audit {{ margin-left: auto; font-weight: 800; }}
  .audit.ok {{ color: #8fd48a; }}
  .audit.bad {{ color: #ff8f75; }}
  .grid {{ display: grid; grid-template-columns: repeat(auto-fill, minmax(230px, 1fr)); gap: 16px; }}
  .card {{ min-width: 0; border: 1px solid #79551f; border-radius: 8px; overflow: hidden; background: linear-gradient(180deg, #24190f, #110b07); }}
  .name {{ display: flex; justify-content: space-between; gap: 10px; align-items: baseline; padding: 11px 12px; border-bottom: 1px solid #664719; color: #ffe188; font-size: 17px; font-weight: 800; }}
  .name small {{ min-width: 0; color: #a98a50; font-size: 12px; font-weight: 700; text-align: right; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }}
  .tag {{ margin-left: 8px; color: #8fd48a; font-size: 11px; font-weight: 800; }}
  .art {{ height: 330px; display: flex; align-items: flex-end; justify-content: center; padding: 14px; background: linear-gradient(90deg, rgba(255,255,255,0.035) 1px, transparent 1px), linear-gradient(rgba(255,255,255,0.035) 1px, transparent 1px), radial-gradient(circle at 50% 18%, rgba(255,212,91,0.16), transparent 44%), #21170e; background-size: 28px 28px, 28px 28px, 100% 100%, 100% 100%; }}
  img {{ display: block; max-width: 100%; max-height: 100%; object-fit: contain; filter: drop-shadow(0 14px 16px rgba(0,0,0,0.62)); }}
  .file {{ padding: 8px 10px 10px; border-top: 1px solid #3d2a12; color: #f7d56e; font-size: 12px; word-break: break-all; }}
  .source {{ display: block; margin-top: 4px; color: #a98a50; font-size: 11px; line-height: 1.35; }}
  .missing .art {{ align-items: center; color: #ff9a7a; font-size: 13px; font-weight: 900; text-align: center; }}
  .missing .file {{ color: #ff9a7a; }}
  @media (max-width: 720px) {{ body {{ padding: 18px; }} h1 {{ font-size: 24px; }} .toolbar {{ align-items: flex-start; flex-direction: column; }} .audit {{ margin-left: 0; }} .grid {{ grid-template-columns: repeat(auto-fill, minmax(170px, 1fr)); }} .art {{ height: 260px; }} }}
</style>
</head>
<body>
<h1>진짜 신규 기준 200명 전신 갤러리</h1>
<p class="sub">기존 승인 30명은 그대로 쓰고, 나머지 170명은 새 렌더가 들어와야 채워지는 구조입니다.</p>
<p class="warning">복제/색변경 후보는 여기서 사용하지 않습니다. 이미지가 없으면 빈칸으로 두고 `렌더 대기`로 표시합니다.</p>
<div class="toolbar"><input id="search" type="search" placeholder="이름, 파일명, 상태 검색"><div class="count" id="count"></div><div class="audit" id="audit">검수 중...</div></div>
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
  card.dataset.key = `${{item.slug}} ${{item.ko}} ${{item.group}} ${{item.status}} ${{item.body}} ${{item.weapon}} ${{item.palette}}`.toLowerCase();
  card.innerHTML = `
    <div class="name"><span>${{index + 1}}. ${{item.ko}} <span class="tag">${{item.group}}</span></span><small>${{file}}</small></div>
    <div class="art"><img src="assets/generals/${{item.assetDir}}/${{file}}?v=real-200-20260511" alt="${{item.ko}} 전신"></div>
    <div class="file">${{item.assetDir}}/${{file}}<span class="source">status: ${{item.status}}<br>body: ${{item.body}}<br>weapon: ${{item.weapon}}<br>palette: ${{item.palette}}</span></div>
  `;
  return card;
}}

const cards = generals.map(card);
cards.forEach(card => grid.appendChild(card));
function updateAudit() {{
  const checked = loaded + failed;
  audit.textContent = failed ? `이미지 ${{loaded}}/${{generals.length}}, 렌더 대기 ${{failed}}` : `이미지 ${{loaded}}/${{generals.length}}`;
  audit.className = `audit ${{loaded === generals.length ? 'ok' : failed ? 'bad' : ''}}`;
}}
grid.querySelectorAll('img').forEach(img => {{
  img.addEventListener('load', () => {{ loaded++; updateAudit(); }});
  img.addEventListener('error', () => {{
    failed++;
    const card = img.closest('.card');
    card.classList.add('missing');
    img.closest('.art').textContent = '렌더 대기';
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
    (ROOT / "real_generals_200_gallery.html").write_text(html, encoding="utf-8")


def main() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    RAW_DIR.mkdir(parents=True, exist_ok=True)
    FINAL_DIR.mkdir(parents=True, exist_ok=True)
    base_ids = approved_base_ids()
    roster = load_roster()
    extras = [(slug, ko) for slug, ko in roster if slug not in base_ids]
    if len(extras) != 170:
        raise SystemExit(f"Expected 170 new render targets, got {len(extras)}")

    jobs = []
    jsonl_path = OUT_DIR / "jobs_busts_170.jsonl"
    manifest_path = OUT_DIR / "manifest.json"
    with jsonl_path.open("w", encoding="utf-8") as f:
        for idx, (slug, ko) in enumerate(extras, start=1):
            spec = design_spec(slug, ko, idx)
            out = f"{slug}.png"
            job = {
                "prompt": prompt(slug, ko, spec),
                "use_case": "stylized-concept",
                "size": "1024x1536",
                "quality": "high",
                "output_format": "png",
                "out": out,
                "slug": slug,
                "ko": ko,
                "design": spec,
            }
            jobs.append(job)
            f.write(json.dumps(job, ensure_ascii=False) + "\n")

    manifest = {
        "status": "queued_for_true_new_render",
        "approved_existing_count": len(base_ids),
        "new_render_count": len(jobs),
        "raw_dir": str(RAW_DIR),
        "final_dir": str(FINAL_DIR),
        "jobs_jsonl": str(jsonl_path),
        "items": [
            {
                "slug": job["slug"],
                "ko": job["ko"],
                "design": job["design"],
                "raw_output": str(RAW_DIR / str(job["out"])),
                "final_output": str(FINAL_DIR / str(job["out"])),
            }
            for job in jobs
        ],
    }
    manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    write_board(jobs)
    write_real_200_gallery(jobs)
    print(f"queued: {len(jobs)}")
    print(jsonl_path)
    print(manifest_path)
    print(ROOT / "real_generals_170_production_board.html")
    print(ROOT / "real_generals_200_gallery.html")


if __name__ == "__main__":
    main()
