#!/usr/bin/env python3
# 삼국 난이도 시뮬레이터 — 전투력/스테이지 밸런스 검증
# prototype.html 의 실제 상수/병력 템플릿을 반영. Lanchester 제곱법칙 기반 추상 전투.
import math

DMG_RATE = 0.18
STAR_MULT = [1.0, 1.0, 1.2, 1.4, 1.7, 2.0]      # index=stars 1~5
ENH_MULT  = [1.0, 1.0, 1.2, 1.4, 1.6, 1.8, 2.0] # index=lv 1~6
UPG = {'unitAtk':0.06, 'unitDef':0.05, 'castleAtk':0.08, 'castleDef':0.10, 'prodRate':0.10}

# 생성 스테이지 템플릿 — prototype.html 그대로. (창,기,궁) 합.
# 다성 스테이지는 성 하나씩 순차 점령 → '가장 강한 단일 적 성'이 실질 난이도.
PLAYER_HOME = {0:52, 1:52, 2:56, 3:58, 4:56, 'boss':78}
ENEMY_MAX   = {0:29, 1:30, 2:30, 3:30, 4:30, 'boss':52}   # 최강 단일 적 성
ENEMY_N     = {0:3,  1:2,  2:3,  3:3,  4:3,  'boss':4}     # 적 성 개수

def enemy_count(ch, local, variant, scaling):
    mx = ENEMY_MAX['boss'] if local==20 else ENEMY_MAX[variant]
    n  = ENEMY_N['boss']  if local==20 else ENEMY_N[variant]
    em = scaling['enemyMult'](ch, local)
    if local==20: em += 0.26  # 보스 성 추가 보정
    # 순차 점령: 최강 성 기준 + 성 수만큼 누적 부담(완만)
    return mx * em * (1 + 0.16*(n-1))

def player_home(ch, local, variant, scaling):
    base = PLAYER_HOME['boss'] if local==20 else PLAYER_HOME[variant]
    pm = scaling['playerMult'](ch, local)
    n  = ENEMY_N['boss']  if local==20 else ENEMY_N[variant]
    # 점령하며 아군도 증강(완만)
    return base * pm * (1 + 0.10*(n-1))

# ── 투자 수준 → 플레이어 공격 배수 ──
# 업그레이드 + 장수(별/강화) + 상성 운용 스킬
INVEST = {
    0: dict(uAtk=0, uDef=0, gStars=3, gEnh=1, gCount=1, label='무투자(시작장수만)'),
    1: dict(uAtk=3, uDef=2, gStars=3, gEnh=2, gCount=3, label='가벼운 투자'),
    2: dict(uAtk=8, uDef=6, gStars=3, gEnh=3, gCount=5, label='중간 투자'),
    3: dict(uAtk=14,uDef=11,gStars=4, gEnh=5, gCount=6, label='집중 투자'),
    4: dict(uAtk=20,uDef=20,gStars=5, gEnh=6, gCount=6, label='거의 만렙'),
}
# 장수 기본 버프(공격형 대표 ~0.10 unitAtk). 별×강화 배수 적용. 편성 장수 일부만 전투 기여.
STAR_FLAT = [0, 0, 0.012, 0.025, 0.045, 0.075]  # C안: 별 플랫 바닥값(unitAtk)
def player_mult(inv):
    iv = INVEST[inv]
    uAtk = 1 + UPG['unitAtk']*iv['uAtk']
    # 장수 병공 실효버프 = base*star*enh + 별플랫, 편성 인원 비례(선봉 위주 0.6 가중)
    gAtk = 0.10 * STAR_MULT[iv['gStars']] * ENH_MULT[iv['gEnh']] + STAR_FLAT[iv['gStars']]
    gbuff = 1 + gAtk * (0.5 + 0.08*iv['gCount'])
    return uAtk * gbuff
def player_def_mult(inv):
    iv = INVEST[inv]
    return 1 + UPG['unitDef']*iv['uDef']

def battle_margin(P_troops, P_off, P_def, E_troops, E_off):
    # Lanchester 제곱: 유효전력 = 병력 × 공격배수, 방어배수는 받는 피해 감쇠
    PF = P_troops * P_off
    EF = E_troops * E_off / P_def
    if PF <= EF: return -(EF-PF)/max(PF,1)   # 패배(음수 마진)
    return math.sqrt(max(0, 1 - (EF/PF)**2))  # 생존 비율 0~1

def classify(m):
    if m < 0:    return '패배(투자부족)'
    if m < 0.12: return '아슬아슬'
    if m < 0.35: return '빡빡(투자필요)'
    if m < 0.60: return '적당'
    return '너무쉬움'

# ── 시나리오 정의 ──
def scaling_current():
    return dict(
        enemyMult = lambda ch,l: 0.75 + (ch-1)*0.08 + l*0.018,
        playerMult= lambda ch,l: 1.10 + (ch-1)*0.10 + l*0.014,
        # Layer B 전역보정
        enemyEase = lambda ch: (ch-1)*0.04,
        playerBoost=lambda ch: (ch-1)*0.03,
        enemyGenBuff=lambda ch: 1.0,   # 적 장수 버프 없음
        aiFactor = lambda ch,l: 1 + 0.03*min(4, ch),  # AI 캡4
    )
def scaling_proposed(P):
    return dict(
        enemyMult = lambda ch,l: P['eBase'] + (ch-1)*P['ePer'] + (l-1)*P['eLocal'],
        playerMult= lambda ch,l: 1.0 + (ch-1)*P['pPer'],
        enemyEase = lambda ch: 0.0,      # 완화 제거
        playerBoost=lambda ch: 0.0,
        enemyGenBuff=lambda ch: 1 + P['egBase']*(ch),   # 적 장수 버프 ON(챕터비례)
        aiFactor = lambda ch,l: 1 + 0.04*min(5, round(1+(ch-1)*0.5)),  # AI 5캡
    )

def run(scaling, label):
    print(f"\n===== {label} =====")
    print(f"{'Ch':>2} {'St':>3} | " + " | ".join(f"{INVEST[i]['label'][:6]:>6}" for i in range(5)))
    # 대표 스테이지: 각 챕터의 5/10/20(보스)
    rows = []
    for ch in range(1, 11):
        for local in (5, 10, 20):
            variant = (local-1)%5 if local!=20 else 'boss'
            E = enemy_count(ch, local, variant, scaling)
            # 완화/AI/적장수 보정
            E = E * (1 + (-scaling['enemyEase'](ch))) if 'enemyEase' in scaling else E
            E = E * scaling['enemyGenBuff'](ch) * scaling['aiFactor'](ch, local)
            E = E * 1.18  # 수비측 이점(성벽/반격/출진 오버헤드)
            cells = []
            for inv in range(5):
                P = player_home(ch, local, variant, scaling)
                P = P * (1 + scaling.get('playerBoost', lambda c:0)(ch))
                Poff = player_mult(inv); Pdef = player_def_mult(inv)
                m = battle_margin(P, Poff, Pdef, E, 1.0)
                cells.append(m)
            rows.append((ch, local, cells))
            tag = {5:'중반',10:'중후',20:'보스'}[local]
            print(f"{ch:>2} {tag:>3} | " + " | ".join(f"{classify(m):>6}" for m in cells))
    return rows

def curve(scaling, label):
    # 각 챕터 보스/중반에서 '클리어 최소 투자수준'과 '만렙 시 마진' 출력
    print(f"\n===== {label} — 클리어 최소투자 & 만렙마진 =====")
    print(f"{'Ch':>2} | {'s5필요':>6} {'보스필요':>7} | {'보스@만렙':>9}")
    for ch in range(1, 11):
        need = {}
        for tag, local in (('s5',5),('boss',20)):
            variant = (local-1)%5 if local!=20 else 'boss'
            E = enemy_count(ch, local, variant, scaling)
            E = E * scaling['enemyGenBuff'](ch) * scaling['aiFactor'](ch, local) * 1.18
            E *= (1 - scaling.get('enemyEase', lambda c:0)(ch))
            mininv = None; maxmargin = None
            for inv in range(5):
                P = player_home(ch, local, variant, scaling) * (1 + scaling.get('playerBoost', lambda c:0)(ch))
                m = battle_margin(P, player_mult(inv), player_def_mult(inv), E, 1.0)
                if m >= 0.08 and mininv is None: mininv = inv
                if inv==4: maxmargin = m
            need[tag] = (mininv, maxmargin)
        s5inv = need['s5'][0]; binv,bmax = need['boss']
        f = lambda v: '불가' if v is None else f"inv{v}"
        print(f"{ch:>2} | {f(s5inv):>6} {f(binv):>7} | {(('%.2f'%bmax) if bmax is not None else 'NA'):>9}")

cur = scaling_current()
curve(cur, "현재 (CURRENT)")

for P in [
  dict(eBase=0.78, ePer=0.19, eLocal=0.034, pPer=0.018, egBase=0.0),
]:
    curve(scaling_proposed(P), f"제안 {P}")
