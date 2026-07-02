// engine.js — 손가락삼국지 순수 시뮬 엔진 (Phase 0 추출 진행중)
//
// 목표: 서버·호스트·싱글이 공유하는 결정론 시뮬. 브라우저 API(DOM/캔버스/window/zoom/DPR) 의존 0.
// 상위문서: docs/multiplayer_realtime_design.md, docs/phase0_engine_extraction.md
//
// 현재 상태(2026-07): 골격 + 첫 시스템(성 생산 growth) 이관 완료. 전투/이동/AI/공성은 미이관(아래 TODO).
//   prototype.html의 동명 함수를 이 엔진 메서드로 순차 이관하며, 이관될 때마다 하네스가 결정론을 검증한다.
//
// 좌표계: 월드픽셀(Step1/2에서 prototype.html이 이미 기기·줌 독립으로 전환). 성 x/y=정규화(0..1),
//   부대 x/y=정규화×worldPx. 엔진은 렌더를 모르며 순수 상태만 굴린다.

// ── 결정론 난수 (prototype.html _mulberry32와 동일 알고리즘) ──────────────
export function mulberry32(seed) {
  let s = (seed | 0) || 1;
  return function () {
    s = (s + 0x6D2B79F5) | 0;
    let t = Math.imul(s ^ (s >>> 15), 1 | s);
    t = (t + Math.imul(t ^ (t >>> 7), 61 | t)) ^ t;
    return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
  };
}

// ── 스냅샷 결정론 해시 (FNV-1a 32bit, 네트워크·테스트 상태비교용) ──────────
export function hashSnapshot(snap) {
  const str = JSON.stringify(snap);
  let h = 0x811c9dc5;
  for (let i = 0; i < str.length; i++) {
    h ^= str.charCodeAt(i);
    h = Math.imul(h, 0x01000193);
  }
  return (h >>> 0).toString(16).padStart(8, '0');
}

// ── 시뮬 상수 (prototype.html에서 이관, 병종/생산) ───────────────────────
export const UNITS = {
  spear:   { speed: 1.0 },
  cavalry: { speed: 1.5 },
  archer:  { speed: 0.9 },
};
export const UNIT_KEYS = ['spear', 'cavalry', 'archer'];
export const CASTLE_AUTO_GROW_CAP = 99; // prototype.html:17752 실측치 일치

export function counters(atk, def) {
  return (atk === 'spear'   && def === 'cavalry') ||
         (atk === 'cavalry' && def === 'archer')  ||
         (atk === 'archer'  && def === 'spear');
}

function totalTroops(c) {
  return (c.troops.spear | 0) + (c.troops.cavalry | 0) + (c.troops.archer | 0);
}

// ── SimEngine — 순수 권위 시뮬 ────────────────────────────────────────────
// 계약(설계문서 §2): constructor(mapDef, seed, opts) / enqueue / step / snapshot / applySnapshot
export class SimEngine {
  constructor(mapDef, seed, opts = {}) {
    this.rng = mulberry32(seed >>> 0);      // 시뮬 난수 단일 소스 (prototype.html simRng 대응)
    this.tick = 0;                          // 스텝 카운터 (performance.now 대체)
    this.simTime = 0;                       // 누적 시뮬 시간(초) — 생산-공성 게이팅용
    this.world = { w: mapDef.world?.w || 1, h: mapDef.world?.h || 1 };
    // 스테이지/플레이어 파라미터 (prototype.html STAGES[cur]/업그레이드 대응) — 순수 값으로 주입
    this.params = {
      growthMult: mapDef.growthMult || 1,   // STAGES[cur].growthMult
      prodRateUpg: opts.prodRateUpg || 1,   // upgVal('prodRate') (아군 성 생산 가속)
      commanderProd: opts.commanderProd || 1,
    };
    // 순수 상태(직렬화 가능). mapDef.castles = [{x,y,owner,name,primary,troops,size,trait}]
    this.castles = (mapDef.castles || []).map((c) => ({
      x: c.x, y: c.y, owner: c.owner, name: c.name,
      size: c.size || 1.0, trait: c.trait || 'prod',
      primary: c.primary, troops: { ...c.troops },
      _grow: 0, _contested: false, _lastSiegeT: 0,
    }));
    this.armies = [];                       // TODO: 부대 상태(이관 예정)
    this.events = [];                       // 이번 스텝 이벤트(전투/함락/대사) → 렌더가 소비
    this._cmdQueue = [];
  }

  // 명령 큐잉 (id 기반, 검증 후 적용). prototype.html sendArmy 대응.
  enqueue(playerId, cmd) {
    // TODO: 소유권·병력·쿨다운 검증. 현재는 자리표시.
    this._cmdQueue.push({ playerId, cmd });
  }

  // 고정 dt 시뮬 스텝. prototype.html update(dt)의 시뮬분 이관 대상.
  step(dt = 1 / 15) {
    this.events.length = 0;
    this.tick++;
    this.simTime += dt;
    // TODO(§3 이관): applyCommands → enemyAI → resolveEngagements → resolveSieges → wallRegen → move
    this._growth(dt);   // ✅ 이관 완료: 성 생산
    return this.events;
  }

  // 성 생산 — prototype.html growth(dt) 충실 이관 (19336). 연출·UI 제거, simTime 게이팅.
  _growth(dt) {
    const now = this.simTime;
    for (const c of this.castles) {
      if (c.owner === 0) continue;
      if (c._contested) continue;
      if (c._lastSiegeT && now - c._lastSiegeT < 0.7) continue; // 공성 중 생산 정지
      c._grow += dt;
      let rate = c.trait === 'prod' ? 0.7 : 1.2;
      const sMult = this.params.growthMult;
      if (c.owner === 2 && sMult > 1) rate /= sMult;
      if (c.owner === 1) rate /= this.params.prodRateUpg;
      if (c.owner === 1) rate /= this.params.commanderProd;
      while (c._grow >= rate) {
        c._grow -= rate;
        if (totalTroops(c) < CASTLE_AUTO_GROW_CAP) c.troops[c.primary]++;
      }
    }
  }

  // 네트워크 전송용 순수 복사. 연출용 임시필드(_grow 등)는 제외해 해시 안정화.
  snapshot() {
    return {
      tick: this.tick,
      castles: this.castles.map((c) => ({
        x: c.x, y: c.y, owner: c.owner, primary: c.primary,
        troops: { spear: c.troops.spear | 0, cavalry: c.troops.cavalry | 0, archer: c.troops.archer | 0 },
      })),
      armies: this.armies.map((a) => ({
        owner: a.owner, unit: a.unit, troops: a.troops | 0,
        x: Math.round(a.x), y: Math.round(a.y),
      })),
    };
  }

  applySnapshot(s) {
    this.tick = s.tick;
    // TODO: 게스트 반영(보간은 렌더). 현재 골격.
  }
}

// TODO(이관 로드맵 — prototype.html → SimEngine 메서드):
//   _enemyAI/_aiTurn        ← aiTurn (19237)         : AI 출진 결정 (rng: 스킵롤)
//   _resolveEngagements     ← resolveEngagements (19534): 부대-부대 전투 (rng: rollCrit)
//   _resolveSieges          ← resolveSieges (19669)   : 공성 (_lastSiegeT 기록)
//   _wallRegenAndFire       ← wallRegenAndFire (19892)
//   _moveArmies             ← update 내 부대 루프 (19937~): aggro/사격/합류/점령/도착
//   _sendArmy               ← sendArmy (19022) 등     : enqueue 처리
//   huoyu 일체              ← tryHuoyu/split (19357~) : rng 화공
