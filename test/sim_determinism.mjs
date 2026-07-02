// test/sim_determinism.mjs — 결정론 하네스 (Node, 브라우저 불필요)
//   실행: node test/sim_determinism.mjs
//
// 검증(설계문서 §7): "같은 seed + 같은 명령열 → 항상 같은 최종상태".
//   전장 전 시스템(생산·이동·aggro·전투·크리티컬·공성·성벽·화살·AI·화공·승리)이 이관됨.

import { SimEngine, mulberry32, hashSnapshot } from '../engine.js';

let pass = 0, fail = 0;
function check(name, cond) {
  if (cond) { pass++; console.log(`  ✅ ${name}`); }
  else { fail++; console.log(`  ❌ ${name}`); }
}

// 대칭 PvP 맵 (본진2 + 중립2)
function makeMap() {
  return {
    world: { w: 1, h: 2.2 }, growthMult: 1.5, aiLevel: 3,
    castles: [
      { x: 0.5, y: 0.10, owner: 1, name: '본진A', primary: 'spear',   troops: { spear: 40, cavalry: 10, archer: 10 }, size: 1.15, trait: 'prod' },
      { x: 0.5, y: 0.90, owner: 2, name: '본진B', primary: 'spear',   troops: { spear: 40, cavalry: 10, archer: 10 }, size: 1.15, trait: 'prod' },
      { x: 0.3, y: 0.50, owner: 0, name: '중립1', primary: 'archer',  troops: { spear: 4,  cavalry: 3, archer: 3 }, size: 0.9, trait: 'def' },
      { x: 0.7, y: 0.50, owner: 0, name: '중립2', primary: 'cavalry', troops: { spear: 4,  cavalry: 3, archer: 3 }, size: 0.9, trait: 'atk' },
    ],
  };
}

// 고정 명령 스크립트: 특정 틱에 성→목표 출진 (fromId/toId = castles 인덱스)
const SCRIPT = [
  { tick: 5,   from: 0, to: 2, unit: 'cavalry' }, // A → 중립1
  { tick: 5,   from: 0, to: 3, unit: 'archer'  }, // A → 중립2
  { tick: 120, from: 0, to: 1, unit: 'spear'   }, // A 본진 → B 본진 (본격 공성)
  { tick: 120, from: 0, to: 1, unit: 'cavalry' },
  { tick: 300, from: 0, to: 1, unit: 'archer'  },
];

function runMatch(seed, steps) {
  const eng = new SimEngine(makeMap(), seed);
  const events = [];
  for (let t = 0; t < steps; t++) {
    for (const cmd of SCRIPT) {
      if (cmd.tick === t) eng.enqueue('p1', { type: 'SEND_ARMY', fromId: cmd.from, toId: cmd.to, unit: cmd.unit });
    }
    const ev = eng.step(1 / 15);
    for (const e of ev) events.push({ t, ...e });
    if (eng.winner != null) break;
  }
  return { eng, hash: hashSnapshot(eng.snapshot()), events };
}

console.log('── 1) RNG 스트림 결정론 ──');
{
  const a = mulberry32(42), b = mulberry32(42), c = mulberry32(43);
  const sA = Array.from({ length: 8 }, () => a());
  const sB = Array.from({ length: 8 }, () => b());
  const sC = Array.from({ length: 8 }, () => c());
  check('같은 seed → 동일 수열', JSON.stringify(sA) === JSON.stringify(sB));
  check('다른 seed → 상이 수열', JSON.stringify(sA) !== JSON.stringify(sC));
}

console.log('── 2) 전체 전장 시뮬 결정론 (동일 seed+명령열 2회) ──');
{
  const r1 = runMatch(12345, 4000);
  const r2 = runMatch(12345, 4000);
  check(`동일 최종해시 (${r1.hash})`, r1.hash === r2.hash);
  check('동일 이벤트열', JSON.stringify(r1.events) === JSON.stringify(r2.events));
}

console.log('── 3) 다른 seed → (보통) 다른 전개 ──');
{
  const r1 = runMatch(1, 4000);
  const r2 = runMatch(999999, 4000);
  check('다른 seed → 상이 해시(또는 상이 결과)', r1.hash !== r2.hash || JSON.stringify(r1.events) !== JSON.stringify(r2.events));
}

console.log('── 4) 전투/공성/점령/승리가 실제 발생 ──');
{
  const { eng, events } = runMatch(777, 6000);
  const captures = events.filter(e => e.type === 'capture');
  const breaches = events.filter(e => e.type === 'wallBreach');
  const dead = events.filter(e => e.type === 'armyDead');
  check(`중립성 점령 발생 (${captures.length}건)`, captures.length >= 1);
  check(`성벽 돌파 발생 (${breaches.length}건)`, breaches.length >= 1);
  check(`부대 전멸 발생 (${dead.length}건)`, dead.length >= 1);
  check('승자 결정 (winner != null)', eng.winner != null);
  console.log(`     최종: winner=${eng.winner}, tick=${eng.tick}, 남은부대=${eng.armies.length}`);
  const owners = eng.snapshot().castles.map(c => c.owner);
  console.log(`     성 소유: [${owners.join(', ')}]`);
}

console.log('── 5) 생산 결정론 (단일 성, rng 무관 확정) ──');
{
  const map = { world: { w: 1, h: 1 }, castles: [
    { x: 0.5, y: 0.5, owner: 1, primary: 'spear', troops: { spear: 10, cavalry: 0, archer: 0 }, trait: 'prod' },
  ]};
  const e1 = new SimEngine(map, 1); for (let i = 0; i < 150; i++) e1.step(1 / 15);
  const e2 = new SimEngine(map, 2); for (let i = 0; i < 150; i++) e2.step(1 / 15);
  const t1 = e1.snapshot().castles[0].troops.spear;
  const t2 = e2.snapshot().castles[0].troops.spear;
  check(`생산은 seed 무관 동일 (${t1}==${t2}), 10→증가`, t1 === t2 && t1 > 10);
}

console.log(`\n결과: ${pass} 통과 / ${fail} 실패`);
process.exit(fail ? 1 : 0);
