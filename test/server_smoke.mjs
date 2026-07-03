// test/server_smoke.mjs — 중계서버 검증 (Node 내장 WebSocket 클라이언트).
//   서버를 서브프로세스로 띄우고: 닉네임 등록·중복체크·매칭(먼저=호스트)·중계·전적기록 확인.
import { spawn } from 'node:child_process';
import { fileURLToPath } from 'node:url';
import path from 'node:path';
import fs from 'node:fs';

const here = path.dirname(fileURLToPath(import.meta.url));
const root = path.dirname(here);
const PORT = 8899;
const DB = path.join(here, '.test_mp.db');
try { fs.rmSync(DB, { force: true }); } catch {}

let pass = 0, fail = 0;
const check = (n, c) => { if (c) { pass++; console.log('  ✅ ' + n); } else { fail++; console.log('  ❌ ' + n); } };
const sleep = (ms) => new Promise((r) => setTimeout(r, ms));

// 편의: WS 연결 + 메시지 큐
function connect() {
  const ws = new WebSocket('ws://127.0.0.1:' + PORT);
  ws._q = []; ws._waiters = [];
  ws.onmessage = (e) => { const m = JSON.parse(e.data); const w = ws._waiters.shift(); if (w) w(m); else ws._q.push(m); };
  ws.next = () => new Promise((res) => { if (ws._q.length) res(ws._q.shift()); else ws._waiters.push(res); });
  ws.j = (o) => ws.send(JSON.stringify(o));
  return new Promise((res) => { ws.onopen = () => res(ws); });
}

const srv = spawn(process.execPath, [path.join(root, 'server', 'mp_server.js')], {
  env: { ...process.env, PORT: String(PORT), DB_PATH: DB }, stdio: 'ignore',
});
await sleep(700);

try {
  console.log('── 1) 닉네임 등록 + 중복체크 ──');
  const a = await connect();
  a.j({ t: 'hello', nick: 'Alice' });
  const wa = await a.next();
  check('Alice 등록 welcome + uid', wa.t === 'welcome' && wa.nick === 'Alice' && !!wa.uid);
  const aUid = wa.uid;

  const dup = await connect();
  dup.j({ t: 'hello', nick: 'Alice' });
  const wd = await dup.next();
  check('중복 닉네임 거부', wd.t === 'error' && wd.code === 'dup');
  dup.close();

  const b = await connect();
  b.j({ t: 'hello', nick: 'Bob' });
  const wb = await b.next();
  check('Bob 등록', wb.t === 'welcome' && wb.nick === 'Bob');
  const bUid = wb.uid;

  console.log('── 2) 매칭: 먼저 큐 = 호스트 ──');
  a.j({ t: 'queue' });
  const aq = await a.next();
  check('A 대기(queued)', aq.t === 'queued');
  await sleep(50);
  b.j({ t: 'queue' });
  const am = await a.next(), bm = await b.next();
  check('A=호스트 (먼저 큐)', am.t === 'matched' && am.role === 'host' && am.opp === 'Bob');
  check('B=게스트 (나중 큐)', bm.t === 'matched' && bm.role === 'guest' && bm.opp === 'Alice');

  console.log('── 3) 중계: A→B, B→A ──');
  a.j({ t: 'relay', m: { hello: 'from-a' } });
  const br = await b.next();
  check('B가 A의 메시지 수신', br.t === 'relay' && br.m.hello === 'from-a');
  b.j({ t: 'relay', m: { hi: 'from-b' } });
  const ar = await a.next();
  check('A가 B의 메시지 수신', ar.t === 'relay' && ar.m.hi === 'from-b');

  console.log('── 4) 전적: 호스트가 결과 보고 → 승/패 기록 ──');
  a.j({ t: 'result', winner: 1 });   // side1(호스트=Alice) 승
  const as = await a.next(), bs = await b.next();
  check('Alice 전적 1승0패', as.t === 'stats' && as.wins === 1 && as.losses === 0);
  check('Bob 전적 0승1패', bs.t === 'stats' && bs.wins === 0 && bs.losses === 1);

  console.log('── 5) uid 재로그인 ──');
  const a2 = await connect();
  a2.j({ t: 'hello', uid: aUid });
  const w2 = await a2.next();
  check('uid로 재로그인(닉·전적 유지)', w2.t === 'welcome' && w2.nick === 'Alice' && w2.wins === 1);
  a2.close();

  a.close(); b.close();
} catch (e) {
  fail++; console.log('  ❌ 예외:', e.message);
} finally {
  srv.kill();
  await sleep(100);
  try { fs.rmSync(DB, { force: true }); } catch {}
}

console.log('\n결과: ' + pass + ' 통과 / ' + fail + ' 실패');
process.exit(fail ? 1 : 0);
