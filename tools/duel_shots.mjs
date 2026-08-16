// 리그 PoC 프레임 캡처 — 애니메이션을 눈으로 확인하려고 특정 프레임에서 멈춰 찍는다.
//   node tools/duel_shots.mjs heavy 0,10,21,26,32,45
import { spawn } from 'node:child_process';
import { mkdtemp, readFile, writeFile, rm } from 'node:fs/promises';
import { tmpdir } from 'node:os';
import { join } from 'node:path';

const CHROME = '/Applications/Google Chrome.app/Contents/MacOS/Google Chrome';
const move = process.argv[2] || 'heavy';
const frames = (process.argv[3] || '0,8,16,22,27,34,44').split(',').map(Number);
const outDir = process.argv[4] || '/private/tmp/claude-501/-Users-leesp-workspace-game2/31667c17-7e29-48d8-9309-2104d2ca79ca/scratchpad';

const wait = ms => new Promise(r => setTimeout(r, ms));
const profile = await mkdtemp(join(tmpdir(), 'duel-shot-'));
const child = spawn(CHROME, ['--headless=new', '--disable-gpu', '--remote-debugging-port=0',
  `--user-data-dir=${profile}`, '--window-size=1160,720',
  'http://127.0.0.1:5173/duel_rig_poc.html'], { stdio: 'ignore' });

async function port() {
  for (let i = 0; i < 80; i++) {
    try { return (await readFile(join(profile, 'DevToolsActivePort'), 'utf8')).split(/\r?\n/)[0]; }
    catch { await wait(120); }
  }
  throw new Error('DevTools 포트가 열리지 않았다');
}

try {
  const p = await port();
  const pages = await (await fetch(`http://127.0.0.1:${p}/json`)).json();
  const page = pages.find(x => x.type === 'page');
  const ws = new WebSocket(page.webSocketDebuggerUrl);
  await new Promise((res, rej) => { ws.onopen = res; ws.onerror = rej; });

  let id = 0; const pending = new Map(); const errors = [];
  ws.onmessage = ev => {
    const m = JSON.parse(ev.data);
    if (m.method === 'Runtime.exceptionThrown')
      errors.push(m.params?.exceptionDetails?.exception?.description || m.params?.exceptionDetails?.text);
    if (m.method === 'Runtime.consoleAPICalled' && m.params?.type === 'error')
      errors.push((m.params.args || []).map(a => a.value ?? a.description ?? '').join(' '));
    const r = pending.get(m.id); if (r) { pending.delete(m.id); r(m); }
  };
  const call = (method, params = {}) => new Promise(res => {
    const cid = ++id; pending.set(cid, res); ws.send(JSON.stringify({ id: cid, method, params }));
  });
  const evalJs = async expr => {
    const r = await call('Runtime.evaluate', { expression: expr, returnByValue: true, awaitPromise: true });
    if (r.result?.exceptionDetails) throw new Error(r.result.exceptionDetails.exception?.description);
    return r.result.result.value;
  };

  await call('Runtime.enable');
  await call('Page.enable');
  await wait(2500);

  const ok = await evalJs('typeof __poc !== "undefined"');
  if (!ok) throw new Error('__poc 훅이 없다 — 페이지 로드 실패?\n' + errors.join('\n'));

  for (const f of frames) {
    await evalJs(`__poc.freeze(${JSON.stringify(move)}, ${f})`);
    await wait(140);
    const shot = await call('Page.captureScreenshot', { format: 'png', fromSurface: true,
      clip: { x: 18, y: 96, width: 1122, height: 522, scale: 1 } });
    const path = join(outDir, `rig_${move}_${String(f).padStart(2, '0')}.png`);
    await writeFile(path, Buffer.from(shot.result.data, 'base64'));
    console.log('✓', path);
  }
  if (errors.length) console.log('\n런타임 오류:\n' + errors.join('\n'));
} finally {
  child.kill();
  await rm(profile, { recursive: true, force: true });
}
