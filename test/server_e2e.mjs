// test/server_e2e.mjs — 서버+넷코드+엔진 전체를 '실제 WebSocket 중계'로 end-to-end 검증.
//   두 Node 클라가 서버 접속 → 닉등록 → 매칭 → HostMatch/GuestMatch를 WS중계로 실행 → 대전완주 → 전적기록.
//   (브라우저 클라가 하는 일에서 '렌더'만 뺀 전 경로)
import { spawn } from 'node:child_process';
import { fileURLToPath } from 'node:url';
import path from 'node:path';
import fs from 'node:fs';
import { SimEngine, hashSnapshot } from '../engine.js';
import { HostMatch, GuestMatch } from '../netmatch.js';

const here = path.dirname(fileURLToPath(import.meta.url));
const root = path.dirname(here);
const PORT = 8898, DB = path.join(here, '.e2e_mp.db');
try { fs.rmSync(DB, { force: true }); } catch {}
let pass = 0, fail = 0;
const check = (n, c) => { if (c) { pass++; console.log('  ✅ ' + n); } else { fail++; console.log('  ❌ ' + n); } };
const sleep = (ms) => new Promise((r) => setTimeout(r, ms));

function pvpMap() {
  const home = (x, y, o, n) => ({ x, y, owner: o, name: n, isHome: true, primary: 'spear', troops: { spear: 30, cavalry: 8, archer: 8 }, size: 1.3, trait: 'prod' });
  const neu = (x, y, t, p) => ({ x, y, owner: 0, primary: p, troops: { spear: 5, cavalry: 4, archer: 4 }, size: 1.0, trait: t });
  return { world: { w: 1, h: 1.7 }, growthMult: 1.0, humanFactions: [1, 2], castles: [
    home(0.5, 0.90, 1, 'A'), home(0.5, 0.10, 2, 'B'), neu(0.5, 0.50, 'def', 'archer'),
    neu(0.24, 0.66, 'atk', 'cavalry'), neu(0.76, 0.34, 'atk', 'cavalry'), neu(0.76, 0.66, 'prod', 'spear'), neu(0.24, 0.34, 'prod', 'spear'),
  ]};
}
function botCmds(castles, side, thr) {
  const cmds = [];
  castles.forEach((c, i) => { if (c.owner !== side) return; const tot = c.troops.spear + c.troops.cavalry + c.troops.archer; if (tot < (thr || 20)) return;
    let best = -1, bd = Infinity; castles.forEach((k, ki) => { if (k.owner === side) return; const bias = (k.isHome && k.owner !== 0 && k.owner !== side) ? -0.4 : 0; const d = Math.hypot(c.x - k.x, c.y - k.y) + bias; if (d < bd) { bd = d; best = ki; } });
    if (best < 0) return; for (const u of ['spear', 'cavalry', 'archer']) if (c.troops[u] > 0) cmds.push({ type: 'SEND_ARMY', fromId: i, toId: best, unit: u }); });
  return cmds;
}

// WS 클라(서버앱과 동일 프로토콜): 닉등록·큐·매칭·relay채널
function client(nick) {
  const ws = new WebSocket('ws://127.0.0.1:' + PORT);
  const app = { ws, role: null, host: null, guest: null, mySide: null, gmap: null, stats: null, matched: false, welcomed: false,
    chan: { _hs: [], send(m) { ws.send(JSON.stringify({ t: 'relay', m })); }, onMessage(cb) { this._hs.push(cb); }, _deliver(m) { for (const h of this._hs) h(m); } } };
  ws.onmessage = (e) => {
    const m = JSON.parse(e.data);
    if (m.t === 'welcome') { app.welcomed = true; app.uid = m.uid; app.stats = { wins: m.wins, losses: m.losses }; }
    else if (m.t === 'matched') {
      app.matched = true; app.role = m.role;
      if (m.role === 'host') { app.mySide = 1; app.gmap = pvpMap(); app.host = new HostMatch(app.gmap, (Math.random() * 2e9) >>> 0, app.chan, { hostSide: 1, guestSide: 2, snapEvery: 1 }); app.host.start(); }
      else { app.guest = new GuestMatch(app.chan, { onStart: (mm) => { app.mySide = mm.youSide; app.gmap = mm.map; }, onEnd: () => {} }); app.guest.join(); }
    }
    else if (m.t === 'stats') { app.stats = { wins: m.wins, losses: m.losses }; }
    else if (m.t === 'relay') { app.chan._deliver(m.m); }
  };
  return new Promise((res) => { ws.onopen = () => { ws.send(JSON.stringify({ t: 'hello', nick })); res(app); }; });
}

const srv = spawn(process.execPath, [path.join(root, 'server', 'mp_server.js')], { env: { ...process.env, PORT: String(PORT), DB_PATH: DB }, stdio: 'ignore' });
await sleep(700);
try {
  console.log('── 서버 통한 실제 대전 (WS 중계) ──');
  const A = await client('Kim'); const B = await client('Lee');
  await sleep(150);
  check('둘 다 welcome', A.welcomed && B.welcomed);

  A.ws.send(JSON.stringify({ t: 'queue' })); await sleep(60);
  B.ws.send(JSON.stringify({ t: 'queue' })); await sleep(200);
  check('A=호스트 매칭', A.role === 'host'); check('B=게스트 매칭', B.role === 'guest');
  await sleep(150);
  check('게스트 START 수신(map/side)', B.mySide === 2 && !!B.gmap);

  // 호스트 루프 + 봇 명령 (실제 브라우저의 host.tick 대체)
  let hT = 0, gT = 0;
  for (let t = 0; t < 30000 && A.host && !A.host.over; t++) {
    hT -= 1 / 15; if (hT <= 0) { hT = 2.5; for (const c of botCmds(A.host.eng.castles, 1, 15)) A.host.hostCommand(c); }
    gT -= 1 / 15;
    if (gT <= 0 && B.guest && B.guest.snap) { gT = 6.0; const v = B.guest.map.castles.map((mc, i) => ({ x: mc.x, y: mc.y, isHome: mc.isHome, owner: B.guest.snap.castles[i].owner, troops: B.guest.snap.castles[i].troops })); for (const c of botCmds(v, 2, 40)) B.guest.command(c); }
    A.host.tick();
    if (t % 40 === 0) await sleep(0); // 이벤트 루프 양보(WS relay 처리)
  }
  check('대전 완주(승자)', A.host.eng.winner != null);
  await sleep(150);
  check('게스트도 종료·승자 일치', B.guest.over && B.guest.winner === A.host.eng.winner);
  check('게스트 스냅샷 == 호스트 권위', hashSnapshot(B.guest.snap) === hashSnapshot(A.host.eng.snapshot()));

  // 호스트가 결과 보고 → 전적 기록
  A.ws.send(JSON.stringify({ t: 'result', winner: A.host.eng.winner }));
  await sleep(200);
  const w = A.host.eng.winner;
  check('승자측 1승 기록', (w === 1 ? A.stats.wins : B.stats.wins) === 1);
  check('패자측 1패 기록', (w === 1 ? B.stats.losses : A.stats.losses) === 1);
  console.log('     winner=' + w + ' tick=' + A.host.eng.tick + ' A전적=' + JSON.stringify(A.stats) + ' B전적=' + JSON.stringify(B.stats));
  A.ws.close(); B.ws.close();
} catch (e) { fail++; console.log('  ❌ 예외:', e.stack || e.message); }
finally { srv.kill(); await sleep(100); try { fs.rmSync(DB, { force: true }); } catch {} }

console.log('\n결과: ' + pass + ' 통과 / ' + fail + ' 실패');
process.exit(fail ? 1 : 0);
