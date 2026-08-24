#!/usr/bin/env node
/**
 * Compare an attack with and without its optional swing sprite through the
 * actual duel canvas renderer.  This is deliberately a measurement aid, not
 * an auto-delete tool: weapon arcs, smear, and pose silhouette all contribute
 * to a legitimate large pixel delta.
 *
 * Usage:
 *   node tools/measure_swing_runtime.mjs lu_bu
 *   node tools/measure_swing_runtime.mjs --all --json > swing-runtime.json
 *   node tools/measure_swing_runtime.mjs --capture taishi_ci:slash
 *
 * A local server for the project must be available at 127.0.0.1:5173.
 */

import { spawn } from 'node:child_process';
import { mkdtemp, readFile, readdir, writeFile } from 'node:fs/promises';
import { tmpdir } from 'node:os';
import { join } from 'node:path';

const ROOT = new URL('..', import.meta.url).pathname.replace(/^\//, '');
const ASSETS = join(ROOT, 'assets', 'arcade_duel');
const CHROME = 'C:/Program Files/Google/Chrome/Application/chrome.exe';
const BASE_URL = 'http://127.0.0.1:5173/duel_v2.html?embed=1&dummy=1';
const wait = ms => new Promise(resolve => setTimeout(resolve, ms));

const args = process.argv.slice(2);
const json = args.includes('--json');
const all = args.includes('--all');
const captureAt = args.indexOf('--capture');
const capture = captureAt >= 0 ? args[captureAt + 1] : null;
const requested = args.filter(arg => !arg.startsWith('--'));

async function swingGenerals() {
  const dirs = await readdir(ASSETS, { withFileTypes: true });
  const out = [];
  for (const entry of dirs) {
    if (!entry.isDirectory() || !entry.name.endsWith('_states')) continue;
    const gid = entry.name.slice(0, -'_states'.length);
    const meta = JSON.parse(await readFile(join(ASSETS, entry.name, 'poses.json'), 'utf8'));
    if (meta.swing) out.push(gid);
  }
  return out.sort();
}

async function connect() {
  const profile = await mkdtemp(join(tmpdir(), 'duel-swing-'));
  const child = spawn(CHROME, [
    '--headless=new', '--disable-gpu', '--disable-background-timer-throttling',
    '--remote-debugging-port=0', `--user-data-dir=${profile}`,
    '--window-size=430,932', BASE_URL,
  ], { stdio: 'ignore' });
  let port;
  for (let i = 0; i < 80; i++) {
    try { port = (await readFile(join(profile, 'DevToolsActivePort'), 'utf8')).split(/\r?\n/)[0]; break; }
    catch { await wait(150); }
  }
  if (!port) { child.kill(); throw new Error('Chrome remote debugging did not start.'); }
  const pages = await (await fetch(`http://127.0.0.1:${port}/json`)).json();
  const page = pages.find(item => item.type === 'page');
  const socket = new WebSocket(page.webSocketDebuggerUrl);
  const pending = new Map(); let id = 0;
  socket.onmessage = event => {
    const msg = JSON.parse(event.data);
    if (msg.id && pending.has(msg.id)) { pending.get(msg.id)(msg); pending.delete(msg.id); }
  };
  await new Promise(resolve => { socket.onopen = resolve; });
  const send = (method, params = {}) => new Promise(resolve => {
    const callId = ++id; pending.set(callId, resolve);
    socket.send(JSON.stringify({ id: callId, method, params }));
  });
  const evaluate = async expression => {
    const result = await send('Runtime.evaluate', { expression, awaitPromise: true, returnByValue: true });
    if (result.result?.exceptionDetails) throw new Error(result.result.exceptionDetails.text || 'Runtime.evaluate failed');
    return result.result?.result?.value;
  };
  await send('Runtime.enable');
  await wait(6500);
  // Let the existing animation callback finish once, then prevent it from
  // queuing another one. Measurements drive update/render explicitly.
  await evaluate('window.__swingAuditStop=true; window.requestAnimationFrame=()=>0; true');
  await wait(120);
  return { child, socket, send, evaluate };
}

async function captureReview(browser, spec) {
  const [gid, attack] = spec.split(':');
  const moveKey = attack === 'slash' ? 'light' : attack;
  if (!gid || !['slash', 'thrust', 'heavy'].includes(attack))
    throw new Error('Use --capture general:slash|thrust|heavy');
  const output = await mkdtemp(join(tmpdir(), 'duel-swing-captures-'));
  const labels = ['pre', 'middle', 'impact'];
  const files = [];
  for (const enabled of [true, false]) {
    for (const label of labels) {
      await browser.evaluate(`(async () => {
        await loadGeneral(${JSON.stringify(gid)}, 'player');
        $('intro').hidden = true; $('overlay').hidden = true;
        document.body.classList.remove('introing');
        resetMatch(); phase = 'fight'; DUMMY = 1;
        P.x = STAGE_W / 2 - 190; B.x = STAGE_W / 2 + 190; P.z = B.z = Z_MAX / 2;
        P.dir = 1; B.dir = -1;
        for (let i = 0; i < 35; i++) { updateCamera(); render(); }
        const move = MOVES[${JSON.stringify(moveKey)}];
        const set = POSE_SET.player[move.sheet];
        const original = set[3]; set[3] = ${enabled} ? original : null;
        P.move = move; P.moveKey = ${JSON.stringify(moveKey)};
        const split = Math.ceil(move.startup * 0.55);
        if (${JSON.stringify(label)} === 'impact') { P.state = 'active'; P.st = 0; }
        else { P.state = 'windup'; P.st = ${JSON.stringify(label)} === 'pre' ? split - 1 : split; }
        render(); set[3] = original;
      })()`);
      const shot = await browser.send('Page.captureScreenshot', { format: 'png' });
      const filename = `${gid}_${attack}_${enabled ? 'on' : 'off'}_${label}.png`;
      const path = join(output, filename);
      await writeFile(path, Buffer.from(shot.result.data, 'base64'));
      files.push(path);
    }
  }
  return files;
}

function browserProbe(gid) {
  return `
    (async () => {
      const gid = ${JSON.stringify(gid)};
      await loadGeneral(gid, 'player');
      const attackMap = {
        slash: { moveKey: 'light', setKey: 'light' },
        thrust: { moveKey: 'thrust', setKey: 'thrust' },
        heavy: { moveKey: 'heavy', setKey: 'heavy' },
      };
      const canvas = document.querySelector('canvas');
      const context = canvas.getContext('2d', { willReadFrequently: true });
      const score = (a, b) => {
        let sum = 0, changed = 0;
        for (let i = 0; i < a.length; i += 4) {
          const delta = Math.abs(a[i] - b[i]) + Math.abs(a[i + 1] - b[i + 1]) + Math.abs(a[i + 2] - b[i + 2]);
          if (delta > 18) { sum += delta; changed++; }
        }
        return changed ? sum / changed : 0;
      };
      const run = (moveKey, swing) => {
        resetMatch(); phase = 'fight'; DUMMY = 1;
        P.x = STAGE_W / 2 - 190; B.x = STAGE_W / 2 + 190; P.z = B.z = Z_MAX / 2;
        P.dir = 1; B.dir = -1; P.stam = P.maxStam;
        // Stabilize the camera before collecting attack frames.
        for (let i = 0; i < 35; i++) { updateCamera(); render(); }
        const move = MOVES[moveKey];
        const set = POSE_SET.player[move.sheet];
        const original = set[3]; set[3] = swing ? original : null;
        if (!startMove(P, moveKey)) throw new Error('Could not start ' + moveKey);
        const frames = [];
        let previous = null;
        for (let i = 0; i < 150 && (busy(P) || i < 2); i++) {
          update(); render();
          const pixels = context.getImageData(0, 0, canvas.width, canvas.height).data;
          if (previous) frames.push(score(previous, pixels));
          previous = pixels;
        }
        set[3] = original;
        return { max: Math.max(...frames), mean: frames.reduce((a, b) => a + b, 0) / frames.length, frames: frames.length };
      };
      const rows = [];
      for (const [sheet, attack] of Object.entries(attackMap)) {
        if (!POSE_SET.player[attack.setKey]?.[3]) continue;
        const withSwing = run(attack.moveKey, true);
        const withoutSwing = run(attack.moveKey, false);
        rows.push({ attack: sheet, withSwing, withoutSwing,
          maxDelta: +(withSwing.max - withoutSwing.max).toFixed(2),
          meanDelta: +(withSwing.mean - withoutSwing.mean).toFixed(2) });
      }
      return { general: gid, rows };
    })()
  `;
}

const browser = await connect();
try {
  if (capture) {
    const files = await captureReview(browser, capture);
    console.log(files.join('\n'));
  } else {
    const gids = all ? await swingGenerals() : requested;
    if (!gids.length) throw new Error('Pass a general id, or use --all.');
    const results = [];
    for (const gid of gids) results.push(await browser.evaluate(browserProbe(gid)));
    if (json) console.log(JSON.stringify(results, null, 2));
    else for (const result of results) {
      console.log(result.general);
      for (const row of result.rows) {
        console.log(`  ${row.attack.padEnd(6)} max ${row.withSwing.max.toFixed(1)} -> ${row.withoutSwing.max.toFixed(1)}  Δ ${row.maxDelta.toFixed(1)} | mean Δ ${row.meanDelta.toFixed(1)}`);
      }
    }
  }
} finally {
  browser.socket.close();
  browser.child.kill();
}
