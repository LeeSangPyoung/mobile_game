#!/usr/bin/env python3
from __future__ import annotations

import hashlib
import json
import math
import random
from pathlib import Path

from PIL import Image, ImageDraw


ROOT = Path(__file__).resolve().parents[1]
JOBS = ROOT / "tmp" / "mobile_generals_200" / "jobs_fullbody_200.jsonl"
OUT = ROOT / "assets" / "generals" / "mobile_fullbody"
RAW = ROOT / "tmp" / "mobile_generals_200" / "raw"
SHEET = ROOT / "tmp" / "mobile_generals_200" / "procedural_contact_sheet.png"
W, H = 640, 768
S = 3

OUT.mkdir(parents=True, exist_ok=True)
SHEET.parent.mkdir(parents=True, exist_ok=True)

PALETTES = {
    "위": {
        "main": (50, 83, 126, 255),
        "dark": (31, 43, 64, 255),
        "accent": (178, 53, 58, 255),
        "cloth": (219, 223, 219, 255),
        "metal": (142, 154, 165, 255),
    },
    "촉": {
        "main": (79, 118, 67, 255),
        "dark": (42, 72, 47, 255),
        "accent": (185, 72, 49, 255),
        "cloth": (230, 218, 182, 255),
        "metal": (151, 151, 131, 255),
    },
    "오": {
        "main": (27, 105, 103, 255),
        "dark": (25, 59, 74, 255),
        "accent": (184, 57, 54, 255),
        "cloth": (236, 221, 190, 255),
        "metal": (151, 134, 95, 255),
    },
    "군웅": {
        "main": (158, 107, 45, 255),
        "dark": (82, 57, 43, 255),
        "accent": (150, 42, 48, 255),
        "cloth": (228, 211, 173, 255),
        "metal": (144, 122, 91, 255),
    },
    "황건": {
        "main": (130, 81, 152, 255),
        "dark": (72, 52, 88, 255),
        "accent": (219, 178, 51, 255),
        "cloth": (239, 204, 77, 255),
        "metal": (134, 119, 92, 255),
    },
    "기타": {
        "main": (94, 86, 77, 255),
        "dark": (48, 45, 44, 255),
        "accent": (154, 60, 72, 255),
        "cloth": (225, 218, 201, 255),
        "metal": (142, 137, 130, 255),
    },
}

SKIN = [
    (229, 177, 132, 255),
    (239, 190, 145, 255),
    (216, 151, 108, 255),
    (198, 132, 92, 255),
]
OUTLINE = (40, 34, 31, 255)
HAIR = [(38, 31, 29, 255), (55, 40, 32, 255), (84, 59, 40, 255), (116, 81, 48, 255)]
WHITE = (255, 249, 235, 255)

FEMALE = {
    "sun_luban", "sun_luyu", "daqiao", "xiaoqiao", "lian_shi", "guan_yinping",
    "diao_chan", "zou_shi",
}
RULER = {
    "cao_cao", "liu_bei", "sun_quan", "sun_jian", "sun_ce", "yuan_shao", "yuan_shu",
    "dong_zhuo", "liu_biao", "liu_zhang", "liu_yao", "liu_yu", "tao_qian",
    "gongsun_zan", "emperor_xian", "he_jin", "wang_yun", "cao_pi", "cao_rui",
    "liu_shan",
}
STRATEGIST = {
    "guo_jia", "pang_tong", "sima_yi", "zhuge_liang", "zhou_yu", "lu_xun", "cheng_yu",
    "xun_yu", "xun_you", "jia_xu", "man_chong", "zhong_yao", "zhong_hui", "lu_su",
    "zhang_zhao", "zhang_hong", "bu_zhi", "kan_ze", "yu_fan", "fa_zheng", "jian_yong",
    "mi_zhu", "sun_qian", "ma_su", "ma_liang", "fei_yi", "dong_yun", "jiang_wan",
    "huang_quan", "zhang_song", "li_hui", "zhuge_zhan", "zhuge_jin", "zhuge_dan",
    "tian_feng", "ju_shou", "shen_pei", "feng_ji", "guo_tu", "xin_ping", "xin_pi",
    "kong_rong", "yan_pu", "cheng_gongying", "li_ru", "kuai_yue", "kuai_liang",
    "mao_jie", "liu_ye", "li_soon_placeholder",
}
ARCHER = {
    "huang_zhong", "xiahou_yuan", "taishi_ci", "cao_xiu", "ding_feng", "han_dang",
    "ma_zhong_wu", "quan_cong", "sun_huan", "liu_feng", "yan_yan",
}
HEAVY = {
    "dian_wei", "xu_chu", "dong_zhuo", "meng_huo", "wen_chou", "yan_liang", "zhang_fei",
    "hua_xiong", "guan_hai", "hu_che_er", "sha_moke", "zhou_cang",
}
MYSTIC = {"hua_tuo", "zuo_ci", "yu_ji", "zhang_jiao"}

WEAPON_OVERRIDES = {
    "guan_yu": "glaive",
    "zhang_fei": "spear",
    "zhao_yun": "spear",
    "ma_chao": "spear",
    "lu_bu": "halberd",
    "dian_wei": "axe",
    "xu_chu": "mace",
    "xu_huang": "axe",
    "huang_zhong": "bow",
    "xiahou_yuan": "bow",
    "zhuge_liang": "fan",
    "sima_yi": "fan",
    "pang_tong": "staff",
    "guo_jia": "scroll",
    "hua_tuo": "staff",
    "zuo_ci": "staff",
    "yu_ji": "staff",
    "zhang_jiao": "staff",
}


def load_items() -> list[dict[str, str]]:
    items = []
    for line in JOBS.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        row = json.loads(line)
        items.append({"slug": row["slug"], "name": row["ko"], "force": row["force"]})
    return items


def seed_for(slug: str) -> int:
    return int(hashlib.sha256(slug.encode("utf-8")).hexdigest()[:16], 16)


def role_for(slug: str, force: str) -> str:
    if slug in FEMALE:
        return "female"
    if slug in MYSTIC:
        return "mystic"
    if force == "황건":
        return "yellow"
    if slug in STRATEGIST:
        return "strategist"
    if slug in RULER:
        return "ruler"
    if slug in ARCHER:
        return "archer"
    if slug in HEAVY:
        return "heavy"
    return "warrior"


class Sprite:
    def __init__(self, item: dict[str, str]) -> None:
        self.slug = item["slug"]
        self.name = item["name"]
        self.force = item["force"]
        self.role = role_for(self.slug, self.force)
        self.rng = random.Random(seed_for(self.slug))
        self.palette = PALETTES[self.force]
        self.skin = self.rng.choice(SKIN)
        self.hair = self.rng.choice(HAIR)
        self.img = Image.new("RGBA", (W * S, H * S), (0, 0, 0, 0))
        self.d = ImageDraw.Draw(self.img)
        self.cx = 320 + self.rng.randint(-7, 7)
        self.head_y = 190 + self.rng.randint(-5, 5)
        self.head_w = 126 + self.rng.randint(-8, 8)
        self.head_h = 138 + self.rng.randint(-7, 7)
        if self.role == "heavy":
            self.head_w += 8
            self.body_w = 150 + self.rng.randint(-6, 10)
        elif self.role in {"strategist", "female", "mystic"}:
            self.body_w = 120 + self.rng.randint(-8, 8)
        else:
            self.body_w = 132 + self.rng.randint(-8, 10)

    def s(self, value: float) -> int:
        return int(round(value * S))

    def box(self, xy: tuple[float, float, float, float]) -> tuple[int, int, int, int]:
        return tuple(self.s(v) for v in xy)

    def line(self, pts: list[tuple[float, float]], fill, width: float, joint: str = "curve") -> None:
        self.d.line([(self.s(x), self.s(y)) for x, y in pts], fill=fill, width=self.s(width), joint=joint)

    def ellipse(self, xy, fill, outline=OUTLINE, width=4) -> None:
        self.d.ellipse(self.box(xy), fill=fill, outline=outline, width=self.s(width))

    def rect(self, xy, fill, outline=OUTLINE, width=4, radius=14) -> None:
        self.d.rounded_rectangle(self.box(xy), radius=self.s(radius), fill=fill, outline=outline, width=self.s(width))

    def poly(self, pts, fill, outline=OUTLINE, width=4) -> None:
        scaled = [(self.s(x), self.s(y)) for x, y in pts]
        self.d.polygon(scaled, fill=fill)
        self.d.line(scaled + [scaled[0]], fill=outline, width=self.s(width), joint="curve")

    def capsule(self, p1, p2, color, width=28, outline=OUTLINE, outline_extra=8) -> None:
        self.line([p1, p2], outline, width + outline_extra)
        for x, y in (p1, p2):
            self.ellipse((x - (width + outline_extra) / 2, y - (width + outline_extra) / 2,
                          x + (width + outline_extra) / 2, y + (width + outline_extra) / 2), outline, outline, 0)
        self.line([p1, p2], color, width)
        for x, y in (p1, p2):
            self.ellipse((x - width / 2, y - width / 2, x + width / 2, y + width / 2), color, color, 0)

    def weapon_type(self) -> str:
        if self.slug in WEAPON_OVERRIDES:
            return WEAPON_OVERRIDES[self.slug]
        if self.role == "strategist":
            return self.rng.choice(["fan", "scroll", "staff"])
        if self.role in {"mystic", "yellow"}:
            return "staff"
        if self.role == "archer":
            return "bow"
        if self.role == "heavy":
            return self.rng.choice(["axe", "mace", "glaive"])
        if self.role == "female":
            return self.rng.choice(["fan", "sword", "bow"])
        if self.role == "ruler":
            return self.rng.choice(["sword", "scroll"])
        return self.rng.choice(["spear", "sword", "glaive", "axe"])

    def draw_weapon_back(self, kind: str) -> None:
        metal = self.palette["metal"]
        wood = (96, 62, 38, 255)
        if kind in {"spear", "glaive", "halberd"}:
            x1 = self.cx - 88 + self.rng.randint(-10, 10)
            x2 = self.cx + 70 + self.rng.randint(-7, 7)
            self.line([(x1, 610), (x2, 128)], OUTLINE, 13)
            self.line([(x1, 610), (x2, 128)], wood, 7)
            if kind == "spear":
                self.poly([(x2, 108), (x2 - 18, 150), (x2 + 18, 150)], metal, OUTLINE, 4)
            elif kind == "glaive":
                self.poly([(x2, 110), (x2 - 8, 175), (x2 + 43, 153), (x2 + 25, 125)], metal, OUTLINE, 4)
            else:
                self.poly([(x2, 111), (x2 - 26, 170), (x2 + 31, 157), (x2 + 20, 126)], metal, OUTLINE, 4)
                self.poly([(x2 - 4, 127), (x2 - 50, 151), (x2 - 14, 171)], metal, OUTLINE, 4)
        elif kind == "bow":
            x = self.cx + 87
            self.d.arc(self.box((x - 42, 206, x + 46, 556)), 266, 94, fill=OUTLINE, width=self.s(13))
            self.d.arc(self.box((x - 36, 214, x + 39, 548)), 266, 94, fill=(122, 75, 44, 255), width=self.s(7))
            self.line([(x + 25, 225), (x + 25, 538)], (220, 205, 176, 255), 3)
        elif kind == "staff":
            x = self.cx + 82
            self.line([(x, 575), (x - 18, 155)], OUTLINE, 13)
            self.line([(x, 575), (x - 18, 155)], (93, 61, 41, 255), 7)
            self.ellipse((x - 41, 122, x + 5, 168), self.palette["accent"], OUTLINE, 4)

    def draw_weapon_front(self, kind: str) -> None:
        metal = self.palette["metal"]
        if kind == "sword":
            hx, hy = self.cx + 78, 420
            self.poly([(hx, hy - 124), (hx - 13, hy + 3), (hx + 13, hy + 3)], (197, 205, 205, 255), OUTLINE, 4)
            self.rect((hx - 32, hy - 4, hx + 32, hy + 14), self.palette["accent"], OUTLINE, 4, 6)
            self.rect((hx - 9, hy + 10, hx + 9, hy + 70), (82, 51, 36, 255), OUTLINE, 4, 7)
        elif kind == "axe":
            x, y = self.cx + 74, 390
            self.line([(x - 18, y + 155), (x, y - 70)], OUTLINE, 13)
            self.line([(x - 18, y + 155), (x, y - 70)], (93, 61, 41, 255), 7)
            self.poly([(x - 2, y - 88), (x - 55, y - 44), (x - 12, y - 25), (x + 18, y - 38), (x + 45, y - 58)], metal, OUTLINE, 4)
        elif kind == "mace":
            x, y = self.cx + 80, 386
            self.line([(x - 22, y + 140), (x, y - 38)], OUTLINE, 15)
            self.line([(x - 22, y + 140), (x, y - 38)], (95, 65, 42, 255), 8)
            self.ellipse((x - 39, y - 84, x + 37, y - 12), metal, OUTLINE, 5)
            for a in range(0, 360, 60):
                px = x + math.cos(math.radians(a)) * 39
                py = y - 48 + math.sin(math.radians(a)) * 35
                self.ellipse((px - 6, py - 6, px + 6, py + 6), OUTLINE, OUTLINE, 0)
        elif kind == "fan":
            x, y = self.cx + 83, 382
            ribs = [(x, y)]
            for i in range(7):
                angle = math.radians(207 + i * 18)
                ribs.append((x + math.cos(angle) * 78, y + math.sin(angle) * 78))
            fan_pts = ribs[1:] + [(x, y)]
            self.poly(fan_pts, (237, 226, 199, 255), OUTLINE, 4)
            for p in ribs[1:]:
                self.line([(x, y), p], (159, 124, 85, 255), 2)
            self.ellipse((x - 10, y - 10, x + 10, y + 10), self.palette["accent"], OUTLINE, 3)
        elif kind == "scroll":
            x, y = self.cx + 78, 381
            self.rect((x - 30, y - 24, x + 45, y + 28), (229, 211, 164, 255), OUTLINE, 4, 10)
            self.ellipse((x - 39, y - 26, x - 14, y + 30), (198, 154, 88, 255), OUTLINE, 3)

    def draw_body(self) -> None:
        p = self.palette
        cx = self.cx
        bw = self.body_w
        y0, y1 = 286, 474
        if self.role in {"strategist", "mystic", "female"}:
            self.poly([(cx - bw / 2, y0), (cx + bw / 2, y0), (cx + bw * 0.62, y1), (cx - bw * 0.62, y1)], p["cloth"], OUTLINE, 5)
            self.poly([(cx - bw * 0.42, y0 + 18), (cx, y1 - 15), (cx + bw * 0.42, y0 + 18)], p["main"], OUTLINE, 4)
            self.rect((cx - bw * 0.46, y0 + 92, cx + bw * 0.46, y0 + 120), p["accent"], OUTLINE, 4, 9)
        else:
            self.rect((cx - bw / 2, y0, cx + bw / 2, y1), p["main"], OUTLINE, 5, 22)
            self.poly([(cx - bw * 0.38, y0 + 18), (cx + bw * 0.38, y0 + 18), (cx + bw * 0.28, y0 + 88), (cx - bw * 0.28, y0 + 88)], p["metal"], OUTLINE, 4)
            self.rect((cx - bw * 0.45, y0 + 94, cx + bw * 0.45, y0 + 120), p["accent"], OUTLINE, 4, 8)
            for i in (-1, 0, 1):
                self.rect((cx + i * 34 - 13, y0 + 128, cx + i * 34 + 13, y0 + 176), p["dark"], OUTLINE, 3, 6)
        if self.role == "ruler":
            self.poly([(cx - bw * 0.62, y0 + 7), (cx - bw * 0.86, y1 + 55), (cx - bw * 0.48, y1 + 42)], p["dark"], OUTLINE, 4)
        if self.role == "yellow":
            self.rect((cx - bw * 0.54, y0 + 28, cx + bw * 0.54, y0 + 54), PALETTES["황건"]["cloth"], OUTLINE, 4, 10)

    def draw_limbs(self) -> None:
        p = self.palette
        cx = self.cx
        shoulder_y = 320
        left_hand = (cx - self.body_w * 0.72, 421 + self.rng.randint(-12, 10))
        right_hand = (cx + self.body_w * 0.72, 414 + self.rng.randint(-10, 14))
        if self.role == "heavy":
            arm_w = 33
        else:
            arm_w = 27
        self.capsule((cx - self.body_w * 0.48, shoulder_y), left_hand, p["cloth"], arm_w)
        self.capsule((cx + self.body_w * 0.48, shoulder_y), right_hand, p["cloth"], arm_w)
        self.ellipse((left_hand[0] - 18, left_hand[1] - 17, left_hand[0] + 18, left_hand[1] + 17), self.skin, OUTLINE, 4)
        self.ellipse((right_hand[0] - 18, right_hand[1] - 17, right_hand[0] + 18, right_hand[1] + 17), self.skin, OUTLINE, 4)
        hip_y = 463
        left_knee = (cx - 46, 548 + self.rng.randint(-6, 8))
        right_knee = (cx + 45, 546 + self.rng.randint(-7, 8))
        left_foot = (cx - 65, 640)
        right_foot = (cx + 65, 640)
        leg_col = p["dark"]
        self.capsule((cx - 38, hip_y), left_knee, leg_col, 33)
        self.capsule(left_knee, left_foot, leg_col, 31)
        self.capsule((cx + 38, hip_y), right_knee, leg_col, 33)
        self.capsule(right_knee, right_foot, leg_col, 31)
        self.rect((left_foot[0] - 42, left_foot[1] - 21, left_foot[0] + 22, left_foot[1] + 18), (55, 43, 36, 255), OUTLINE, 4, 13)
        self.rect((right_foot[0] - 22, right_foot[1] - 21, right_foot[0] + 42, right_foot[1] + 18), (55, 43, 36, 255), OUTLINE, 4, 13)

    def draw_head(self) -> None:
        cx = self.cx
        hw, hh = self.head_w, self.head_h
        x0, y0, x1, y1 = cx - hw / 2, self.head_y - hh / 2, cx + hw / 2, self.head_y + hh / 2
        self.ellipse((x0, y0, x1, y1), self.skin, OUTLINE, 5)
        cap = self.role in {"strategist", "mystic", "ruler"} or self.rng.random() < 0.28
        if self.role == "yellow":
            self.rect((x0 - 2, y0 + 12, x1 + 2, y0 + 48), PALETTES["황건"]["cloth"], OUTLINE, 4, 16)
            self.poly([(cx - 16, y0 + 12), (cx + 26, y0 - 24), (cx + 53, y0 + 26)], PALETTES["황건"]["cloth"], OUTLINE, 4)
        elif cap:
            hat_col = self.palette["dark"]
            self.rect((x0 + 9, y0 - 4, x1 - 9, y0 + 46), hat_col, OUTLINE, 4, 14)
            if self.role in {"strategist", "mystic"}:
                self.rect((cx - 17, y0 - 28, cx + 17, y0 + 18), hat_col, OUTLINE, 4, 7)
        else:
            self.rect((x0 + 4, y0 + 5, x1 - 4, y0 + 45), self.palette["metal"], OUTLINE, 4, 18)
            self.poly([(cx - 15, y0 + 8), (cx, y0 - 26), (cx + 15, y0 + 8)], self.palette["accent"], OUTLINE, 4)
        if self.role == "female":
            self.ellipse((x0 - 24, y0 + 32, x0 + 22, y0 + 100), self.hair, OUTLINE, 3)
            self.ellipse((x1 - 22, y0 + 32, x1 + 24, y0 + 100), self.hair, OUTLINE, 3)
        elif not cap and self.rng.random() < 0.35:
            self.ellipse((cx - 17, y0 - 35, cx + 17, y0 - 5), self.hair, OUTLINE, 3)
        eye_y = self.head_y - 6
        eye_dx = 25
        self.ellipse((cx - eye_dx - 10, eye_y - 10, cx - eye_dx + 10, eye_y + 12), (22, 23, 25, 255), (22, 23, 25, 255), 0)
        self.ellipse((cx + eye_dx - 10, eye_y - 10, cx + eye_dx + 10, eye_y + 12), (22, 23, 25, 255), (22, 23, 25, 255), 0)
        self.ellipse((cx - eye_dx - 4, eye_y - 7, cx - eye_dx + 2, eye_y - 1), WHITE, WHITE, 0)
        self.ellipse((cx + eye_dx - 4, eye_y - 7, cx + eye_dx + 2, eye_y - 1), WHITE, WHITE, 0)
        brow_col = self.hair
        self.line([(cx - 44, eye_y - 24), (cx - 17, eye_y - 28)], brow_col, 5)
        self.line([(cx + 17, eye_y - 28), (cx + 44, eye_y - 24)], brow_col, 5)
        mouth_y = self.head_y + 35
        if self.slug in {"zhang_fei", "dian_wei", "xu_chu", "dong_zhuo", "hua_xiong", "meng_huo"}:
            self.ellipse((cx - 18, mouth_y - 8, cx + 18, mouth_y + 20), (70, 28, 31, 255), OUTLINE, 3)
        else:
            self.d.arc(self.box((cx - 23, mouth_y - 10, cx + 23, mouth_y + 17)), 20, 160, fill=OUTLINE, width=self.s(4))
        beard = self.slug in HEAVY or self.rng.random() < (0.24 if self.role in {"warrior", "ruler"} else 0.08)
        if beard:
            self.poly([(cx - 38, self.head_y + 36), (cx + 38, self.head_y + 36), (cx + 21, self.head_y + 76), (cx - 21, self.head_y + 76)], self.hair, OUTLINE, 3)
            self.line([(cx - 39, self.head_y + 23), (cx - 11, self.head_y + 31)], self.hair, 7)
            self.line([(cx + 11, self.head_y + 31), (cx + 39, self.head_y + 23)], self.hair, 7)
        if self.slug == "xiahou_dun":
            self.line([(cx - 42, eye_y - 8), (cx - 8, eye_y + 8)], OUTLINE, 7)
            self.ellipse((cx - 35, eye_y - 16, cx - 12, eye_y + 11), OUTLINE, OUTLINE, 0)

    def render(self) -> Image.Image:
        kind = self.weapon_type()
        self.draw_weapon_back(kind)
        self.draw_limbs()
        self.draw_body()
        self.draw_weapon_front(kind)
        self.draw_head()
        return self.img.resize((W, H), Image.Resampling.LANCZOS)


def make_contact_sheet(paths: list[Path]) -> None:
    thumb_w, thumb_h = 160, 192
    cols = 10
    rows = math.ceil(len(paths) / cols)
    sheet = Image.new("RGBA", (cols * thumb_w, rows * thumb_h), (246, 241, 231, 255))
    for i, path in enumerate(paths):
        im = Image.open(path).convert("RGBA")
        im.thumbnail((thumb_w - 10, thumb_h - 10), Image.Resampling.LANCZOS)
        x = (i % cols) * thumb_w + (thumb_w - im.width) // 2
        y = (i // cols) * thumb_h + (thumb_h - im.height) // 2
        sheet.alpha_composite(im, (x, y))
    sheet.convert("RGB").save(SHEET)


def main() -> None:
    items = load_items()
    paths = []
    preserved = 0
    for idx, item in enumerate(items, 1):
        path = OUT / f"{item['slug']}.png"
        raw_path = RAW / f"{item['slug']}.png"
        if raw_path.exists() and path.exists():
            preserved += 1
        else:
            sprite = Sprite(item).render()
            sprite.save(path)
        paths.append(path)
        if idx % 25 == 0:
            print(f"rendered {idx}/200")
    make_contact_sheet(paths)
    print(f"written: {len(paths)}")
    print(f"preserved_ai_source: {preserved}")
    print(f"assets: {OUT}")
    print(f"sheet: {SHEET}")


if __name__ == "__main__":
    main()
