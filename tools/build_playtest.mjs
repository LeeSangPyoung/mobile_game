// tools/build_playtest.mjs — engine.js를 인라인한 자체완결 engine_playtest.html 생성.
//   목적: 정적 서버 없이 파일 더블클릭(file://)만으로 엔진 시각확인. engine.js가 원본(단일 소스).
//   실행: node tools/build_playtest.mjs
import fs from 'fs';
import path from 'path';
import { fileURLToPath } from 'url';

const root = path.dirname(path.dirname(fileURLToPath(import.meta.url)));
// engine.js에서 export 키워드만 제거 → 클래식 스크립트로 인라인(전역 노출)
const engineSrc = fs.readFileSync(path.join(root, 'engine.js'), 'utf8').replace(/^export\s+/gm, '');

const html = `<!doctype html>
<html lang="ko">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1, maximum-scale=1">
<title>engine.js 전장 시뮬 시각확인 (Phase 0)</title>
<style>
  :root { color-scheme: dark; }
  body { margin: 0; background: #0d1117; color: #e6edf3; font: 14px/1.5 system-ui, sans-serif; }
  header { padding: 10px 14px; border-bottom: 1px solid #21262d; display: flex; gap: 10px; align-items: center; flex-wrap: wrap; }
  h1 { font-size: 15px; margin: 0; font-weight: 600; }
  button { background: #21262d; color: #e6edf3; border: 1px solid #30363d; border-radius: 6px; padding: 6px 12px; cursor: pointer; }
  button:hover { background: #30363d; }
  label { color: #8b949e; }
  input[type=number] { width: 64px; background: #0d1117; color: #e6edf3; border: 1px solid #30363d; border-radius: 4px; padding: 4px; }
  select { background:#0d1117;color:#e6edf3;border:1px solid #30363d;border-radius:4px;padding:4px; }
  #stat { margin-left: auto; color: #8b949e; font-variant-numeric: tabular-nums; }
  canvas { display: block; margin: 12px auto; background: #161b22; border: 1px solid #21262d; border-radius: 8px; }
  .note { padding: 6px 14px; color: #6e7681; font-size: 12px; }
  b.win { color: #58a6ff; }
</style>
</head>
<body>
<header>
  <h1>engine.js 전장 시뮬 — 시각 확인</h1>
  <label>seed <input id="seed" type="number" value="1234"></label>
  <label>맵 <select id="map">
    <option value="pvp">대칭 1v1 (+중립2)</option>
    <option value="ffa">1v1v1 (+중립)</option>
  </select></label>
  <button id="restart">▶ 새 전투</button>
  <button id="pause">⏸ 일시정지</button>
  <div id="stat"></div>
</header>
<canvas id="cv" width="440" height="760"></canvas>
<div class="note">
  자체완결 페이지(정적 서버 불필요 — <b>파일 더블클릭으로 열림</b>). engine.js(순수 시뮬)를 인라인해 15Hz로 step()을 돌리고 상태를 캔버스에 그립니다.
  용도: 엔진이 그럴듯한 전투(생산·출진·교전·공성·점령·승리)를 결정론적으로 굴리는지 눈으로 확인. prototype.html은 무수정.
  <br>※ engine.js 수정 후엔 <code>node tools/build_playtest.mjs</code>로 재생성.
</div>

<script>
// ===== engine.js 인라인 (tools/build_playtest.mjs가 생성 — 직접 수정 금지) =====
${engineSrc}
// ===== 시각화 =====
(function(){
  const OWNER_COLOR = { 0: '#8b949e', 1: '#58a6ff', 2: '#f85149', 3: '#3fb950', 4: '#d29922' };
  const cv = document.getElementById('cv');
  const ctx = cv.getContext('2d');
  const $ = (id) => document.getElementById(id);

  function makeMap(kind) {
    if (kind === 'ffa') {
      return { world: { w: 1.4, h: 1.4 }, aiLevel: 4, castles: [
        { x: 0.5, y: 0.12, owner: 1, name: '아군', primary: 'spear',   troops: { spear: 35, cavalry: 8, archer: 8 }, size: 1.1, trait: 'prod' },
        { x: 0.12, y: 0.85, owner: 2, name: '적1',  primary: 'cavalry', troops: { spear: 35, cavalry: 8, archer: 8 }, size: 1.1, trait: 'prod' },
        { x: 0.88, y: 0.85, owner: 3, name: '적2',  primary: 'archer',  troops: { spear: 35, cavalry: 8, archer: 8 }, size: 1.1, trait: 'prod' },
        { x: 0.5, y: 0.5,  owner: 0, name: '중립',  primary: 'spear',   troops: { spear: 6, cavalry: 6, archer: 6 }, size: 1.0, trait: 'def' },
      ]};
    }
    return { world: { w: 1, h: 1.7 }, growthMult: 1.4, aiLevel: 3, castles: [
      { x: 0.5, y: 0.10, owner: 1, name: '아군본진', primary: 'spear', troops: { spear: 40, cavalry: 10, archer: 10 }, size: 1.15, trait: 'prod' },
      { x: 0.5, y: 0.90, owner: 2, name: '적본진',   primary: 'spear', troops: { spear: 40, cavalry: 10, archer: 10 }, size: 1.15, trait: 'prod' },
      { x: 0.28, y: 0.50, owner: 0, name: '중립1',    primary: 'archer',  troops: { spear: 4, cavalry: 3, archer: 3 }, size: 0.9, trait: 'def' },
      { x: 0.72, y: 0.50, owner: 0, name: '중립2',    primary: 'cavalry', troops: { spear: 4, cavalry: 3, archer: 3 }, size: 0.9, trait: 'atk' },
    ]};
  }

  let eng, raf, paused = false, acc = 0, lastT = 0, sendTimer = 0;

  function fitScale() {
    const pad = 24;
    return { s: Math.min((cv.width - pad*2)/eng._pxW, (cv.height - pad*2)/eng._pxH), pad };
  }
  function start() {
    const kind = $('map').value;
    const seed = (parseInt($('seed').value, 10) || 1) >>> 0;
    eng = new SimEngine(makeMap(kind), seed);
    paused = false; acc = 0; lastT = performance.now(); sendTimer = 0;
    cancelAnimationFrame(raf); loop();
  }
  function playerAI(dt) {
    sendTimer -= dt; if (sendTimer > 0) return; sendTimer = 2.5;
    const mine = eng.castles.map((c, i) => ({ c, i })).filter(o => o.c.owner === 1);
    const foes = eng.castles.map((c, i) => ({ c, i })).filter(o => o.c.owner !== 1);
    if (!mine.length || !foes.length) return;
    for (const { c, i } of mine) {
      const tot = c.troops.spear + c.troops.cavalry + c.troops.archer;
      if (tot < 20) continue;
      let best = null, bd = Infinity;
      for (const f of foes) { const d = Math.hypot((c.x-f.c.x)*eng._pxW, (c.y-f.c.y)*eng._pxH); if (d < bd) { bd = d; best = f; } }
      if (!best) continue;
      const unit = ['spear','cavalry','archer'].reduce((p, u) => c.troops[u] > c.troops[p] ? u : p, 'spear');
      eng.enqueue('p1', { type: 'SEND_ARMY', fromId: i, toId: best.i, unit });
    }
  }
  function loop() {
    raf = requestAnimationFrame(loop);
    const now = performance.now();
    let dt = Math.min((now - lastT)/1000, 0.1); lastT = now;
    if (!paused && eng.winner == null) {
      acc += dt; const STEP = 1/15;
      while (acc >= STEP) { playerAI(STEP); eng.step(STEP); acc -= STEP; }
    }
    render();
  }
  function render() {
    const { s, pad } = fitScale();
    const W2X = (wx) => pad + wx*s, W2Y = (wy) => pad + wy*s;
    ctx.clearRect(0, 0, cv.width, cv.height);
    for (const c of eng.castles) {
      const x = W2X(eng._wx(c)), y = W2Y(eng._wy(c)), r = 16*(c.size||1);
      ctx.beginPath(); ctx.arc(x, y, r+4, -Math.PI/2, -Math.PI/2 + Math.PI*2*(c.wallHP/c.wallMax));
      ctx.strokeStyle = '#e6edf3'; ctx.lineWidth = 2.5; ctx.stroke();
      ctx.beginPath(); ctx.arc(x, y, r, 0, Math.PI*2);
      ctx.fillStyle = OWNER_COLOR[c.owner] || '#888'; ctx.globalAlpha = c._contested ? 0.5 : 1; ctx.fill(); ctx.globalAlpha = 1;
      const tot = c.troops.spear + c.troops.cavalry + c.troops.archer;
      ctx.fillStyle = '#0d1117'; ctx.font = 'bold 12px system-ui'; ctx.textAlign = 'center'; ctx.textBaseline = 'middle';
      ctx.fillText(tot, x, y);
    }
    for (const a of eng.armies) {
      const x = W2X(a.x), y = W2Y(a.y);
      ctx.beginPath(); ctx.arc(x, y, a.dying ? 3 : 5, 0, Math.PI*2);
      ctx.fillStyle = OWNER_COLOR[a.owner] || '#888'; ctx.globalAlpha = a.dying ? 0.4 : 1; ctx.fill(); ctx.globalAlpha = 1;
      ctx.fillStyle = '#e6edf3'; ctx.font = '9px system-ui'; ctx.fillText(a.troops, x, y - 9);
    }
    const counts = {};
    for (const c of eng.castles) counts[c.owner] = (counts[c.owner] || 0) + 1;
    let stat = 'tick ' + eng.tick + ' · 부대 ' + eng.armies.length + ' · 성 ' + Object.entries(counts).map(([o,n]) => o+':'+n).join(' ');
    $('stat').innerHTML = eng.winner != null ? '<b class="win">승자: 진영 ' + eng.winner + '</b> · ' + stat : stat;
  }
  $('restart').onclick = start;
  $('pause').onclick = () => { paused = !paused; $('pause').textContent = paused ? '▶ 재개' : '⏸ 일시정지'; if (!paused) lastT = performance.now(); };
  start();
})();
</script>
</body>
</html>
`;

fs.writeFileSync(path.join(root, 'engine_playtest.html'), html);
console.log('생성 완료: engine_playtest.html (자체완결, ' + Math.round(html.length/1024) + 'KB)');
