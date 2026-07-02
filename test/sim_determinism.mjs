// test/sim_determinism.mjs — 결정론 하네스 (Node, 브라우저 불필요)
//   실행: node test/sim_determinism.mjs
//
// 검증 목표(설계문서 §7): "같은 seed + 같은 명령열 → 항상 같은 최종상태".
//   1) RNG 스트림 결정론: mulberry32(같은 seed) 수열 동일, 다른 seed 상이.
//   2) 시뮬 상태 결정론: SimEngine(같은 seed) N틱 2회 → 스냅샷 해시 동일.
//   3) (음성 검증) 초기상태가 다르면 결과 해시도 달라야 함.
//
// 현재 이관된 시뮬 시스템: 성 생산(growth). 전투/이동 이관 시 이 하네스가 그대로 커버 확대.

import { SimEngine, mulberry32, hashSnapshot } from '../engine.js';

let pass = 0, fail = 0;
function check(name, cond) {
  if (cond) { pass++; console.log(`  ✅ ${name}`); }
  else { fail++; console.log(`  ❌ ${name}`); }
}

// ── 테스트용 대칭 맵(순수 mapDef) ────────────────────────────────────────
function makeMap() {
  return {
    world: { w: 1, h: 2.2 },
    growthMult: 1.5,
    castles: [
      { x: 0.5, y: 0.10, owner: 1, name: '본진A', primary: 'spear',   troops: { spear: 25, cavalry: 5, archer: 5 }, size: 1.1, trait: 'prod' },
      { x: 0.5, y: 0.90, owner: 2, name: '본진B', primary: 'spear',   troops: { spear: 25, cavalry: 5, archer: 5 }, size: 1.1, trait: 'prod' },
      { x: 0.3, y: 0.50, owner: 0, name: '중립1', primary: 'archer',  troops: { spear: 4,  cavalry: 3, archer: 3 }, size: 0.9, trait: 'def' },
      { x: 0.7, y: 0.50, owner: 0, name: '중립2', primary: 'cavalry', troops: { spear: 4,  cavalry: 3, archer: 3 }, size: 0.9, trait: 'atk' },
    ],
  };
}

function runN(seed, steps, dt = 1 / 15) {
  const eng = new SimEngine(makeMap(), seed);
  for (let i = 0; i < steps; i++) eng.step(dt);
  return hashSnapshot(eng.snapshot());
}

console.log('── 1) RNG 스트림 결정론 ──');
{
  const a = mulberry32(42), b = mulberry32(42), c = mulberry32(43);
  const seqA = Array.from({ length: 8 }, () => a());
  const seqB = Array.from({ length: 8 }, () => b());
  const seqC = Array.from({ length: 8 }, () => c());
  check('같은 seed → 동일 수열', JSON.stringify(seqA) === JSON.stringify(seqB));
  check('다른 seed → 상이 수열', JSON.stringify(seqA) !== JSON.stringify(seqC));
}

console.log('── 2) SimEngine 상태 결정론 (300틱 2회) ──');
{
  const h1 = runN(12345, 300);
  const h2 = runN(12345, 300);
  check(`같은 seed → 동일 최종해시 (${h1})`, h1 === h2);
}

console.log('── 3) 생산 실제 진행 확인 (음성 검증) ──');
{
  const eng = new SimEngine(makeMap(), 7);
  const before = eng.snapshot().castles.map(c => c.troops.spear).join(',');
  for (let i = 0; i < 300; i++) eng.step(1 / 15); // 300틱 = 20초 → 생산 발생
  const after = eng.snapshot().castles.map(c => c.troops.spear).join(',');
  check(`생산으로 상태 변화 (before=${before} → after=${after})`, before !== after);
  // 중립성(owner 0)은 생산 안 함 — 불변 확인
  const neutral = eng.snapshot().castles.filter(c => c.owner === 0);
  check('중립성은 생산 안 함(troops 불변)', neutral.every(c => c.troops.spear === 4 && c.troops.cavalry === 3 && c.troops.archer === 3));
}

console.log('── 4) 결정론 강건성 (dt 분할 무관은 미보장 — 고정 dt 전제 문서화) ──');
{
  // 같은 고정 dt·같은 seed면 스텝수만 같으면 동일해야 함
  const h1 = runN(999, 150);
  const h2 = runN(999, 150);
  check('반복 실행 재현성', h1 === h2);
}

console.log(`\n결과: ${pass} 통과 / ${fail} 실패`);
process.exit(fail ? 1 : 0);
