// duel.js — 일기토(1v1) 서브게임 순수 엔진
//
// 목표: 서버·호스트·게스트가 공유하는 결정론 룰. 브라우저 API(DOM/canvas/입력) 의존 0.
//   입력은 '오차값(err)'만 받는다 → 조작은 각 클라이언트 로컬, 판정은 이 엔진 한 곳.
//   그래서 실시간 조작 서브게임인데도 멀티 동기화가 가위바위보만큼 싸다.
//
// 규칙(v1):
//   1) 매 라운드 양쪽이 '선(target)'에 마커를 멈춘다 → 오차 err = |마커 - 선| (바 길이 비율, 0=완벽)
//   2) 판정 존(zone)은 무력이 낮은 쪽이 더 넓다(열세 보정). 존 밖이면 헛손질.
//   3) 둘 다 존 안이면 정규화 오차(err/zone)가 작은 쪽이 때린다 — 존 폭이 달라도 공정.
//   4) 데미지는 '때린 쪽 무력 / 맞은 쪽 무력'에 비례. HP는 양쪽 동일.
//      → 여포가 동탁을 3대, 동탁이 여포를 7~8대. 격차는 타수로 표현되고 실력으로 뒤집을 수 있다.
//
// 아직 메인 게임에 붙이지 않음 — duel.html 로 단독 검증 후 이식.

import { mulberry32 } from './engine.js';

export const DUEL_DEFAULTS = {
  hp: 100,            // 양쪽 동일 체력
  dmgBase: 28,        // 동무력(1:1) 기준 1타 데미지 → 4대면 KO
  dmgExp: 1.3,        // 무력비 증폭 지수. 1.0=선형, 클수록 강자가 더 아프게 때린다
  //  여포(100)→동탁(74): 2~3대 / 동탁→여포: 4~6대  ← 이 체감을 만드는 값
  dmgClamp: [10, 55], // 1타 데미지 상·하한 (1대컷/10대컷 방지)
  accBonus: 0.4,      // 정확도 보너스 — 존 정중앙이면 데미지 +40%
  critNorm: 0.15,     // 정규화 오차가 이보다 작으면 크리티컬
  critMult: 1.6,
  zoneBase: 0.14,     // 판정 존 반폭(바 길이 비율) — 동무력 기준
  //  ⚠️ 입력 지연(누름→표시 왕복 40~60ms)이 바 폭의 7~9%를 먹는다. 존을 이보다 넉넉히.
  zoneHandicap: 0.5,  // 열세 보정 지수. 0=보정없음, 0.5=무력비 제곱근만큼 존 확대
  zoneClamp: [0.6, 1.7],
  maxRounds: 14,      // 무한 방지 — 초과 시 남은 HP로 판정
};

// 판정 존 반폭 — 무력이 상대보다 낮으면 넓어진다(열세 보정)
export function zoneFor(warMe, warOpp, o = DUEL_DEFAULTS) {
  const r = Math.pow(Math.max(1, warOpp) / Math.max(1, warMe), o.zoneHandicap);
  const c = Math.min(o.zoneClamp[1], Math.max(o.zoneClamp[0], r));
  return o.zoneBase * c;
}

// 1타 데미지 — normErr(0=존 정중앙, 1=존 경계)
export function dmgFor(warHitter, warTarget, normErr, o = DUEL_DEFAULTS) {
  const ratio = Math.max(1, warHitter) / Math.max(1, warTarget);
  const acc = 1 + (1 - Math.min(1, Math.max(0, normErr))) * o.accBonus;
  const crit = normErr < o.critNorm;
  let d = o.dmgBase * Math.pow(ratio, o.dmgExp) * acc * (crit ? o.critMult : 1);
  d = Math.min(o.dmgClamp[1], Math.max(o.dmgClamp[0], d));
  return { dmg: Math.round(d), crit };
}

// 밸런스 표시용 — 존 경계에 맞췄을 때(최악 명중) 필요 타수
export function hitsToKill(warHitter, warTarget, o = DUEL_DEFAULTS) {
  const worst = dmgFor(warHitter, warTarget, 1, o).dmg;
  const best = dmgFor(warHitter, warTarget, 0, o).dmg;
  return { worst: Math.ceil(o.hp / worst), best: Math.ceil(o.hp / best), dmgWorst: worst, dmgBest: best };
}

export class DuelEngine {
  // a, b: { id, name, war }   war = 무력(0~100 스케일)
  constructor({ a, b, seed = 1, opts = {} }) {
    this.o = { ...DUEL_DEFAULTS, ...opts };
    this.a = { ...a };
    this.b = { ...b };
    this.rng = mulberry32(seed >>> 0);
    this.hp = { a: this.o.hp, b: this.o.hp };
    this.round = 0;
    this.over = false;
    this.winner = null;      // 'a' | 'b' | null(무승부)
    this.log = [];
    this.zone = {
      a: zoneFor(this.a.war, this.b.war, this.o),
      b: zoneFor(this.b.war, this.a.war, this.o),
    };
  }

  // 이번 라운드의 '선' 위치 (0.2~0.8) — 결정론. 근육기억 방지용으로 매 라운드 이동.
  nextTarget() { return 0.2 + this.rng() * 0.6; }

  // AI 오차 생성 — skill 0..1 (1=거의 완벽). 결정론(this.rng), Box-Muller 반정규분포.
  aiError(skill = 0.6) {
    const s = Math.min(1, Math.max(0, skill));
    const sigma = 0.015 + (1 - s) * 0.20;
    const u1 = Math.max(1e-9, this.rng());
    const u2 = this.rng();
    const g = Math.sqrt(-2 * Math.log(u1)) * Math.cos(2 * Math.PI * u2);
    return Math.min(1, Math.abs(g) * sigma);
  }

  // 라운드 판정 — errA/errB: 0..1 (바 길이 비율). 반환: 결과 객체
  resolveRound(errA, errB) {
    if (this.over) return null;
    this.round++;
    const nA = errA / this.zone.a;
    const nB = errB / this.zone.b;
    const inA = nA <= 1;
    const inB = nB <= 1;
    let side = null;
    let normErr = 0;
    if (inA && inB) { side = nA <= nB ? 'a' : 'b'; normErr = Math.min(nA, nB); }
    else if (inA) { side = 'a'; normErr = nA; }
    else if (inB) { side = 'b'; normErr = nB; }

    const r = {
      round: this.round, errA, errB, normA: nA, normB: nB,
      hitter: side, dmg: 0, crit: false, finish: false, timeout: false,
    };
    if (side) {
      const H = side === 'a' ? this.a : this.b;
      const T = side === 'a' ? this.b : this.a;
      const d = dmgFor(H.war, T.war, normErr, this.o);
      r.dmg = d.dmg;
      r.crit = d.crit;
      const tk = side === 'a' ? 'b' : 'a';
      this.hp[tk] = Math.max(0, this.hp[tk] - d.dmg);
      if (this.hp[tk] <= 0) { this.over = true; this.winner = side; r.finish = true; }
    }
    if (!this.over && this.round >= this.o.maxRounds) {
      this.over = true;
      this.winner = this.hp.a === this.hp.b ? null : (this.hp.a > this.hp.b ? 'a' : 'b');
      r.timeout = true;
    }
    this.log.push(r);
    return r;
  }

  snapshot() {
    return { hp: { ...this.hp }, round: this.round, over: this.over, winner: this.winner };
  }
}

// ── 등용모드 연동용(아직 미배선) ────────────────────────────────────────────
// '거짓말이지롱' — 일기토를 이겨도 약속을 깨고 도망칠 확률. 지력이 높을수록 말로 빠져나간다.
//   제갈량(100)·사마의(98) ≈ 40% / 여포·전위 같은 저지력 맹장 ≈ 10% 이하.
export function liarChance(intel, k = 0.4) {
  return Math.max(0, Math.min(0.6, ((intel || 50) / 100) * k));
}

// 도발 발생 — 등용 실패 시 이 확률로 포로가 일기토를 걸어온다
export const TAUNT_CHANCE = 0.30;
