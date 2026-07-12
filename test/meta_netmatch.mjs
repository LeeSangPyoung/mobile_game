// test/meta_netmatch.mjs — 메타 로드아웃이 넷코드(호스트권위)로 교환·주입되는지 검증 (Node)
//   실행: node test/meta_netmatch.mjs
//
// 검증: 호스트는 자기 로드아웃을 갖고, 게스트가 HELLO로 상대 로드아웃을 보내면
//       호스트가 '게스트 로드아웃 수신 후' 엔진을 생성해 양측 보정을 주입한다.
//       또 게스트가 조작한 로드아웃도 engine 클램프로 무력화된다.
import { HostMatch, GuestMatch, makeLoopbackPair } from '../netmatch.js';

let pass = 0, fail = 0;
const check = (n, c) => { if (c) { pass++; console.log('  ✅ ' + n); } else { fail++; console.log('  ❌ ' + n); } };

function pvpMap() {
  const home = (x, y, o, n) => ({ x, y, owner: o, name: n, isHome: true, primary: 'spear', troops: { spear: 30, cavalry: 8, archer: 8 }, size: 1.25, trait: 'prod' });
  const neut = (x, y, n) => ({ x, y, owner: 0, name: n, primary: 'spear', troops: { spear: 10 }, size: 1.0, trait: 'prod' });
  return { world: { w: 1, h: 1.7 }, growthMult: 1.0, humanFactions: [1, 2],
    castles: [ home(0.5, 0.90, 1, 'A'), home(0.5, 0.10, 2, 'B'), neut(0.3, 0.5, 'n1'), neut(0.7, 0.5, 'n2'), neut(0.5, 0.5, 'n3') ] };
}
const STRONG = { upg: { unitAtk: 1.3, unitDef: 1.2, castleAtk: 1.3, castleDef: 1.4, prodRate: 1.5 },
  generals: [ { atk: 0.5, def: 0.3, cAtk: 0.4, cDef: 0.4, prod: 0.6, critChance: 0.3, critMult: 1.8 } ] };
const WEAK = { upg: {}, generals: [] };
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

console.log('── 1) 호스트는 게스트 로드아웃 수신 후 엔진 생성(메타 모드) ──');
{
  const [hCh, gCh] = makeLoopbackPair();
  const host = new HostMatch(pvpMap(), 4242, hCh, { hostSide: 1, guestSide: 2, hostLoadout: STRONG });
  check('메타 모드: start 전 엔진 미생성', host.eng === null && host.useLoadouts === true);
  const guest = new GuestMatch(gCh, { loadout: WEAK });
  host.start();
  check('게스트 join 전: 엔진 아직 없음', host.eng === null);
  guest.join();                       // HELLO {loadout: WEAK} 전달(루프백=동기)
  check('게스트 join 후: 엔진 생성됨', host.eng !== null);
  check('양측 로드아웃 주입됨(side 1·2 존재)', !!host.eng.side && !!host.eng.side[1] && !!host.eng.side[2]);
  check('호스트(1) 강함 보정, 게스트(2) 무보정', host.eng.castles[0].atkMul > 1 && host.eng.castles[1].atkMul === 1);
  check('게스트 START 수신', guest.map && guest.youSide === 2);
}

console.log('── 2) 대전 완주 + 강한(호스트) 측 우세 ──');
{
  const [hCh, gCh] = makeLoopbackPair();
  const host = new HostMatch(pvpMap(), 7, hCh, { hostSide: 1, guestSide: 2, hostLoadout: STRONG, snapEvery: 2 });
  const guest = new GuestMatch(gCh, { loadout: WEAK });
  host.start(); guest.join();
  let hT = 0, gT = 0;
  for (let t = 0; t < 30000 && !host.over; t++) {
    hT -= 1 / 15; if (hT <= 0) { hT = 2.5; for (const c of botCmds(host.eng.castles, 1)) host.hostCommand(c); }
    gT -= 1 / 15;
    if (gT <= 0 && guest.snap) { gT = 2.5; const v = guest.map.castles.map((mc, i) => ({ x: mc.x, y: mc.y, owner: guest.snap.castles[i].owner, troops: guest.snap.castles[i].troops })); for (const c of botCmds(v, 2)) guest.command(c); }
    host.tick();
  }
  check('대전 완주(승자 결정)', host.eng.winner != null);
  check('강한 로드아웃(호스트=side1) 승리', host.eng.winner === 1);
  console.log('     winner=' + host.eng.winner + ' tick=' + host.eng.tick);
}

console.log('── 3) 게스트 조작 로드아웃도 engine 클램프로 무력화 ──');
{
  const [hCh, gCh] = makeLoopbackPair();
  const CHEAT = { upg: { unitAtk: 9999, prodRate: 9999 }, generals: [ { atk: 9999, critChance: 9, critMult: 99 } ] };
  const host = new HostMatch(pvpMap(), 1, hCh, { hostSide: 1, guestSide: 2, hostLoadout: WEAK });
  const guest = new GuestMatch(gCh, { loadout: CHEAT });
  host.start(); guest.join();
  const gside = host.eng.side[2];
  check('게스트 업그레이드 3배 상한', gside.upg.unitAtk === 3 && gside.upg.prodRate === 3);
  check('게스트 장수버프/크리 상한 클램프', gside.gens[0].atk === 1 && gside.gens[0].critChance === 0.4 && gside.gens[0].critMult === 2);
}

console.log('\n결과: ' + pass + ' 통과 / ' + fail + ' 실패');
process.exit(fail ? 1 : 0);
