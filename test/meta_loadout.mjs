// test/meta_loadout.mjs — 진영별 장수 로드아웃(메타) 결정론·공정성 검증 (Node)
//   실행: node test/meta_loadout.mjs
//
// 검증: (1) 로드아웃 없으면 기존과 동일(무보정)  (2) 양 진영 모두 보정 적용(공정)
//       (3) 같은 seed+로드아웃 → 동일 결과(결정론)  (4) 강한 장수측이 이긴다(효과 확인)
//       (5) 생산보정이 양측 모두 적용  (6) 게스트 조작값 클램프(치팅 방지)
import { SimEngine, hashSnapshot } from '../engine.js';

let pass = 0, fail = 0;
const check = (n, c) => { if (c) { pass++; console.log('  ✅ ' + n); } else { fail++; console.log('  ❌ ' + n); } };

function pvpMap() {
  const home = (x, y, o, n) => ({ x, y, owner: o, name: n, isHome: true, primary: 'spear', troops: { spear: 30, cavalry: 8, archer: 8 }, size: 1.25, trait: 'prod' });
  const neut = (x, y, n) => ({ x, y, owner: 0, name: n, primary: 'spear', troops: { spear: 10, cavalry: 0, archer: 0 }, size: 1.0, trait: 'prod' });
  return {
    world: { w: 1, h: 1.7 }, growthMult: 1.0, humanFactions: [1, 2],
    castles: [
      home(0.5, 0.90, 1, 'A'), home(0.5, 0.10, 2, 'B'),
      neut(0.30, 0.50, 'n1'), neut(0.70, 0.50, 'n2'), neut(0.50, 0.50, 'n3'),
    ],
  };
}
// 강한 장수 3명(공/방/성 버프 + 크리)
const STRONG = { upg: { unitAtk: 1.3, unitDef: 1.2, castleAtk: 1.3, castleDef: 1.4, prodRate: 1.5 },
  generals: [ { atk: 0.5, def: 0.3, cAtk: 0.4, cDef: 0.4, prod: 0.6, critChance: 0.3, critMult: 1.8 },
              { atk: 0.4, def: 0.3, cAtk: 0.3, cDef: 0.3, prod: 0.4, critChance: 0.2, critMult: 1.6 },
              { atk: 0.3, def: 0.2, cAtk: 0.2, cDef: 0.2, prod: 0.3, critChance: 0.1, critMult: 1.4 } ] };
const WEAK = { upg: {}, generals: [] };  // 무장수·무업그레이드

// 봇: 각 성에서 가장 가까운 비아군 성으로 전 병종 송출
function botCmds(castles, side, thr = 15) {
  const cmds = [];
  castles.forEach((c, i) => {
    if (c.owner !== side) return;
    const tot = (c.troops.spear | 0) + (c.troops.cavalry | 0) + (c.troops.archer | 0);
    if (tot < thr) return;
    let best = -1, bd = Infinity;
    castles.forEach((k, ki) => { if (k.owner === side) return; const d = Math.hypot(c.x - k.x, c.y - k.y); if (d < bd) { bd = d; best = ki; } });
    if (best < 0) return;
    for (const u of ['spear', 'cavalry', 'archer']) if (c.troops[u] > 0) cmds.push({ type: 'SEND_ARMY', fromId: i, toId: best, unit: u });
  });
  return cmds;
}
function runMatch(seed, loadouts, maxTicks = 30000) {
  const eng = new SimEngine(pvpMap(), seed, loadouts ? { loadouts } : {});
  let t1 = 0, t2 = 0;
  for (let t = 0; t < maxTicks && eng.winner == null; t++) {
    t1 -= 1 / 15; if (t1 <= 0) { t1 = 2.5; for (const c of botCmds(eng.castles, 1)) eng.enqueue(1, c); }
    t2 -= 1 / 15; if (t2 <= 0) { t2 = 2.5; for (const c of botCmds(eng.castles, 2)) eng.enqueue(2, c); }
    eng.step();
  }
  return eng;
}

console.log('── 1) 로드아웃 없으면 무보정(기존과 동일) ──');
{
  const eng = new SimEngine(pvpMap(), 7, {});
  check('pvp=false, side=null', eng.pvp === false && eng.side === null);
  check('성 atkMul/_prodMul 무보정', eng.castles[0].atkMul === 1 && (eng.castles[0]._prodMul === undefined));
}

console.log('── 2) 양 진영 모두 보정 적용(공정) + 커맨더 배정 ──');
{
  const eng = new SimEngine(pvpMap(), 7, { loadouts: { 1: STRONG, 2: STRONG } });
  const A = eng.castles[0], B = eng.castles[1];
  check('본진 A(side1) 커맨더 배정됨', A._cmdSide === 1 && A._cmdIdx === 0);
  check('본진 B(side2) 커맨더 배정됨', B._cmdSide === 2 && B._cmdIdx === 0);
  check('양측 본진 동일 보정(대칭)', A.atkMul === B.atkMul && A._prodMul === B._prodMul && A.critChance === B.critChance);
  check('보정이 실제로 1 초과', A.atkMul > 1 && A._prodMul > 1 && A.critChance > 0);
  check('중립성 무보정', eng.castles[2].atkMul === 1 && eng.castles[2].critChance === 0);
}

console.log('── 3) 결정론: 같은 seed+로드아웃 2회 동일 ──');
{
  const e1 = runMatch(555, { 1: STRONG, 2: WEAK });
  const e2 = runMatch(555, { 1: STRONG, 2: WEAK });
  check('동일 최종상태(해시 일치)', hashSnapshot(e1.snapshot()) === hashSnapshot(e2.snapshot()));
  check('승자·tick 동일', e1.winner === e2.winner && e1.tick === e2.tick);
}

console.log('── 4) 강한 장수측이 이긴다(효과 확인, 다중 seed 다수결) ──');
{
  let s1win = 0, s2win = 0;
  for (const seed of [1, 2, 3, 4, 5, 6, 7]) {
    const e = runMatch(seed, { 1: STRONG, 2: WEAK });   // side1 강함
    if (e.winner === 1) s1win++; else if (e.winner === 2) s2win++;
  }
  console.log('     강한쪽(side1) 승: ' + s1win + ' / 약한쪽(side2) 승: ' + s2win);
  check('강한 장수측(side1)이 과반 승리', s1win > s2win);
}

console.log('── 5) 로드아웃 스왑 → 결과도 스왑(순수 대칭) ──');
{
  const a = runMatch(99, { 1: STRONG, 2: WEAK });   // side1 강함
  const b = runMatch(99, { 1: WEAK, 2: STRONG });   // side2 강함
  check('스왑 시 승자도 반대(맵/시드 동일, 보정만 반전)', a.winner === 1 && b.winner === 2);
}

console.log('── 6) 생산 보정 양측 적용(무전투 순수 생산) ──');
{
  // 명령 없이 생산만 — prodRate 높은 쪽이 더 빨리 증강.
  const eng = new SimEngine(pvpMap(), 3, { loadouts: { 1: STRONG, 2: WEAK } });
  for (let t = 0; t < 200; t++) eng.step();
  const s1 = eng.castles[0].troops, s2 = eng.castles[1].troops;
  const tot = (x) => (x.spear | 0) + (x.cavalry | 0) + (x.archer | 0);
  console.log('     side1 본진 병력=' + tot(s1) + ' / side2 본진 병력=' + tot(s2));
  check('생산보정 큰 side1이 side2보다 병력 많음(양측 _prodMul 동작)', tot(s1) > tot(s2));
}

console.log('── 7) 게스트 조작값 클램프(치팅 방지) ──');
{
  const CHEAT = { upg: { unitAtk: 9999, prodRate: 9999 }, generals: [ { atk: 9999, def: 9999, critChance: 9, critMult: 99 } ] };
  const eng = new SimEngine(pvpMap(), 1, { loadouts: { 1: CHEAT, 2: WEAK } });
  const A = eng.castles[0];
  const g = eng.side[1].gens[0];
  check('업그레이드 3배 상한 클램프', eng.side[1].upg.unitAtk === 3 && eng.side[1].upg.prodRate === 3);
  check('장수 버프 분수 1.0 상한, 크리 0.4/2.0 상한', g.atk === 1 && g.def === 1 && g.critChance === 0.4 && g.critMult === 2);
  check('클램프 후에도 유한한 보정', Number.isFinite(A.atkMul) && A.atkMul <= 3 * 2);
}

console.log('\n결과: ' + pass + ' 통과 / ' + fail + ' 실패');
process.exit(fail ? 1 : 0);
