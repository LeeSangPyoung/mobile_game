// test/mp_game_smoke.mjs — mp_game.html의 매칭+엔진+넷코드 통합을 Node로 검증(브라우저 없이).
//   공유 버스로 두 클라 시뮬: 먼저 큐 입장=호스트, 뒤=게스트 → 대전 완주 확인.
import { SimEngine, hashSnapshot } from '../engine.js';
import { HostMatch, GuestMatch } from '../netmatch.js';

let pass = 0, fail = 0;
const check = (n, c) => { if (c) { pass++; console.log('  ✅ ' + n); } else { fail++; console.log('  ❌ ' + n); } };

// 공유 버스(BroadcastChannel 모사): 자기 자신에겐 에코 안 함
function makeBus() {
  const clients = [];
  return {
    join() {
      const hs = [];
      const ep = {
        _hs: hs,
        send(m) { const c = JSON.parse(JSON.stringify(m)); for (const o of clients) if (o !== ep) for (const h of o._hs) h(c); },
        onMessage(cb) { hs.push(cb); },
      };
      clients.push(ep);
      return ep;
    },
  };
}

function pvpMap() {
  const home = (x, y, o, n) => ({ x, y, owner: o, name: n, isHome: true, primary: 'spear', troops: { spear: 30, cavalry: 8, archer: 8 }, size: 1.3, trait: 'prod' });
  const neu = (x, y, t, p) => ({ x, y, owner: 0, primary: p, troops: { spear: 5, cavalry: 4, archer: 4 }, size: 1.0, trait: t });
  return { world: { w: 1, h: 1.7 }, growthMult: 1.0, humanFactions: [1, 2], castles: [
    home(0.5, 0.90, 1, 'A'), home(0.5, 0.10, 2, 'B'),
    neu(0.5, 0.50, 'def', 'archer'),
    neu(0.24, 0.66, 'atk', 'cavalry'), neu(0.76, 0.34, 'atk', 'cavalry'),
    neu(0.76, 0.66, 'prod', 'spear'), neu(0.24, 0.34, 'prod', 'spear'),
  ]};
}

// 한 클라이언트: 매칭 로직(mp_game.html과 동일 구조)
function makeClient(bus, qtime, name) {
  const chan = bus.join();
  const st = { role: null, host: null, guest: null, mySide: null, gmap: null, qid: (Math.random() * 2e9) >>> 0, qtime, inQueue: true };
  const startGuest = () => {
    st.role = 'guest';
    st.guest = new GuestMatch(chan, { onStart: (mm) => { st.mySide = mm.youSide; st.gmap = mm.map; }, onEnd: () => {} });
    st.guest.join();
  };
  chan.onMessage((m) => {
    if (!m) return;
    if (m.t === 'Q') {
      if (!st.inQueue || st.role || m.id === st.qid) return;
      const iAmHost = (st.qtime < m.jt) || (st.qtime === m.jt && st.qid < m.id);
      if (iAmHost) { st.inQueue = false; st.role = 'host'; st.mySide = 1; st.gmap = pvpMap(); st.host = new HostMatch(st.gmap, 4242, chan, { hostSide: 1, guestSide: 2, snapEvery: 1 }); st.host.start(); }
      // 아니면 대기 → START 기다림
    } else if (m.t === 'START' && !st.role) {
      st.inQueue = false; startGuest();
    }
  });
  st.q = () => { if (st.inQueue) chan.send({ t: 'Q', id: st.qid, jt: st.qtime }); };
  return st;
}

// 간이 봇: side 성이 20+면 가장 가까운 비아군성으로 전병력(상대본진 우선)
function botCmds(castles, side, thr) {
  const cmds = [];
  castles.forEach((c, i) => {
    if (c.owner !== side) return;
    const tot = c.troops.spear + c.troops.cavalry + c.troops.archer;
    if (tot < (thr || 20)) return;
    let best = -1, bd = Infinity;
    castles.forEach((k, ki) => { if (k.owner === side) return; const bias = (k.isHome && k.owner !== 0 && k.owner !== side) ? -0.4 : 0; const d = Math.hypot(c.x - k.x, c.y - k.y) + bias; if (d < bd) { bd = d; best = ki; } });
    if (best < 0) return;
    for (const u of ['spear', 'cavalry', 'archer']) if (c.troops[u] > 0) cmds.push({ type: 'SEND_ARMY', fromId: i, toId: best, unit: u });
  });
  return cmds;
}

console.log('── 1) 매칭: 먼저 큐 입장(qtime 작은 쪽)=호스트 ──');
{
  const bus = makeBus();
  const a = makeClient(bus, 1000, 'A');  // 먼저
  const b = makeClient(bus, 2000, 'B');  // 나중
  a.q(); b.q(); a.q(); b.q();  // Q 교환
  check('먼저 들어온 A=호스트', a.role === 'host');
  check('나중 들어온 B=게스트', b.role === 'guest');
  check('게스트 START 수신(map/side)', b.mySide === 2 && !!b.gmap);
}

console.log('── 2) 실제 대전 완주(호스트 권위) + 게스트 동기화 ──');
{
  const bus = makeBus();
  const a = makeClient(bus, 1000);   // host (side1)
  const b = makeClient(bus, 2000);   // guest (side2)
  a.q(); b.q(); a.q(); b.q();
  const host = a.host, guest = b.guest;
  let hT = 0, gT = 0;
  for (let t = 0; t < 30000 && !host.over; t++) {
    hT -= 1 / 15; if (hT <= 0) { hT = 2.5; for (const c of botCmds(host.eng.castles, 1, 15)) host.hostCommand(c); }
    gT -= 1 / 15;
    if (gT <= 0 && guest.snap) { gT = 6.0; const v = guest.map.castles.map((mc, i) => ({ x: mc.x, y: mc.y, isHome: mc.isHome, owner: guest.snap.castles[i].owner, troops: guest.snap.castles[i].troops })); for (const c of botCmds(v, 2, 40)) guest.command(c); }
    host.tick();
  }
  check('대전 완주(승자 결정)', host.eng.winner != null);
  check('게스트 END 수신, 승자 일치', guest.over && guest.winner === host.eng.winner);
  check('게스트 스냅샷 == 호스트 권위', hashSnapshot(guest.snap) === hashSnapshot(host.eng.snapshot()));
  console.log('     winner=' + host.eng.winner + ' reason=' + guest.reason + ' tick=' + host.eng.tick);
}

console.log('\\n결과: ' + pass + ' 통과 / ' + fail + ' 실패');
process.exit(fail ? 1 : 0);
