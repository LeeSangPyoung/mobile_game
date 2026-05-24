#!/usr/bin/env python3
# 보상 경제 시뮬레이터 — 10회 플레이스루로 골드/별 수급 vs 소모 검증.
# 핵심 질문: 별이 고갈돼 후반에 막히는가(데드락)? 골드는 균형인가?
import random

# ── 실제 상수 (prototype.html) ──
def upg_cost(lv):  # 업그레이드 lv→lv+1
    return int(1000 + lv*200 + lv*lv*150)
ENH_SUCCESS = [0, 0.90, 0.60, 0.40, 0.15, 0.05]  # lv→lv+1 성공률
ENH_COST_GOLD = 200
ENH_COST_STAR = 1
STAR_TO_GOLD = 100

# 챕터별 보스 클리어에 필요한 투자 티어
CH_REQ = {1:1, 2:1, 3:2, 4:2, 5:2, 6:3, 7:3, 8:3, 9:3, 10:4}
# 티어 → 목표 (업글 lv, 편성 장수 수, '선봉' 강화목표 lv) — 캠페인 클리어는 enh4 상한(만렙 enh6은 선택)
# 강화는 선봉 1~2명만 목표lv, 나머지는 enh2 정도(현실적 운용)
TIER = {
  0: dict(uAtk=0,  uDef=0,  gen=1, leadEnh=1, subEnh=1, leads=1),
  1: dict(uAtk=3,  uDef=2,  gen=3, leadEnh=2, subEnh=1, leads=1),
  2: dict(uAtk=7,  uDef=5,  gen=4, leadEnh=3, subEnh=2, leads=2),
  3: dict(uAtk=12, uDef=9,  gen=5, leadEnh=4, subEnh=2, leads=2),
  4: dict(uAtk=16, uDef=13, gen=6, leadEnh=4, subEnh=3, leads=3),
}

def upg_gold_to(uAtk, uDef):
    g = 0
    for lv in range(uAtk): g += upg_cost(lv)
    for lv in range(uDef): g += upg_cost(lv)
    return g

def enhance_one_to(target_lv):
    # 한 장수를 target_lv까지: 실패 시 레벨 하락 반영. (별, 골드, 시도수) 반환
    lv = 1; stars = 0; gold = 0; tries = 0
    guard = 0
    while lv < target_lv and guard < 2000:
        guard += 1
        stars += ENH_COST_STAR; gold += ENH_COST_GOLD; tries += 1
        rate = ENH_SUCCESS[lv] if lv < len(ENH_SUCCESS) else 0.03
        if random.random() < rate:
            lv += 1
        else:
            if lv > 1:
                lv = 1 + random.randint(0, lv-2)  # 하락
    return stars, gold, tries

def tier_cost(tier):
    """0→tier 누적 (gold, star). 강화는 몬테카를로 평균."""
    t = TIER[tier]
    gold = upg_gold_to(t['uAtk'], t['uDef'])
    star = 0
    # 등용: gen-1명 확보 (시작 1명)
    star += sum(random.choice([1,1,2]) for _ in range(max(0, t['gen']-1)))
    # 강화: 선봉 leads명 leadEnh, 나머지 subEnh
    for gi in range(t['gen']):
        tgt = t['leadEnh'] if gi < t['leads'] else t['subEnh']
        lv = 1; guard=0
        while lv < tgt and guard < 500:
            guard+=1; star += ENH_COST_STAR; gold += ENH_COST_GOLD
            rate = ENH_SUCCESS[lv] if lv < len(ENH_SUCCESS) else 0.03
            if random.random() < rate: lv += 1
            elif lv > 1: lv = 1 + random.randint(0, lv-2)
    return gold, star

def req_tier(ch, s):
    base = CH_REQ[ch]
    if s < 10:  # 챕터 전반은 한 단계 낮게(완화 구간)
        return max(base-1, CH_REQ.get(ch-1, 0))
    return base

def run_playthrough(rule):
    gold_pool = 1000; star_pool = 0
    invested = 0
    stuck_at = None
    minstar = 0; mingold = 1000
    # 미리 각 티어 누적비용 산정(이번 런의 RNG로)
    costs = {t: tier_cost(t) for t in range(5)}
    for ch in range(1, 11):
        for s in range(1, 21):
            need = req_tier(ch, s)
            # 필요 티어까지 점진 투자
            while invested < need:
                gnext, snext = costs[invested+1]
                gprev, sprev = costs[invested]
                dg, ds = gnext-gprev, snext-sprev
                if star_pool - ds < 0:
                    # 별 부족 = 데드락 (별은 골드로 못 삼)
                    if stuck_at is None: stuck_at = (ch, s)
                    break
                star_pool -= ds; gold_pool -= dg
                invested += 1
            if stuck_at: break
            # 스테이지 클리어 보상
            gidx = 1 + (ch-1)*20 + s
            rating = random.choices([1,2,3], weights=[0.3,0.45,0.25])[0]
            gold_pool += 100 + gidx*50 + rating*50
            star_pool += rating
            if rule == 'proposed':
                # 재클리어는 모델 밖. 무한모드 별도. 여기선 스테이지별 추가 없음.
                pass
            minstar = min(minstar, star_pool); mingold = min(mingold, gold_pool)
        if stuck_at: break
        if rule == 'proposed':
            # 챕터 클리어 보너스: 골드 + 별5 + 확정장수
            gold_pool += 800 + ch*500
            star_pool += 5
    return gold_pool, star_pool, stuck_at, minstar, mingold

def summarize(rule):
    stucks=0; fg=[]; fs=[]; mss=[]; mgs=[]
    for i in range(10):
        random.seed(1000+i)
        g,s,stuck,minstar,mingold = run_playthrough(rule)
        if stuck: stucks+=1
        fg.append(g); fs.append(s); mss.append(minstar); mgs.append(mingold)
    print(f"[{rule:9}] 데드락 {stucks}/10 | 최저별잔고 {min(mss)} | 최저골드잔고 {min(mgs):,} | 종료 평균 골드 {sum(fg)//10:,} 별 {sum(fs)//10}")
    return stucks

print("=== 10회 플레이스루 경제 시뮬 (스테이지별 점진 투자) ===")
summarize('current')
summarize('proposed')
print("\n데드락 = 후반에 별 부족으로 강화 못 해 진행 막힘 / 잔고 음수 = 자원 고갈")
