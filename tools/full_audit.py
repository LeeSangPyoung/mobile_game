#!/usr/bin/env python3
# 전체 감사 — 200스테이지 난이도·보상·경제를 실제 공식으로 전수 점검, 이상치 탐지.
import math, random

STAGES_PER_CH = 20
# 난이도 공식 (prototype.html makeGeneratedStage)
def enemyMult(ch, local): return 0.70 + (ch-1)*0.21 + (local-1)*0.024
def playerMult(ch, local): return 1.0 + (ch-1)*0.018
def aiLevel(ch, local):
    if local == 20: return min(5, ch+1)
    return min(5, max(1, round(1+(ch-1)*0.5) + (1 if local>15 else 0) - (1 if local<5 else 0)))
# 보상 (global idx 기준)
def gidx(ch, local): return 1 + (ch-1)*20 + local  # 튜토 offset 1
def goldFirst(ch, local, stars=3): return 100 + gidx(ch,local)*50 + stars*50
def goldReclear(ch, local, stars=3): return math.floor(goldFirst(ch,local,stars)*0.25)
def reclearStar(ch, local): return 1 + (gidx(ch,local)//40)
def chapterBonusGold(ch): return 800 + ch*500

# 적/아군 유효전력 (난이도 시뮬 모델)
ENEMY_MAX={0:29,1:30,2:30,3:30,4:30}; ENEMY_N={0:3,1:2,2:3,3:3,4:3}
PLAYER_HOME={0:52,1:52,2:56,3:58,4:56}
def stage_power(ch, local):
    variant = (local-1)%5
    if local==20:
        e = 52*(enemyMult(ch,local)+0.35)*(1+0.16*3); p=78*playerMult(ch,local)*(1+0.10*3)
    else:
        e = ENEMY_MAX[variant]*enemyMult(ch,local)*(1+0.16*(ENEMY_N[variant]-1))
        p = PLAYER_HOME[variant]*playerMult(ch,local)*(1+0.10*(ENEMY_N[variant]-1))
    e *= 1.18  # 수비 오버헤드
    return p, e

print("=== 전 200스테이지 감사 ===\n")

# 1) 난이도 단조성: 챕터 경계/스테이지에서 역전(난이도가 내려가는) 구간 점검
print("[1] 난이도 단조성 (적/아군 전력비 = 어려울수록↑)")
prev_ratio=None; anomalies=[]
ratios=[]
for ch in range(1,11):
    for local in range(1,21):
        p,e=stage_power(ch,local); r=e/p; ratios.append((ch,local,r))
# 챕터 보스 vs 다음 챕터 1장 (톱니 점검)
for ch in range(1,10):
    pb,eb=stage_power(ch,20); rb=eb/pb
    pn,en=stage_power(ch+1,1); rn=en/pn
    drop=(rb-rn)/rb*100
    flag = ' <- 낙폭 과대' if drop>45 else (' <- 낙폭 미미(완화부족)' if drop<8 else '')
    print(f"  {ch}ch보스 비{rb:.2f} → {ch+1}ch1장 비{rn:.2f}  (완화 {drop:.0f}%) {flag}")

# 2) 보상 곡선 이상치
print("\n[2] 보상 곡선")
for ch in [1,5,10]:
    print(f"  {ch}ch: 1장 첫클{goldFirst(ch,1)}G 재클{goldReclear(ch,1)}G/별{reclearStar(ch,1)}"
          f" | 보스 첫클{goldFirst(ch,20)}G + 챕터보너스{chapterBonusGold(ch)}G/별5")

# 3) AI 분포
print("\n[3] AI 레벨 분포(스테이지 수)")
from collections import Counter
aic=Counter()
for ch in range(1,11):
    for local in range(1,21): aic[aiLevel(ch,local)]+=1
for lv in sorted(aic): print(f"  AI{lv}: {aic[lv]}개")

# 4) 전력비 급변(인접 스테이지 점프) 점검
print("\n[4] 인접 스테이지 난이도 점프(>35% 상승)")
jumps=0
flat=[(c,l,r) for (c,l,r) in ratios]
for i in range(1,len(flat)):
    c0,l0,r0=flat[i-1]; c1,l1,r1=flat[i]
    if c1==c0 and (r1-r0)/r0>0.35:
        print(f"  {c1}ch {l0}→{l1}장: 비 {r0:.2f}→{r1:.2f}"); jumps+=1
if jumps==0: print("  (없음 — 챕터 내 매끄러움)")

# 5) 전력비 절대값 범위(클리어 가능성 감)
print("\n[5] 전력비 범위 (참고: ~1.0=무투자 한계, >2.0=고투자 필요)")
allr=[r for _,_,r in ratios]
print(f"  최소 {min(allr):.2f}(1ch1장) ~ 최대 {max(allr):.2f}(10ch보스), 평균 {sum(allr)/len(allr):.2f}")
# 비1.0 미만(무투자로도 쉬운) 스테이지 비율 — 너무 많으면 지루
easy=sum(1 for r in allr if r<1.0)
print(f"  비<1.0(쉬움) 스테이지: {easy}/200 ({easy*200//200//2}%) ... {easy/2:.0f}%")

# ── 개선안 검증 ──
def em2(ch,local): return 0.78 + (ch-1)*0.19 + (local-1)*0.034  # 골 올리고 챕터증분 약간↓, 챕터내 가파르게
def bossBonus(): return 0.26
def sp2(ch,local):
    variant=(local-1)%5
    if local==20:
        e=52*(em2(ch,local)+bossBonus())*(1+0.16*3); p=78*playerMult(ch,local)*(1+0.10*3)
    else:
        e=ENEMY_MAX[variant]*em2(ch,local)*(1+0.16*(ENEMY_N[variant]-1)); p=PLAYER_HOME[variant]*playerMult(ch,local)*(1+0.10*(ENEMY_N[variant]-1))
    return p, e*1.18
print("\n=== [개선안] em=0.78+(ch-1)*0.19+(local-1)*0.034, boss+0.26 ===")
r2=[]
for ch in range(1,11):
    for local in range(1,21):
        p,e=sp2(ch,local); r2.append(e/p)
for ch in range(1,10):
    pb,eb=sp2(ch,20); pn,en=sp2(ch+1,1); drop=(eb/pb-en/pn)/(eb/pb)*100
    print(f"  {ch}ch보스 {eb/pb:.2f}→{ch+1}ch1장 {en/pn:.2f} (완화 {drop:.0f}%)")
easy2=sum(1 for r in r2 if r<1.0)
print(f"  범위 {min(r2):.2f}~{max(r2):.2f} 평균 {sum(r2)/len(r2):.2f} | 쉬움(<1.0) {easy2/2:.0f}%")
