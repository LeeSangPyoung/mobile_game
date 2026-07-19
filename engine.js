// engine.js — 손가락삼국지 순수 전장 시뮬 엔진 (Phase 0 추출)
//
// 목표: 서버·호스트·싱글이 공유하는 결정론 시뮬. 브라우저 API(DOM/캔버스/window/zoom/DPR) 의존 0.
// 상위문서: docs/multiplayer_realtime_design.md, docs/phase0_engine_extraction.md
//
// 범위: 전장(성·부대·이동·aggro·전투·크리티컬·공성·성벽·화살·AI·화공·승리).
//   장수/업그레이드/로스터 같은 '메타 보정'은 부대·성의 숫자 필드로 주입받는다(기본 1 = 중립/적).
//   배선층(prototype.html)이 플레이어/장수 보정을 계산해 명령·엔티티에 실어 준다.
//   연출(파티클·대사·오디오·진동)은 엔진에 없음 → 의미있는 사건만 events[]로 방출, 클라가 소비.
//
// 좌표계: prototype.html Step1/2에서 기기·줌 독립(월드픽셀)으로 전환됨. 성 x/y=정규화(0..1),
//   부대 x/y=정규화×worldPx. 아래 상수는 prototype.html과 1:1 일치.

// ── 기기독립 월드 상수 (prototype.html:17776~ 일치) ───────────────────────
export const SIM_DPR = 1.5;
export const SIM_VW = 617;
export const SIM_VH = 1371;
export const SIM_REF_ZOOM = 1.0;
const MIN_LAYOUT_CSS_W = 360;

// ── 시뮬 상수 (prototype.html 일치) ───────────────────────────────────────
export const UNITS = {
  spear:   { speed: 1.0 },
  cavalry: { speed: 1.5 },
  archer:  { speed: 0.9 },
};
export const UNIT_KEYS = ['spear', 'cavalry', 'archer'];
export const CASTLE_AUTO_GROW_CAP = 99;    // prototype.html:17752
const DMG_RATE = 0.18;                      // 초당 데미지 계수
const ENGAGE_WARMUP = 1.2;                  // 첫 접촉 후 데미지 시작까지(초)
const HUOYU_FULL_CONVERT_MAX = 55;
const HUOYU_PARTIAL_MIN = 16;
const HUOYU_PARTIAL_MAX = 35;
// 사거리/반경 — prototype.html: N*SIM_DPR/SIM_REF_ZOOM (줌 독립)
const SHOOT_RANGE  = 90  * SIM_DPR / SIM_REF_ZOOM;
const ENGAGE_DIST  = 60  * SIM_DPR / SIM_REF_ZOOM;
const AGGRO_DIST   = 100 * SIM_DPR / SIM_REF_ZOOM;
const ATTACK_RANGE = 80  * SIM_DPR / SIM_REF_ZOOM;
// AI 레벨 (prototype.html:19216 AI_LEVELS 일치)
export const AI_LEVELS = {
  0: { interval: 999, skip: 1.0,  minTroops: 9999 },
  1: { interval: 12.0, skip: 0.92, minTroops: 28 },
  2: { interval: 9.0,  skip: 0.78, minTroops: 22 },
  3: { interval: 6.5,  skip: 0.6,  minTroops: 16 },
  4: { interval: 5.0,  skip: 0.4,  minTroops: 12 },
  5: { interval: 3.5,  skip: 0.25, minTroops: 8 },
};

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

// ── 스냅샷 결정론 해시 (FNV-1a 32bit) ─────────────────────────────────────
export function hashSnapshot(snap) {
  const str = JSON.stringify(snap);
  let h = 0x811c9dc5;
  for (let i = 0; i < str.length; i++) {
    h ^= str.charCodeAt(i);
    h = Math.imul(h, 0x01000193);
  }
  return (h >>> 0).toString(16).padStart(8, '0');
}

// ── 순수 헬퍼 ─────────────────────────────────────────────────────────────
export function counters(atk, def) {
  return (atk === 'spear'   && def === 'cavalry') ||
         (atk === 'cavalry' && def === 'archer')  ||
         (atk === 'archer'  && def === 'spear');
}
// === 창병 정체성 = '돌파 + 공성' ===
// ⚠️ prototype.html 의 SPEAR_TANK / SPEAR_SIEGE 와 반드시 같은 값이어야 함(락스텝 desync 방지).
const SPEAR_TANK  = 1.25;   // 창병이 받는 피해 감소(근접+원거리 공통)
const SPEAR_SIEGE = 1.30;   // 창병의 성벽 공성 피해 배수
function totalTroops(c) {
  return (c.troops.spear | 0) + (c.troops.cavalry | 0) + (c.troops.archer | 0);
}
function majorityUnit(c) {
  let best = 'spear', n = -1;
  for (const k of UNIT_KEYS) if (c.troops[k] > n) { n = c.troops[k]; best = k; }
  return best;
}
function addTroopsToCastle(c, unit, count) {
  if (!c || !unit || count <= 0) return 0;
  const added = Math.floor(count);
  c.troops[unit] = (c.troops[unit] || 0) + added;
  return added;
}

// ── 진영 로드아웃 정규화 (게스트 전송값 검증·클램프 — 치팅 방지) ──────────
function _clamp(v, lo, hi) { v = Number(v); if (!Number.isFinite(v)) return lo; return v < lo ? lo : (v > hi ? hi : v); }
// 계정 업그레이드(단련소) 배수: upgVal 곱 형태(≥1). prototype: castleAtk .08/lv 등 → 상한 3배로 클램프.
function normUpg(u) {
  u = u || {};
  return {
    unitAtk:   _clamp(u.unitAtk,   1, 3),
    unitDef:   _clamp(u.unitDef,   1, 3),
    castleAtk: _clamp(u.castleAtk, 1, 3),
    castleDef: _clamp(u.castleDef, 1, 3),
    prodRate:  _clamp(u.prodRate,  1, 3),
  };
}
// 장수 1명의 해석된 버프(분수) + 크리티컬. prototype generalBuff/commanderCritStats 결과를 그대로 실어옴.
function normGen(g) {
  g = g || {};
  return {
    atk:  _clamp(g.atk,  0, 1),   // unitAtk 분수
    def:  _clamp(g.def,  0, 1),   // unitDef 분수
    cAtk: _clamp(g.cAtk, 0, 1),   // castleAtk 분수
    cDef: _clamp(g.cDef, 0, 1),   // castleDef 분수
    prod: _clamp(g.prod, 0, 1),   // prodRate 분수
    critChance: _clamp(g.critChance, 0, 0.4),
    critMult:   _clamp(g.critMult,   1, 2),
  };
}

// ── SimEngine — 순수 권위 전장 시뮬 ───────────────────────────────────────
// 계약(설계문서 §2): constructor(mapDef, seed, opts) / enqueue / step / snapshot / applySnapshot
export class SimEngine {
  constructor(mapDef, seed, opts = {}) {
    this.rng = mulberry32(seed >>> 0);
    this.tick = 0;
    this.simTime = 0;                    // 누적 시뮬 시간(초)
    this._engageTick = 0;
    this._engageSkipDt = 0;
    this._groupSeq = 1;
    this.huoyuUsed = false;              // 스테이지당 1회
    this.winner = null;
    this.world = { w: mapDef.world?.w || 1, h: mapDef.world?.h || 1 };
    this._pxW = this.world.w * Math.max(SIM_VW, MIN_LAYOUT_CSS_W * SIM_DPR);
    this._pxH = this.world.h * SIM_VH;
    this.params = {
      growthMult: mapDef.growthMult || 1,
      aiLevel: mapDef.aiLevel != null ? mapDef.aiLevel : 1,
      alliance: !!mapDef.alliance,
    };
    // 사람이 조종하는 진영(AI 미작동). 기본 [1]=플레이어. PvP는 [1,2] 등으로 지정.
    this.humanFactions = new Set(mapDef.humanFactions || [1]);
    this.aiTimers = {};
    // 순수 상태. mapDef.castles=[{x,y,owner,name,primary,troops,size,trait, wallMax?, muls...}]
    this.castles = (mapDef.castles || []).map((c) => {
      const size = c.size || 1.0;
      const wallMax = c.wallMax != null ? c.wallMax
        : Math.floor((45 + 20 * (size - 0.9) + (c.trait === 'def' ? 25 : 0)) * (c.defMul || 1));
      return {
        x: c.x, y: c.y, owner: c.owner, name: c.name || '', isHome: !!c.isHome,
        size, trait: c.trait || 'prod',
        primary: c.primary, troops: { spear: 0, cavalry: 0, archer: 0, ...c.troops },
        wallMax, wallHP: wallMax,
        _grow: 0, _wreg: 0, _contested: false, _lastSiegeT: 0, _tdmg: 0, _captureSmokeOnly: false,
        // 메타 보정(기본 1 = 중립/적). 배선층이 owner=1 성에 주입.
        atkMul: c.atkMul || 1, defMul: c.defMul || 1, arriveDefMul: c.arriveDefMul || 1,
        critChance: c.critChance || 0, critMult: c.critMult || 1, _critCD: 0,
      };
    });
    this.armies = [];
    this.arrows = [];
    this.events = [];
    this._cmdQueue = [];
    // 본진(isHome) 원소유자 기록 — 함락 즉시승 판정용(MP 대전). 미지정 맵은 소멸 판정만.
    this._homes = [];
    (mapDef.castles || []).forEach((c, i) => { if (c.isHome) this._homes.push({ idx: i, owner: c.owner }); });
    // 진영별 장수 로드아웃(대칭 PvP 메타). 있으면 pvp 모드: 양측 성/부대에 장수·업그레이드 보정을 결정론 계산.
    this.loadouts = opts.loadouts || null;
    this.pvp = !!this.loadouts;
    this.side = null;
    this._initLoadouts();
  }

  // ── 진영 로드아웃 초기화 + 초기 성 커맨더 배정 ──────────────────────────
  _initLoadouts() {
    if (!this.loadouts) return;
    this.side = {};
    for (const s of [1, 2]) {
      const L = this.loadouts[s] || {};
      this.side[s] = {
        upg: normUpg(L.upg),
        gens: (L.generals || []).slice(0, 10).map(normGen),
        used: new Set(),          // 성에 배정된 gen 인덱스
      };
    }
    // 초기 소유 성에 rank순(본진 우선) 커맨더 배정. 배열/정렬 순서 결정론 유지(V8 안정정렬).
    for (const s of [1, 2]) {
      const owned = this.castles.filter((c) => c.owner === s);
      owned.sort((a, b) => (b.isHome ? 1 : 0) - (a.isHome ? 1 : 0));
      for (const c of owned) this._assignCommander(c);
    }
    // 나머지(중립 등)도 무보정 필드 확정.
    for (const c of this.castles) if (c._cmdSide == null) this._applyCastleMuls(c);
  }
  _assignCommander(c) {
    if (!this.side) return;
    const S = this.side[c.owner];
    if (!S) { c._cmdIdx = -1; c._cmdSide = c.owner || 0; this._applyCastleMuls(c); return; }
    let idx = -1;
    for (let i = 0; i < S.gens.length; i++) { if (!S.used.has(i)) { idx = i; break; } }
    if (idx >= 0) { S.used.add(idx); c._cmdIdx = idx; } else { c._cmdIdx = -1; }
    c._cmdSide = c.owner;
    this._applyCastleMuls(c);
  }
  _releaseCommander(c) {
    if (!this.side) return;
    const S = c._cmdSide ? this.side[c._cmdSide] : null;
    if (S && c._cmdIdx >= 0) S.used.delete(c._cmdIdx);
    c._cmdIdx = -1; c._cmdSide = 0;
  }
  // 점령 시: 이전 소유자 커맨더 반납 → 소유자 변경 → 새 소유자 커맨더 배정 → 벽/생산/전투 보정 갱신.
  _captureCastle(c, newOwner) {
    if (this.side) this._releaseCommander(c);
    c.owner = newOwner;
    if (this.side) this._assignCommander(c);
  }
  _applyCastleMuls(c) {
    const S = (this.side && c.owner) ? this.side[c.owner] : null;
    if (!S) { c.atkMul = 1; c.defMul = 1; c.arriveDefMul = 1; c.critChance = 0; c.critMult = 1; c._prodMul = 1; c._cmdSide = c._cmdSide || 0; return; }
    const g = (c._cmdIdx >= 0) ? S.gens[c._cmdIdx] : null;
    const cAtkB = g ? 1 + g.cAtk : 1, cDefB = g ? 1 + g.cDef : 1, prodB = g ? 1 + g.prod : 1;
    c.atkMul = S.upg.castleAtk * cAtkB;
    c.defMul = S.upg.castleDef * cDefB;
    c.arriveDefMul = cDefB;                 // 도착방어는 upg 미포함(prototype asymmetry 보존)
    c._prodMul = S.upg.prodRate * prodB;
    c.critChance = g ? g.critChance : 0;
    c.critMult = g ? g.critMult : 1;
  }
  // 부대 스폰 시 출발성 커맨더에서 부대 보정 산출(pvp). prototype: army atk/def=upgVal×commander, arriveAtk=commander만.
  _armyMulsFrom(from) {
    if (!this.side) return null;
    const S = this.side[from.owner];
    if (!S) return { atkMul: 1, defMul: 1, arriveAtkMul: 1, critChance: 0, critMult: 1 };
    const g = (from._cmdIdx >= 0) ? S.gens[from._cmdIdx] : null;
    return {
      atkMul: S.upg.unitAtk * (g ? 1 + g.atk : 1),
      defMul: S.upg.unitDef * (g ? 1 + g.def : 1),
      arriveAtkMul: g ? (1 + g.atk) * (1 + g.cAtk) : 1,
      critChance: g ? g.critChance : 0,
      critMult: g ? g.critMult : 1,
    };
  }

  // ── 좌표 변환 (렌더 아님 — 시뮬 내부 정규화→월드픽셀) ──
  _wx(c) { return c.x * this._pxW; }
  _wy(c) { return c.y * this._pxH; }

  // ── 명령 큐잉 (id 기반). {type:'SEND_ARMY', fromId, toId, unit, withCommander, muls?} ──
  enqueue(playerId, cmd) {
    this._cmdQueue.push({ playerId, cmd });
  }
  _applyCommands() {
    for (const { cmd } of this._cmdQueue) {
      if (!cmd || cmd.type !== 'SEND_ARMY') continue;
      const from = this.castles[cmd.fromId];
      if (!from || from.owner === 0) continue;
      const to = cmd.toType === 'army' ? this.armies[cmd.toId] : this.castles[cmd.toId];
      if (!to) continue;
      const unit = cmd.unit;
      if (!unit || (from.troops[unit] | 0) < 1) continue;
      this._spawnArmy(from, to, unit, { muls: cmd.muls, homeCastle: from });
    }
    this._cmdQueue.length = 0;
  }

  // ── 부대 스폰 (prototype.html sendArmy 시뮬분) ──
  _spawnArmy(from, to, unit, opts = {}) {
    const send = from.troops[unit] | 0;
    if (send < 1) return null;
    from.troops[unit] = 0;
    const isArmyTarget = !!(to && to.isArmy);
    // muls: 명시 주입 우선, 없으면 pvp에서 출발성 커맨더로 결정론 산출(기본 무보정).
    const m = opts.muls || (this.pvp ? this._armyMulsFrom(from) : null) || {};
    const a = {
      owner: from.owner, troops: send, unit,
      atkBonus: from.trait === 'atk' ? 1.4 : 1.0, _start: send,
      x: this._wx(from), y: this._wy(from), _sx: this._wx(from), _sy: this._wy(from),
      target: isArmyTarget ? from : to,
      pursuingArmy: isArmyTarget ? to : null,
      homeCastle: opts.homeCastle || null,
      groupId: opts.groupId != null ? opts.groupId : null,
      isArmy: true, dying: false, deathT: 0,
      // 메타 보정(기본 1/0 = 중립/적)
      atkMul: m.atkMul || 1, defMul: m.defMul || 1, arriveAtkMul: m.arriveAtkMul || 1,
      critChance: m.critChance || 0, critMult: m.critMult || 1, _critCD: 0,
      huoyuChance: m.huoyuChance || 0, huoyuIntel: m.huoyuIntel || 0, // 회유 능력(플레이어 선봉)
      _defendCastle: opts._defendCastle || null,
    };
    this.armies.push(a);
    return a;
  }

  // ── 고정 dt 시뮬 스텝 (prototype.html update(dt)의 시뮬분) ──
  step(dt = 1 / 15) {
    this.events.length = 0;
    this.tick++;
    this.simTime += dt;
    this._applyCommands();
    this._growth(dt);
    this._enemyAI(dt);
    this._resolveEngagements(dt);
    this._resolveSieges(dt);
    this._wallRegen(dt);
    this._moveArmies(dt);
    this._moveArrows(dt);
    this._checkWin();
    return this.events;
  }

  // ── 성 생산 (growth 19336) ──
  _growth(dt) {
    const now = this.simTime;
    for (const c of this.castles) {
      if (c.owner === 0) continue;
      if (c._contested) continue;
      if (c._lastSiegeT && now - c._lastSiegeT < 0.7) continue;
      c._grow += dt;
      let rate = c.trait === 'prod' ? 0.7 : 1.2;
      // 싱글: 적(2)에 AI 성장핸디캡. pvp에선 대칭이라 미적용.
      if (!this.pvp && c.owner === 2 && this.params.growthMult > 1) rate /= this.params.growthMult;
      // 생산 보정: 양 진영 모두 적용(_prodMul 기본 1). pvp에선 양측 장수/업그레이드 반영.
      rate /= (c._prodMul || 1);
      while (c._grow >= rate) {
        c._grow -= rate;
        if (totalTroops(c) < CASTLE_AUTO_GROW_CAP) c.troops[c.primary]++;
      }
    }
  }

  // ── 크리티컬 (rollCritOnEntity 14227). 장수 없으면 critChance=0 → 1배 ──
  _rollCrit(ent, dt) {
    if (!ent.critChance) return 1;
    ent._critCD = (ent._critCD == null ? 0.6 : ent._critCD) - dt;
    if (ent._critCD > 0) return 1;
    if (this.rng() < ent.critChance) { ent._critCD = 1.2; return ent.critMult || 1; }
    ent._critCD = 0.5;
    return 1;
  }

  // ── AI 출진 (aiTurn 19252) ──
  _enemyAI(dt) {
    const present = new Set();
    const isAI = (o) => o !== 0 && !this.humanFactions.has(o); // 사람 진영·중립은 AI 미작동
    for (const a of this.armies) if (isAI(a.owner) && !a.dying) present.add(a.owner);
    for (const c of this.castles) if (isAI(c.owner)) present.add(c.owner);
    for (const f of present) this._aiTurn(f, dt);
  }
  _aiTurn(faction, dt) {
    const lvl = AI_LEVELS[this.params.aiLevel || 1];
    this.aiTimers[faction] = (this.aiTimers[faction] || 0) + dt;
    if (this.aiTimers[faction] < lvl.interval) return;
    this.aiTimers[faction] = 0;
    const myCastles = this.castles.filter(c => c.owner === faction && totalTroops(c) > lvl.minTroops);
    const sizeByOwner = {};
    for (const c of this.castles) sizeByOwner[c.owner] = (sizeByOwner[c.owner] | 0) + 1;
    for (const ec of myCastles) {
      if (this.rng() < lvl.skip) continue;
      const targetFilter = (c) => {
        if (c.owner === faction) return false;
        if (c.owner === 0) return true;
        return true; // 동맹 세부는 배선층/맵에서; 엔진 기본은 자유교전
      };
      const castleTargets = this.castles.filter(targetFilter);
      let target = null, pursuingArmy = null;
      if (castleTargets.length) {
        const scoreOf = (c) => {
          const d = Math.hypot((ec.x - c.x) * this._pxW, (ec.y - c.y) * this._pxH);
          const size = sizeByOwner[c.owner] | 0;
          const sizeBonus = size >= 4 ? 80 : size >= 3 ? 40 : 0;
          return d - sizeBonus;
        };
        castleTargets.sort((a, b) => scoreOf(a) - scoreOf(b));
        target = castleTargets[0];
      } else {
        const enemyArmies = this.armies.filter(a =>
          a.owner !== faction && a.owner !== 0 && a.troops > 0 && !a.dying);
        if (!enemyArmies.length) continue;
        enemyArmies.sort((a, b) => {
          const da = Math.hypot(a.x - this._wx(ec), a.y - this._wy(ec));
          const db = Math.hypot(b.x - this._wx(ec), b.y - this._wy(ec));
          return da - db;
        });
        pursuingArmy = enemyArmies[0];
        target = ec;
      }
      const u = majorityUnit(ec);
      if (ec.troops[u] < 1) continue;
      const a = this._spawnArmy(ec, target, u, { homeCastle: pursuingArmy ? ec : null });
      if (a && pursuingArmy) { a.pursuingArmy = pursuingArmy; a.target = ec; }
    }
  }

  // ── 부대-부대 전투 (resolveEngagements 19549) ──
  _resolveEngagements(dt) {
    this._engageTick = (this._engageTick + 1) & 0xffff;
    if (this._engageTick & 1) { this._engageSkipDt += dt; return; }
    dt += this._engageSkipDt; this._engageSkipDt = 0;
    const armies = this.armies;
    const engaged = new Set();
    const damage = new Map();
    for (let i = 0; i < armies.length; i++) {
      for (let j = i + 1; j < armies.length; j++) {
        const a = armies[i], b = armies[j];
        if (a.owner === b.owner) continue;
        if (a.troops <= 0 || b.troops <= 0) continue;
        const d = Math.hypot(a.x - b.x, a.y - b.y);
        if (d > ENGAGE_DIST) continue;
        engaged.add(a); engaged.add(b);
        const firstContact = !a._engagedFlash && !b._engagedFlash;
        if (firstContact) {
          a._engagedFlash = b._engagedFlash = true;
          // 회유(화공): 아군(1) vs 적(2) 첫 접촉 시 극저확률 전향
          const pa = a.owner === 1 ? a : (b.owner === 1 ? b : null);
          const ea = a.owner === 2 ? a : (b.owner === 2 ? b : null);
          if (pa && ea && this._tryHuoyu(pa, ea)) { engaged.delete(a); engaged.delete(b); continue; }
        } else { a._engagedFlash = b._engagedFlash = true; }
        const aCnt = counters(a.unit, b.unit) ? 1.5 : (counters(b.unit, a.unit) ? 1 / 1.5 : 1);
        const bCnt = counters(b.unit, a.unit) ? 1.5 : (counters(a.unit, b.unit) ? 1 / 1.5 : 1);
        const aAtk = a.atkMul, bAtk = b.atkMul, aDef = a.defMul, bDef = b.defMul;
        a._engageT = (a._engageT || 0) + dt;
        b._engageT = (b._engageT || 0) + dt;
        if (a._engageT < ENGAGE_WARMUP || b._engageT < ENGAGE_WARMUP) continue;
        const aTank = a.unit === 'spear' ? SPEAR_TANK : 1, bTank = b.unit === 'spear' ? SPEAR_TANK : 1;   // 창병 탱커(근접)
        const dpsA = a.troops * (a.atkBonus || 1) * aCnt * DMG_RATE * aAtk / (bDef * bTank);
        const dpsB = b.troops * (b.atkBonus || 1) * bCnt * DMG_RATE * bAtk / (aDef * aTank);
        const aCritMult = this._rollCrit(a, dt);
        const bCritMult = this._rollCrit(b, dt);
        damage.set(b, (damage.get(b) || 0) + dpsA * aCritMult * dt);
        damage.set(a, (damage.get(a) || 0) + dpsB * bCritMult * dt);
      }
    }
    for (const a of armies) {
      if (damage.has(a)) a._dmg = (a._dmg || 0) + damage.get(a);
      while ((a._dmg || 0) >= 1 && a.troops > 0) { a.troops--; a._dmg -= 1; }
      a._engaged = engaged.has(a);
    }
    for (let i = armies.length - 1; i >= 0; i--) {
      const dead = armies[i];
      if (dead.troops <= 0 && !dead.dying) {
        dead.dying = true; dead.deathT = 0;
        this.events.push({ type: 'armyDead', owner: dead.owner, x: dead.x, y: dead.y });
      }
    }
  }

  // ── 공성 (resolveSieges 19684) ──
  _resolveSieges(dt) {
    const castles = this.castles, armies = this.armies;
    for (const c of castles) {
      if (c._contested) {
        const def = armies.some(x => x._defendCastle === c && !x.dying && x.troops > 0);
        if (!def) c._contested = false;
      }
    }
    const siegers = new Map();
    for (const a of armies) {
      a._sieging = false;
      if (a._engaged) continue;
      if (a.pursuingArmy) continue;
      if (!a.target || a.target.isArmy) continue;
      if (a.target.owner === a.owner) continue;
      if (a.target.owner === 0) continue;
      const d = Math.hypot(this._wx(a.target) - a.x, this._wy(a.target) - a.y);
      if (d < ATTACK_RANGE) {
        a._sieging = true;
        if (!siegers.has(a.target)) siegers.set(a.target, []);
        siegers.get(a.target).push(a);
      }
    }
    for (const [castle, atks] of siegers) {
      castle._lastSiegeT = this.simTime;
      for (const a of atks) {
        const cDef = castle.defMul || 1;
        const aPow = a.troops * (a.atkBonus || 1) * (a.unit === 'spear' ? SPEAR_SIEGE : 1) / cDef;   // 창병 = 성을 미는 병종
        // 성 반격
        const cAtk = castle.atkMul || 1;
        const garrison = totalTroops(castle);
        const wallFactor = castle.wallHP > 0 ? 1 : 0;
        const critMult = this._rollCrit(castle, dt);
        const counter = garrison * DMG_RATE * 0.08 * cAtk * wallFactor * critMult * dt;
        a._cdmg = (a._cdmg || 0) + counter;
        while ((a._cdmg || 0) >= 1 && a.troops > 0) { a.troops--; a._cdmg -= 1; }

        if (castle.wallHP > 0) {
          const before = castle.wallHP;
          castle.wallHP = Math.max(0, castle.wallHP - aPow * 0.22 * dt);
          if (before > 0 && castle.wallHP === 0) {
            this.events.push({ type: 'wallBreach', castle: this.castles.indexOf(castle), by: a.owner });
            if (totalTroops(castle) > 0) {
              const aliveAtks = atks.filter(x => x.troops > 0);
              if (aliveAtks.length > 0) {
                let i = 0;
                for (const u of UNIT_KEYS) {
                  if ((castle.troops[u] || 0) > 0) {
                    const target = aliveAtks[i % aliveAtks.length]; i++;
                    const sortied = this._spawnArmy(castle, target, u, { homeCastle: castle, _defendCastle: castle });
                    if (sortied) sortied._defendCastle = castle;
                  }
                }
              }
              castle.wallHP = 0; castle._tdmg = 0; castle._contested = true;
            }
          }
        } else {
          castle._tdmg = (castle._tdmg || 0) + aPow * 0.7 * dt;
          while ((castle._tdmg || 0) >= 1 && totalTroops(castle) > 0) {
            const k = majorityUnit(castle);
            if (castle.troops[k] > 0) castle.troops[k]--;
            castle._tdmg -= 1;
          }
        }
      }
      const liveDefenders = armies.some(x => x._defendCastle === castle && !x.dying && x.troops > 0);
      if (castle._contested && !liveDefenders) castle._contested = false;
      // 점령
      if (totalTroops(castle) === 0 && castle.wallHP === 0 &&
          atks.some(a => a.troops > 0) && !castle._contested && !liveDefenders) {
        const aliveAtks = atks.filter(a => a.troops > 0);
        const winner = aliveAtks.reduce((p, x) => (p && p.troops > x.troops ? p : x), null);
        if (winner) {
          const prevOwner = castle.owner;
          this._captureCastle(castle, winner.owner);
          castle._contested = false;
          castle.primary = winner.unit;
          castle.troops = { spear: 0, cavalry: 0, archer: 0 };
          for (let i = armies.length - 1; i >= 0; i--) {
            const ar = armies[i];
            if (aliveAtks.includes(ar)) { addTroopsToCastle(castle, ar.unit, ar.troops); armies.splice(i, 1); }
          }
          castle.wallHP = Math.floor(castle.wallMax * 0.5);
          this.events.push({ type: 'capture', castle: this.castles.indexOf(castle), from: prevOwner, to: winner.owner });
        }
      }
    }
    for (let i = armies.length - 1; i >= 0; i--) {
      if (armies[i].troops <= 0 && !armies[i].dying) armies.splice(i, 1);
    }
  }

  // ── 성벽 자연회복 (wallRegenAndFire 19907) ──
  _wallRegen(dt) {
    for (const c of this.castles) {
      if (c._contested) { c.wallHP = 0; continue; }
      if (c.owner !== 0 && c.wallHP < c.wallMax) {
        c._wreg = (c._wreg || 0) + dt;
        while (c._wreg >= 1.5) { c._wreg -= 1.5; if (c.wallHP < c.wallMax) c.wallHP++; }
      }
      if (c._captureSmokeOnly && (c.wallHP / c.wallMax) >= 0.56) c._captureSmokeOnly = false;
    }
  }

  // ── 화공(회유) (tryHuoyu 19431 / split·convert). 플레이어 부대에 huoyuChance 주입 시만 발동 ──
  _tryHuoyu(playerArmy, enemyArmy) {
    if (this.huoyuUsed) return false;
    const chance = playerArmy.huoyuChance || 0;
    const intel = playerArmy.huoyuIntel || 0;
    if (chance <= 0) return false;
    if (this.rng() >= chance) return false;
    this.huoyuUsed = true;
    if (enemyArmy.troops > HUOYU_FULL_CONVERT_MAX && enemyArmy.troops > 1) {
      const rate = intel >= 90 ? 0.34 : (intel >= 75 ? 0.29 : 0.22);
      const count = Math.max(HUOYU_PARTIAL_MIN, Math.min(HUOYU_PARTIAL_MAX, Math.floor(enemyArmy.troops * rate), enemyArmy.troops - 1));
      const turn = Math.max(1, Math.min(count | 0, enemyArmy.troops - 1));
      enemyArmy.troops -= turn;
      const splitAng = this.rng() * Math.PI * 2;
      const splitDist = (26 + this.rng() * 18) * SIM_DPR / SIM_REF_ZOOM;
      const ally = {
        owner: 1, troops: turn, unit: enemyArmy.unit, atkBonus: enemyArmy.atkBonus || 1, _start: turn,
        x: enemyArmy.x + Math.cos(splitAng) * splitDist,
        y: enemyArmy.y + Math.sin(splitAng) * splitDist * 0.72,
        _sx: enemyArmy.x, _sy: enemyArmy.y,
        target: null, pursuingArmy: null, homeCastle: null, groupId: null,
        isArmy: true, dying: false, deathT: 0,
        atkMul: 1, defMul: 1, arriveAtkMul: 1, critChance: 0, critMult: 1, _critCD: 0,
      };
      this._retargetHuoyu(ally);
      this.armies.push(ally);
    } else {
      enemyArmy.owner = 1;
      enemyArmy.pursuingArmy = null; enemyArmy._defendCastle = null;
      enemyArmy._engaged = false; enemyArmy._engagedFlash = false; enemyArmy._engagedOnce = false;
      enemyArmy._sieging = false;
      this._retargetHuoyu(enemyArmy);
    }
    this.events.push({ type: 'huoyu' });
    return true;
  }
  _retargetHuoyu(a) {
    const near = (owner) => {
      let best = null, bd = Infinity;
      for (const c of this.castles) {
        if (c.owner !== owner) continue;
        const dx = this._wx(c) - a.x, dy = this._wy(c) - a.y;
        const dd = dx * dx + dy * dy;
        if (dd < bd) { bd = dd; best = c; }
      }
      return best;
    };
    const target = near(2) || near(0) || near(1);
    if (target) { a.target = target; a.homeCastle = target; }
  }

  // ── 부대 이동/aggro/사격/합류/점령/도착 (update 부대 루프 19953) ──
  _moveArmies(dt) {
    const armies = this.armies, castles = this.castles;
    for (let i = armies.length - 1; i >= 0; i--) {
      const a = armies[i];
      if (a.dying) {
        a.deathT = (a.deathT || 0) + dt;
        if (a.deathT > 0.4) armies.splice(i, 1);
        continue;
      }
      // 추격 대상 정리
      if (a.pursuingArmy) {
        const p = a.pursuingArmy;
        const stillAlive = p && p.troops > 0 && !p.dying && armies.indexOf(p) >= 0;
        if (!stillAlive) {
          a.pursuingArmy = null;
          if (a._aggroSavedTarget) { a.target = a._aggroSavedTarget; delete a._aggroSavedTarget; continue; }
          let home = (a.homeCastle && a.homeCastle.owner === a.owner) ? a.homeCastle : null;
          if (!home) {
            let bestD = Infinity;
            for (const k of castles) {
              if (k.owner !== a.owner) continue;
              const dx = this._wx(k) - a.x, dy = this._wy(k) - a.y;
              const dd = dx * dx + dy * dy;
              if (dd < bestD) { bestD = dd; home = k; }
            }
          }
          if (home) { a.homeCastle = home; a.target = home; }
        }
      }
      // aggro 자동 끌림
      a._aggroCool = (a._aggroCool || 0) - dt;
      if (a._aggroCool <= 0 && !a.pursuingArmy && !a.dying && a.target) {
        a._aggroCool = 0.15 + this.rng() * 0.05;
        const aggroR = AGGRO_DIST, aggroR2 = aggroR * aggroR;
        let castleNear = false;
        if (a.target && !a.target.isArmy) {
          const tdx = this._wx(a.target) - a.x, tdy = this._wy(a.target) - a.y;
          const near = aggroR * 0.6;
          if (tdx * tdx + tdy * tdy < near * near) castleNear = true;
        }
        if (!castleNear) {
          let best = null, bestD2 = aggroR2;
          for (let k = 0; k < armies.length; k++) {
            const e = armies[k];
            if (e === a || e.owner === a.owner || e.dying || e.troops <= 0) continue;
            const dx = e.x - a.x, dy = e.y - a.y, d2 = dx * dx + dy * dy;
            if (d2 < bestD2) { bestD2 = d2; best = e; }
          }
          if (best) { a._aggroSavedTarget = a.target; a.pursuingArmy = best; }
        }
      }
      // 목표 좌표
      let tx, ty;
      if (a.pursuingArmy) { tx = a.pursuingArmy.x; ty = a.pursuingArmy.y; }
      else { tx = this._wx(a.target); ty = this._wy(a.target); }
      const dx = tx - a.x, dy = ty - a.y;
      const d = Math.sqrt(dx * dx + dy * dy);

      // 궁수 사격
      const _pursuingFriend = a.pursuingArmy && a.pursuingArmy.owner === a.owner;
      if (!_pursuingFriend && a.unit === 'archer' && a.target && a.target.owner !== a.owner) {
        let foe = null, foeD = Infinity;
        for (const b of armies) {
          if (b === a || b.owner === a.owner || b.troops <= 0 || b.dying) continue;
          const bd = Math.hypot(b.x - a.x, b.y - a.y);
          if (bd < foeD) { foeD = bd; foe = b; }
        }
        const targetingFoe = foe && foeD < SHOOT_RANGE;
        const targetingCastle = !targetingFoe && d < SHOOT_RANGE;
        if (targetingFoe || targetingCastle) {
          a._shootCD = (a._shootCD || 0) - dt;
          if (a._shootCD <= 0) {
            a._shootCD = 0.35 + this.rng() * 0.15;
            const numArrows = Math.min(3, Math.ceil(a.troops / 5));
            for (let k = 0; k < numArrows; k++) {
              this.arrows.push({
                t: 0, dur: 0.55, owner: a.owner,
                hitArmy: targetingFoe ? foe : null,
                hitCastle: targetingFoe ? null : a.target,
                dmg: 0.35 * (a.atkBonus || 1) * (a.atkMul || 1),
              });
            }
          }
          if (targetingFoe) continue;
        }
      }

      if (a._sieging || a._engaged) continue;

      // 아군 성 합류
      if (!a.pursuingArmy && a.target && a.target.owner === a.owner && d < 10 * SIM_DPR / SIM_REF_ZOOM) {
        addTroopsToCastle(a.target, a.unit, a.troops);
        if (a._defendCastle === a.target) {
          a.target._contested = false;
          if (a.target.wallHP < a.target.wallMax * 0.5) a.target.wallHP = Math.floor(a.target.wallMax * 0.5);
        }
        armies.splice(i, 1); continue;
      }
      // 빈 성 점령
      if (a.target && a.target.owner === 0 && d < 12 * SIM_DPR / SIM_REF_ZOOM) {
        const prevOwner = a.target.owner;
        this._captureCastle(a.target, a.owner);
        a.target.primary = a.unit;
        a.target.troops = { spear: 0, cavalry: 0, archer: 0 };
        a.target.troops[a.unit] = a.troops;
        a.target.wallHP = a.target.wallMax;
        this.events.push({ type: 'capture', castle: castles.indexOf(a.target), from: prevOwner, to: a.owner });
        armies.splice(i, 1); continue;
      }

      let speed = 18 * SIM_DPR * (UNITS[a.unit]?.speed || 1) / SIM_REF_ZOOM;
      if (a._sx !== undefined) {
        const totD = Math.hypot(tx - a._sx, ty - a._sy);
        if (totD > 0 && (1 - d / totD) > 0.85) speed *= 1.3;
      }
      if (!a.pursuingArmy && d < 6 / SIM_REF_ZOOM) { this._arrive(a); armies.splice(i, 1); }
      else if (d > 0) {
        let mvx = dx / d, mvy = dy / d;
        for (const c of castles) {
          if (c === a.target) continue;
          const ex = a.x - this._wx(c), ey = a.y - this._wy(c);
          const ed = Math.hypot(ex, ey);
          const rr = 53 * SIM_DPR * (c.size || 1) + 18 * SIM_DPR;
          if (ed < rr && ed > 0.01) {
            const push = (rr - ed) / rr;
            mvx += (ex / ed) * push * 1.4;
            mvy += (ey / ed) * push * 1.4;
          }
        }
        const ml = Math.hypot(mvx, mvy) || 1;
        a.x += (mvx / ml) * speed * dt; a.y += (mvy / ml) * speed * dt;
      }
    }
  }

  // ── 성 도착 백병전 (arrive 20294) ──
  _arrive(a) {
    const c = a.target;
    if (!c) return;
    if (c.owner === a.owner) { addTroopsToCastle(c, a.unit, a.troops); return; }
    const defTotal = totalTroops(c);
    const defUnit = defTotal > 0 ? majorityUnit(c) : a.unit;
    const counterBonus = counters(a.unit, defUnit) ? 1.5 : (counters(defUnit, a.unit) ? 1 / 1.5 : 1);
    const atk = a.troops * (a.atkBonus || 1) * counterBonus * (a.arriveAtkMul || 1);
    const def = defTotal * (c.trait === 'def' ? 1.55 : 1) * (c.arriveDefMul || 1);
    if (atk > def) {
      const remain = Math.max(1, Math.ceil((atk - def) / ((a.atkBonus || 1) * counterBonus)));
      const prevOwner = c.owner;
      if (defTotal > 0 && prevOwner !== 0) {
        const retreatCount = Math.max(1, Math.floor(defTotal * 0.3));
        const retreatTo = this._nearestFriendlyCastle(c, prevOwner);
        if (retreatTo && retreatCount > 0) {
          this.armies.push({
            owner: prevOwner, troops: retreatCount, unit: defUnit, atkBonus: 1, _start: retreatCount,
            x: this._wx(c), y: this._wy(c), _sx: this._wx(c), _sy: this._wy(c),
            target: retreatTo, pursuingArmy: null, homeCastle: retreatTo, groupId: null,
            isArmy: true, dying: false, deathT: 0, isRetreat: true,
            atkMul: 1, defMul: 1, arriveAtkMul: 1, critChance: 0, critMult: 1, _critCD: 0,
          });
        }
      }
      this._captureCastle(c, a.owner);
      c.primary = a.unit;
      c.troops = { spear: 0, cavalry: 0, archer: 0 };
      c.troops[a.unit] = remain;
      c.wallHP = Math.floor(c.wallMax * 0.5);
      this.events.push({ type: 'capture', castle: this.castles.indexOf(c), from: prevOwner, to: a.owner });
    } else {
      // 비례 손실 (arrive 20353)
      const remainTotal = Math.max(1, Math.ceil((def - atk) / (c.trait === 'def' ? 1.55 : 1)));
      const ratio = defTotal > 0 ? remainTotal / defTotal : 0;
      for (const k of UNIT_KEYS) c.troops[k] = Math.floor(c.troops[k] * ratio);
      if (totalTroops(c) === 0) c.troops[c.primary] = 1;
    }
  }
  _nearestFriendlyCastle(c, faction) {
    let best = null, bestD = Infinity;
    const cx = this._wx(c), cy = this._wy(c);
    for (const k of this.castles) {
      if (k === c || k.owner !== faction) continue;
      const dx = this._wx(k) - cx, dy = this._wy(k) - cy, d = dx * dx + dy * dy;
      if (d < bestD) { bestD = d; best = k; }
    }
    return best;
  }

  // ── 화살 (update 화살 루프 20195). 명중은 참조로 판정 ──
  _moveArrows(dt) {
    const arrows = this.arrows;
    for (let i = arrows.length - 1; i >= 0; i--) {
      const ar = arrows[i];
      ar.t += dt;
      if (ar.t < ar.dur) continue;
      if (ar.hitArmy && ar.hitArmy.troops > 0 && !ar.hitArmy.dying && ar.hitArmy.owner !== ar.owner) {
        // 원거리 피해에도 방어 적용(창병 탱커 + 병력 방어력) — prototype.html 과 동일 규칙
        const _tgTank = ar.hitArmy.unit === 'spear' ? SPEAR_TANK : 1;
        const _tgDef = ar.hitArmy.defMul || 1;
        // 원거리 상성 — 궁병을 카운터하는 병종(기병)만 감쇄. 궁>창 보너스는 원거리엔 미적용.
        // (궁병은 원거리+근접 동시 타격이라 보너스까지 주면 이중 특혜) — prototype.html 과 동일 규칙
        const _tgCnt = counters(ar.hitArmy.unit, 'archer') ? 1 / 1.5 : 1;
        ar.hitArmy._dmg = (ar.hitArmy._dmg || 0) + (ar.dmg || 0) * _tgCnt / (_tgDef * _tgTank);
        while ((ar.hitArmy._dmg || 0) >= 1 && ar.hitArmy.troops > 0) { ar.hitArmy.troops--; ar.hitArmy._dmg -= 1; }
      } else if (ar.hitCastle && ar.hitCastle.owner !== ar.owner && ar.hitCastle.owner !== 0) {
        if (ar.hitCastle.wallHP > 0) {
          ar.hitCastle.wallHP = Math.max(0, ar.hitCastle.wallHP - (ar.dmg || 0) * 0.4);
        } else {
          ar.hitCastle._tdmg = (ar.hitCastle._tdmg || 0) + (ar.dmg || 0);
          while ((ar.hitCastle._tdmg || 0) >= 1 && totalTroops(ar.hitCastle) > 0) {
            const k = majorityUnit(ar.hitCastle);
            if (ar.hitCastle.troops[k] > 0) ar.hitCastle.troops[k]--;
            ar.hitCastle._tdmg -= 1;
          }
        }
      }
      arrows.splice(i, 1);
    }
  }

  // ── 승리 판정 (checkWin 20451 시뮬분: 비-플레이어 적성 0 → 승) ──
  _checkWin() {
    if (this.winner != null) return;
    // 본진 함락 즉시승 (isHome 지정 시) — 상대 본진이 원소유자 손을 떠나면 즉시 결착
    if (this._homes.length) {
      const defeated = new Set();
      for (const h of this._homes) if (this.castles[h.idx].owner !== h.owner) defeated.add(h.owner);
      if (defeated.size >= 1) {
        const alive = [...new Set(this._homes.map(h => h.owner))].filter(o => !defeated.has(o));
        if (alive.length === 1) { this.winner = alive[0]; this.events.push({ type: 'win', winner: this.winner, reason: 'homeCapture' }); return; }
      }
    }
    const owners = new Set();
    for (const c of this.castles) if (c.owner !== 0) owners.add(c.owner);
    for (const a of this.armies) if (a.owner !== 0 && !a.dying && a.troops > 0) owners.add(a.owner);
    if (owners.size === 1) {
      this.winner = [...owners][0];
      this.events.push({ type: 'win', winner: this.winner });
    }
  }

  // ── 스냅샷/해시 (네트워크·결정론 테스트) ──
  snapshot() {
    return {
      tick: this.tick,
      winner: this.winner,
      castles: this.castles.map((c) => ({
        owner: c.owner, primary: c.primary, wallHP: Math.round(c.wallHP),
        troops: { spear: c.troops.spear | 0, cavalry: c.troops.cavalry | 0, archer: c.troops.archer | 0 },
      })),
      armies: this.armies.map((a) => ({
        owner: a.owner, unit: a.unit, troops: a.troops | 0,
        x: Math.round(a.x), y: Math.round(a.y), dying: !!a.dying,
      })),
    };
  }
  applySnapshot(s) { this.tick = s.tick; this.winner = s.winner; /* TODO 게스트 반영 */ }
}
