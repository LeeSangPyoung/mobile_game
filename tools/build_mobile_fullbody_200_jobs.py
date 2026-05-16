#!/usr/bin/env python3
from __future__ import annotations

import json
import re
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
HTML = ROOT / "samguk_generals_200.html"
OUT_DIR = ROOT / "tmp" / "mobile_generals_200"
RAW_DIR = OUT_DIR / "raw"
FINAL_DIR = ROOT / "assets" / "generals" / "mobile_fullbody"
JOBS = OUT_DIR / "jobs_fullbody_200.jsonl"
MANIFEST = OUT_DIR / "manifest.json"


FEMALE = {
    "daqiao", "xiaoqiao", "lian_shi", "sun_luban", "sun_luyu",
    "guan_yinping", "diao_chan", "zou_shi",
}
STRATEGIST = {
    "zhuge_liang", "pang_tong", "guo_jia", "sima_yi", "zhou_yu", "lu_xun",
    "jia_xu", "xun_yu", "xun_you", "cheng_yu", "fa_zheng", "lu_su",
    "zhang_zhao", "zhang_hong", "tian_feng", "ju_shou", "shen_pei",
    "guo_tu", "xin_ping", "xin_pi", "li_ru", "wang_yun", "mao_jie",
    "liu_ye", "zhong_yao", "kuai_yue", "kuai_liang", "kan_ze", "yu_fan",
}
HEAVY = {
    "zhang_fei", "dian_wei", "xu_chu", "wen_chou", "yan_liang", "hua_xiong",
    "meng_huo", "ji_ling", "gan_ning", "huang_gai", "wei_yan", "zhou_tai",
    "pan_zhang", "guan_hai", "zhang_man_cheng",
}
CAVALRY = {
    "lu_bu", "zhao_yun", "ma_chao", "ma_dai", "ma_teng", "gongsun_zan",
    "xiahou_yuan", "zhang_liao", "taishi_ci", "wen_yang", "han_sui",
    "zhang_xiu", "sun_ce",
}
COURT = {
    "emperor_xian", "he_jin", "zhang_rang", "dong_cheng", "liu_biao",
    "liu_zhang", "tao_qian", "kong_rong", "yuan_shu", "liu_yu", "liu_yao",
}
MYSTIC = {"hua_tuo", "zuo_ci", "yu_ji", "zhang_jiao"}


BODY_TYPES = [
    "short square commander with large head, huge boots, compact torso, and confident stance",
    "broad heavy infantry bruiser with barrel chest, thick arms, huge boots, and low center of gravity",
    "lean spear officer with strong vertical silhouette, long shoulder guards, and oversized hands",
    "older strategist with compact robe armor, long sleeves, scroll pouch, and calm posture",
    "young noble officer with clean face, slim waist, oversized shoulder guards, and polished armor",
    "frontier cavalry archer with quiver, layered fur collar, asymmetrical armor, and big boots",
    "court official commander with ceremonial robe armor, compact toy-like proportions, and tall cap",
    "masked or scarred veteran with one exposed eye, heavy brow, and chunky armored gloves",
    "wild rebel warlord with rough hair, uneven pauldrons, aggressive stance, and blocky armor",
    "elegant fan-bearing tactician with cape panels, calm expression, and short heroic proportions",
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
    "위": [
        "deep navy, gunmetal, bright gold, small royal blue gems",
        "black lacquer, cobalt cloth, polished gold trim",
        "silver-blue armor, dark cape, restrained red cords",
    ],
    "촉": [
        "green cloak, black armor, gold trim, cream cloth",
        "white and blue armor with gold trim",
        "deep red cloth, dark armor, gold ornaments",
    ],
    "오": [
        "red lacquer, ivory cloth, bright gold trim, blue gem accents",
        "teal blue cape, dark bronze armor, gold trim",
        "warm crimson armor with white robe panels",
    ],
    "군웅": [
        "sand gold, dark leather, weathered bronze, muted red cords",
        "black armor, ochre cape, gold trim",
        "blue-gray steel with fur and brown leather",
    ],
    "황건": [
        "yellow ochre cloth, dark iron armor, rough gold plates",
        "purple-black robe armor with gold talismans",
        "muddy brown leather, yellow scarf, chipped bronze",
    ],
    "기타": [
        "black and crimson armor, harsh gold spikes, smoky dark cloth",
        "yellow ochre cloth, dark iron armor, rough gold plates",
        "muted ivory robe armor, dark bronze trim, small red cords",
    ],
}


def stable_int(text: str) -> int:
    value = 0
    for ch in text:
        value = (value * 131 + ord(ch)) % 1_000_000_007
    return value


def pick(items: list[str], seed: int, offset: int = 0) -> str:
    return items[(seed + offset) % len(items)]


def roster() -> list[dict[str, str]]:
    text = HTML.read_text(encoding="utf-8")
    rows = re.findall(r'\{ slug: "([^"]+)", name: "([^"]+)", force: "([^"]+)" \}', text)
    if len(rows) != 200:
        raise SystemExit(f"expected 200 rows in {HTML.name}, got {len(rows)}")
    return [{"slug": slug, "name": name, "force": force} for slug, name, force in rows]


def design(slug: str, name: str, force: str, index: int) -> dict[str, str]:
    seed = stable_int(slug)
    body = pick(BODY_TYPES, seed, index)
    weapon = pick(WEAPONS, seed // 7, index * 2)
    face = pick(FACE_TRAITS, seed // 11, index * 3)
    helmet = pick(HELMETS, seed // 13, index * 5)
    palette = pick(PALETTES[force], seed // 17, index)
    role = "commander"

    if slug in FEMALE:
        role = "heroine"
        body = "compact heroic female general with blocky game proportions, armored dress panels, oversized boots, and readable silhouette"
        weapon = pick(["folding war fan", "slender sword", "ritual staff", "short spear with tassel"], seed, index)
        face = pick(["calm confident eyes", "fierce battle-ready expression", "elegant stern expression"], seed, index)
        helmet = pick(["gold hair ornament with side ribbons", "small crown with jewel", "white-plumed circlet", "red lacquer hairpiece"], seed, index)
    elif slug in MYSTIC:
        role = "mystic"
        body = "elder mystic healer silhouette with robe armor, chunky boots, talisman accessories, and simple bold shapes"
        weapon = "wooden staff with gold medical charm"
        face = "elder face with long white beard and sharp eyebrows"
        helmet = "simple cloth cap with gold charm"
    elif slug in COURT:
        role = "court"
        body = "court official commander with ceremonial robe armor, compact toy-like proportions, huge boots, and dignified posture"
        weapon = "rectangular command tablet"
        helmet = "flat court cap with bead fringe"
    elif force == "황건":
        role = "yellow rebel"
        body = "wild yellow-scarf rebel general with rough blocky armor, chunky boots, and aggressive but cute stance"
    elif slug in STRATEGIST:
        role = "strategist"
        body = "short SD tactician with robe armor, oversized sleeves, big hands, scroll pouch, and clean readable silhouette"
        weapon = pick(["folding war fan", "scroll case and ritual staff", "rectangular command tablet"], seed, index)
    elif slug in HEAVY:
        role = "heavy"
        body = "broad heavy warrior with oversized fists, barrel chest, huge boots, and simple powerful armor masses"
        weapon = pick(["heavy mace", "crescent halberd", "pair of short axes", "tower shield and short sword"], seed, index)
    elif slug in CAVALRY:
        role = "cavalry"
        body = "compact cavalry hero with long weapon silhouette, strong cape, huge boots, and confident forward stance"
        weapon = pick(["long spear with tassel", "crescent halberd", "curved saber held low"], seed, index)

    return {
        "role": role,
        "body": body,
        "weapon": weapon,
        "face": face,
        "helmet": helmet,
        "palette": palette,
        "force": force,
        "name": name,
    }


def prompt(slug: str, name: str, spec: dict[str, str]) -> str:
    return f"""Use case: stylized-concept
Asset type: production mobile game character, full-body PNG source on chroma-key background.
Primary request: Create ONE original full-body Three Kingdoms general character cutout for {name} ({slug}).
Art direction: polished casual mobile RPG SD style with only subtle Roblox influence. It should NOT look like a full Roblox avatar: large expressive head, compact 4.5-head-tall body, rounded chunky torso and limbs, slightly oversized boots and hands, simple armor plates with only a few squared edges, cute readable proportions, collectible mobile RPG unit.
Production target: this should look like a real mobile game character asset, not a flat icon, not vector art, not a sketch, not a placeholder, not a toy screenshot.
Character design: {spec['body']}; {spec['face']}; {spec['helmet']}; carries {spec['weapon']}.
Faction/color direction: {spec['palette']}.
Composition: centered full body from head to boots, three-quarter front view, feet visible, weapon fully inside frame, readable silhouette at small size, generous padding.
Backdrop: perfectly flat solid #00ff00 chroma-key background only.
Constraints: no text, no labels, no watermark, no cropped limbs, no environmental floor, no cast shadow, no gradient, no green on the character, no photorealism, no tall realistic proportions, no anime thin-body proportions, no fully cubic Roblox body, no hyper-detailed armor noise, no ornate luxury crown, no delicate pretty-boy face, no over-decorated prince styling.
Quality target: clean face, crisp eyes, appealing cute proportions, simple bold shapes, medium-low detail, premium casual mobile game finish."""


def main() -> None:
    rows = roster()
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    RAW_DIR.mkdir(parents=True, exist_ok=True)
    FINAL_DIR.mkdir(parents=True, exist_ok=True)

    jobs = []
    for index, row in enumerate(rows, 1):
        spec = design(row["slug"], row["name"], row["force"], index)
        raw = RAW_DIR / f"{row['slug']}.png"
        final = FINAL_DIR / f"{row['slug']}.png"
        jobs.append({
            "prompt": prompt(row["slug"], row["name"], spec),
            "use_case": "stylized-concept",
            "size": "1024x1536",
            "quality": "high",
            "output_format": "png",
            "out": str(raw),
            "slug": row["slug"],
            "ko": row["name"],
            "force": row["force"],
            "final": str(final),
            "design": spec,
        })

    JOBS.write_text("\n".join(json.dumps(job, ensure_ascii=False) for job in jobs) + "\n", encoding="utf-8")
    MANIFEST.write_text(json.dumps({"count": len(jobs), "jobs": str(JOBS), "raw_dir": str(RAW_DIR), "final_dir": str(FINAL_DIR), "items": jobs}, ensure_ascii=False, indent=2), encoding="utf-8")
    print(JOBS)
    print(MANIFEST)
    print(f"jobs: {len(jobs)}")


if __name__ == "__main__":
    main()
