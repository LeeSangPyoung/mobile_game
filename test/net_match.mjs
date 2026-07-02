// test/net_match.mjs — 호스트 권위 넷코드 검증 (Node, 인메모리 채널)
//   실행: node test/net_match.mjs
//
// 검증: 호스트가 양측 명령을 권위 적용하고, 게스트가 스냅샷으로 상태를 따라오며,
//       치팅 명령(상대 성 조종)이 거부되고, 양측이 같은 승부를 본다.

import { SimEngine, hashSnapshot } from '../engine.js';
import { HostMatch, GuestMatch, makeLoopbackPair } from '../netmatch.js';

let pass = 0, fail = 0;
const check = (n, c) => { if (c) { pass++; console.log(`  ✅ ${n}`); } else { fail++; console.log(`  ❌ ${n}`); } };

function pvpMap() {
  const home = (x, y, o, n) => ({ x, y, owner: o, name: n, isHome: true, primary: 'spear', troops: { spear: 30, cavalry: 8, archer: 8 }, size: 1.25, trait: 'prod' });
  const neu = (x, y, t, p) => ({ x, y, owner: 0, primary: p, troops: { spear: 5, cavalry: 4, archer: 4 }, size: 0.95, trait: t });
  return {
    world: { w: 1, h: 1.7 }, growthMult: 1.0, humanFactions: [1, 2],
    castles: [
      home(0.5, 0.90, 1, 'A'), home(0.5, 0.10, 2, 'B'),
      neu(0.5, 0.50, 'def', 'archer'),
      neu(0.24, 0.66, 'atk', 'cavalry'), neu(0.76, 0.34, 'atk', 'cavalry'),
      neu(0.76, 0.66, 'prod', 'spear'), neu(0.24, 0.34, 'prod', 'spear'),
    ],
  };
}

// 간이 봇: side의 성이 병력 thr+면 가장 가까운 비아군성으로 전병력(상대본진 우선)
function botCommands(castles, side, thr = 20) {
  const cmds = [];
  castles.forEach((c, i) => {
    if (c.owner !== side) return;
    const tot = c.troops.spear + c.troops.cavalry + c.troops.archer;
    if (tot < thr) return;
    let best = -1, bd = Infinity;
    castles.forEach((k, ki) => {
      if (k.owner === side) return;
      const bias = (k.isHome && k.owner !== 0 && k.owner !== side) ? -0.4 : 0;
      const d = Math.hypot(c.x - k.x, c.y - k.y) + bias;
      if (d < bd) { bd = d; best = ki; }
    });
    if (best < 0) return;
    for (const u of ['spear', 'cavalry', 'archer']) if (c.troops[u] > 0) cmds.push({ type: 'SEND_ARMY', fromId: i, toId: best, unit: u });
  });
  return cmds;
}

console.log('── 1) 호스트 권위 대전 완주 + 게스트 동기화 ──');
{
  const [hCh, gCh] = makeLoopbackPair();
  const host = new HostMatch(pvpMap(), 4242, hCh, { hostSide: 1, guestSide: 2, snapEvery: 2 });
  const guest = new GuestMatch(gCh);
  host.start();
  check('게스트 START 수신(youSide=2, map)', guest.youSide === 2 && !!guest.map);

  let hTimer = 0, gTimer = 0;
  for (let t = 0; t < 20000 && !host.over; t++) {
    // 호스트 로컬봇(side1)
    hTimer -= 1 / 15;
    if (hTimer <= 0) { hTimer = 2.5; for (const cmd of botCommands(host.eng.castles, 1, 15)) host.hostCommand(cmd); }
    // 게스트 봇(side2) — 게스트는 자기 스냅샷 기준으로 명령(호스트가 검증)
    gTimer -= 1 / 15;
    if (gTimer <= 0 && guest.snap) {
      gTimer = 6.0;
      // 게스트는 map(정적 좌표)+snap(소유/병력)으로 자기 성 파악
      const view = guest.map.castles.map((mc, i) => ({ x: mc.x, y: mc.y, isHome: mc.isHome, owner: guest.snap.castles[i].owner, troops: guest.snap.castles[i].troops }));
      for (const cmd of botCommands(view, 2, 40)) guest.command(cmd);
    }
    host.tick();
  }
  check('대전 완주(승자 결정)', host.eng.winner != null);
  check('게스트 END 수신, 승자 일치', guest.over && guest.winner === host.eng.winner);
  // 게스트 최신 스냅샷이 호스트 권위 상태와 일치(마지막 방송 기준)
  check('게스트 스냅샷 == 호스트 권위 스냅샷', hashSnapshot(guest.snap) === hashSnapshot(host.eng.snapshot()));
  console.log(`     winner=${host.eng.winner} reason=${guest.reason} tick=${host.eng.tick}`);
}

console.log('── 2) 치팅 거부 — 게스트가 상대(호스트) 성을 조종 시도 ──');
{
  const [hCh, gCh] = makeLoopbackPair();
  const host = new HostMatch(pvpMap(), 1, hCh, { hostSide: 1, guestSide: 2 });
  const guest = new GuestMatch(gCh);
  host.start();
  const before = host.eng.castles[0].troops.spear; // side1(호스트) 본진
  guest.command({ type: 'SEND_ARMY', fromId: 0, toId: 1, unit: 'spear' }); // 게스트가 host 성(0) 조종 시도
  host.tick();
  const after = host.eng.castles[0].troops.spear;
  check('상대 성 명령 거부(병력 불변, 부대 미생성)', before === after && host.eng.armies.length === 0);
  // 자기 성(side2, index1)은 정상 조종
  guest.command({ type: 'SEND_ARMY', fromId: 1, toId: 2, unit: 'spear' });
  host.tick();
  check('자기 성 명령은 정상 처리(부대 생성)', host.eng.armies.some(a => a.owner === 2));
}

console.log('── 3) 넷코드 결정론 — 같은 seed+명령타이밍 2회 동일 ──');
{
  function runNet(seed) {
    const [hCh, gCh] = makeLoopbackPair();
    const host = new HostMatch(pvpMap(), seed, hCh, { hostSide: 1, guestSide: 2 });
    const guest = new GuestMatch(gCh);
    host.start();
    let hT = 0, gT = 0;
    for (let t = 0; t < 20000 && !host.over; t++) {
      hT -= 1 / 15; if (hT <= 0) { hT = 2.5; for (const c of botCommands(host.eng.castles, 1, 15)) host.hostCommand(c); }
      gT -= 1 / 15;
      if (gT <= 0 && guest.snap) { gT = 6.0; const v = guest.map.castles.map((mc, i) => ({ x: mc.x, y: mc.y, isHome: mc.isHome, owner: guest.snap.castles[i].owner, troops: guest.snap.castles[i].troops })); for (const c of botCommands(v, 2, 40)) guest.command(c); }
      host.tick();
    }
    return { w: host.eng.winner, tick: host.eng.tick, hash: hashSnapshot(host.eng.snapshot()) };
  }
  const a = runNet(999), b = runNet(999);
  check(`동일 결과 (winner=${a.w}, tick=${a.tick})`, a.w === b.w && a.tick === b.tick && a.hash === b.hash);
}

console.log(`\n결과: ${pass} 통과 / ${fail} 실패`);
process.exit(fail ? 1 : 0);
