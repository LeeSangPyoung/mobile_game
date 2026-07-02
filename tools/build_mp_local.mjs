// tools/build_mp_local.mjs — engine.js 위에 로컬 1v1 대전(You vs AI)을 얹은 자체완결 페이지 생성.
//   목적: 검증된 순수 엔진이 '실제 대전 플레이'(입력·대칭맵·본진함락 승패)를 지지하는지 로컬 확인.
//         네트워킹(Firebase/WebRTC) 얹기 전 대전 흐름 검증. engine.js가 단일 소스(인라인).
//   실행: node tools/build_mp_local.mjs  → mp_local.html (파일 더블클릭 실행)
import fs from 'fs';
import path from 'path';
import { fileURLToPath } from 'url';

const root = path.dirname(path.dirname(fileURLToPath(import.meta.url)));
const engineSrc = fs.readFileSync(path.join(root, 'engine.js'), 'utf8').replace(/^export\s+/gm, '');

const html = `<!doctype html>
<html lang="ko">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1, maximum-scale=1, user-scalable=no">
<title>손가락삼국지 — 로컬 1v1 대전 (engine.js)</title>
<style>
  :root { color-scheme: dark; }
  * { box-sizing: border-box; }
  html, body { margin: 0; height: 100%; background: #0b0f16; color: #e6edf3; font: 14px/1.4 system-ui, sans-serif; overscroll-behavior: none; }
  #wrap { display: flex; flex-direction: column; height: 100%; }
  header { padding: 8px 12px; border-bottom: 1px solid #1c2430; display: flex; gap: 8px; align-items: center; flex-wrap: wrap; }
  h1 { font-size: 14px; margin: 0; font-weight: 700; }
  .spacer { flex: 1; }
  button { background: #1c2430; color: #e6edf3; border: 1px solid #2b3543; border-radius: 6px; padding: 6px 10px; cursor: pointer; font-size: 13px; }
  button:hover { background: #263041; }
  label { color: #8b949e; font-size: 12px; }
  input[type=number] { width: 60px; background: #0b0f16; color: #e6edf3; border: 1px solid #2b3543; border-radius: 4px; padding: 4px; }
  #hud { display: flex; gap: 14px; padding: 6px 12px; font-variant-numeric: tabular-nums; border-bottom: 1px solid #1c2430; }
  .me { color: #58a6ff; } .ai { color: #f85149; }
  #stage { position: relative; flex: 1; display: flex; align-items: center; justify-content: center; touch-action: none; }
  canvas { background: radial-gradient(circle at 50% 50%, #14203a 0%, #0b0f16 80%); border: 1px solid #1c2430; border-radius: 10px; touch-action: none; }
  #banner { position: absolute; inset: 0; display: none; align-items: center; justify-content: center; flex-direction: column; gap: 12px; background: rgba(5,8,13,.72); backdrop-filter: blur(2px); }
  #banner h2 { font-size: 40px; margin: 0; }
  #tip { padding: 6px 12px; color: #6e7681; font-size: 12px; border-top: 1px solid #1c2430; }
</style>
</head>
<body>
<div id="wrap">
  <header>
    <h1>⚔ 로컬 1v1 대전 <span style="color:#6e7681;font-weight:400">engine.js</span></h1>
    <div class="spacer"></div>
    <label>AI <select id="ai" style="background:#0b0f16;color:#e6edf3;border:1px solid #2b3543;border-radius:4px;padding:4px">
      <option value="2">쉬움</option><option value="3" selected>보통</option><option value="4">어려움</option><option value="5">최상</option>
    </select></label>
    <label>seed <input id="seed" type="number" value="777"></label>
    <button id="restart">▶ 새 대전</button>
  </header>
  <div id="hud">
    <div class="me">🔵 아군 성 <b id="meC">0</b> · 병력 <b id="meT">0</b></div>
    <div class="ai">🔴 적 성 <b id="aiC">0</b> · 병력 <b id="aiT">0</b></div>
    <div class="spacer" style="flex:1"></div>
    <div style="color:#8b949e">tick <b id="tk">0</b></div>
  </div>
  <div id="stage">
    <canvas id="cv" width="420" height="720"></canvas>
    <div id="banner"><h2 id="bwin"></h2><button id="again">다시</button></div>
  </div>
  <div id="tip">내 성(파랑) 탭 → 목표 성 탭 = 전 병력 출진. 적 본진(★) 함락 시 승리. AI는 engine.js 내장 AI가 조종.</div>
</div>

<script>
// ===== engine.js 인라인 (tools/build_mp_local.mjs 생성 — 직접 수정 금지) =====
${engineSrc}
// ===== 로컬 대전 게임 =====
(function(){
  const C = { 0:'#8b949e', 1:'#58a6ff', 2:'#f85149' };
  const UNIT_C = { spear:'#9fb0c4', cavalry:'#e0a54a', archer:'#5fb86a' };
  const cv = document.getElementById('cv'), ctx = cv.getContext('2d');
  const $ = (id) => document.getElementById(id);

  // 점대칭 대전맵: 본진 2 + 중립 대칭 배치 (위치 유불리 없음)
  function makeMap() {
    const home = (x,y,owner,name) => ({ x, y, owner, name, isHome:true, primary:'spear',
      troops:{ spear:30, cavalry:8, archer:8 }, size:1.25, trait:'prod' });
    const neu = (x,y,trait,primary) => ({ x, y, owner:0, name:'', primary,
      troops:{ spear:5, cavalry:4, archer:4 }, size:0.95, trait });
    return { world:{ w:1, h:1.7 }, aiLevel: parseInt($('ai').value,10)||3, growthMult:1.0, castles: [
      home(0.5, 0.90, 1, '아군본진'),
      home(0.5, 0.10, 2, '적본진'),
      neu(0.5, 0.50, 'def', 'archer'),          // 중앙 요충 (자기대칭)
      neu(0.24, 0.66, 'atk', 'cavalry'), neu(0.76, 0.34, 'atk', 'cavalry'), // 대칭쌍
      neu(0.76, 0.66, 'prod', 'spear'), neu(0.24, 0.34, 'prod', 'spear'),   // 대칭쌍
    ]};
  }

  let eng, raf, acc = 0, lastT = 0, selected = -1, over = false;

  function fitScale() {
    const pad = 30;
    return { s: Math.min((cv.width-pad*2)/eng._pxW, (cv.height-pad*2)/eng._pxH), pad };
  }
  const SX = (wx) => { const {s,pad}=fitScale(); return pad + wx*s; };
  const SY = (wy) => { const {s,pad}=fitScale(); return pad + wy*s; };

  function start() {
    const seed = (parseInt($('seed').value,10)||1) >>> 0;
    eng = new SimEngine(makeMap(), seed);
    acc = 0; lastT = performance.now(); selected = -1; over = false;
    $('banner').style.display = 'none';
    cancelAnimationFrame(raf); loop();
  }

  function castleAt(px, py) {
    let best = -1, bd = 26;
    eng.castles.forEach((c,i) => {
      const d = Math.hypot(px - SX(eng._wx(c)), py - SY(eng._wy(c)));
      if (d < bd) { bd = d; best = i; }
    });
    return best;
  }

  function onTap(e) {
    if (over) return;
    const r = cv.getBoundingClientRect();
    const px = (e.clientX - r.left) * (cv.width / r.width);
    const py = (e.clientY - r.top) * (cv.height / r.height);
    const hit = castleAt(px, py);
    if (hit < 0) { selected = -1; return; }
    const c = eng.castles[hit];
    if (selected < 0) {
      if (c.owner === 1) selected = hit;         // 내 성 선택
    } else if (hit === selected) {
      selected = -1;                             // 취소
    } else {
      // 전 병력 출진 (병종별 1부대)
      for (const u of ['spear','cavalry','archer']) {
        if ((eng.castles[selected].troops[u]|0) > 0)
          eng.enqueue('me', { type:'SEND_ARMY', fromId: selected, toId: hit, unit: u });
      }
      selected = -1;
    }
  }
  cv.addEventListener('pointerdown', onTap);

  function loop() {
    raf = requestAnimationFrame(loop);
    const now = performance.now();
    let dt = Math.min((now-lastT)/1000, 0.1); lastT = now;
    if (!over) {
      acc += dt; const STEP = 1/15;
      while (acc >= STEP) { eng.step(STEP); acc -= STEP; if (eng.winner != null) break; }
      if (eng.winner != null) endMatch();
    }
    render();
  }

  function endMatch() {
    over = true;
    $('bwin').textContent = eng.winner === 1 ? '🏆 승리!' : '💀 패배…';
    $('bwin').style.color = eng.winner === 1 ? '#58a6ff' : '#f85149';
    $('banner').style.display = 'flex';
  }

  function render() {
    ctx.clearRect(0,0,cv.width,cv.height);
    // 부대 (성 아래 레이어)
    for (const a of eng.armies) {
      const x = SX(a.x), y = SY(a.y);
      ctx.beginPath(); ctx.arc(x, y, a.dying?3:5.5, 0, Math.PI*2);
      ctx.fillStyle = C[a.owner]||'#888'; ctx.globalAlpha = a.dying?0.35:1; ctx.fill();
      ctx.strokeStyle = UNIT_C[a.unit]||'#fff'; ctx.lineWidth = 1.6; ctx.stroke(); ctx.globalAlpha = 1;
      ctx.fillStyle = '#dfe7f0'; ctx.font = '9px system-ui'; ctx.textAlign='center'; ctx.textBaseline='middle';
      ctx.fillText(a.troops, x, y-10);
    }
    // 성
    eng.castles.forEach((c,i) => {
      const x = SX(eng._wx(c)), y = SY(eng._wy(c)), r = 15*(c.size||1);
      if (i === selected) { ctx.beginPath(); ctx.arc(x,y,r+9,0,Math.PI*2); ctx.strokeStyle='#ffd24a'; ctx.lineWidth=2.5; ctx.stroke(); }
      // 성벽 링
      ctx.beginPath(); ctx.arc(x, y, r+4, -Math.PI/2, -Math.PI/2 + Math.PI*2*Math.max(0,c.wallHP/c.wallMax));
      ctx.strokeStyle = c._contested ? '#e3b341' : '#c9d4e0'; ctx.lineWidth = 2.5; ctx.stroke();
      // 본체
      ctx.beginPath(); ctx.arc(x, y, r, 0, Math.PI*2);
      ctx.fillStyle = C[c.owner]||'#888'; ctx.fill();
      // 병력수
      const tot = c.troops.spear+c.troops.cavalry+c.troops.archer;
      ctx.fillStyle = c.owner===0 ? '#0b0f16' : '#0b0f16'; ctx.font = 'bold 12px system-ui';
      ctx.textAlign='center'; ctx.textBaseline='middle'; ctx.fillText(tot, x, y);
      // 본진 ★
      if (c.isHome) { ctx.fillStyle = '#ffd24a'; ctx.font = '13px system-ui'; ctx.fillText('★', x, y - r - 9); }
    });
    // HUD
    const me = eng.castles.filter(c=>c.owner===1), ai = eng.castles.filter(c=>c.owner===2);
    const sum = (arr) => arr.reduce((s,c)=>s+c.troops.spear+c.troops.cavalry+c.troops.archer,0)
      + eng.armies.filter(a=>arr===me?a.owner===1:a.owner===2).reduce((s,a)=>s+a.troops,0);
    $('meC').textContent = me.length; $('meT').textContent = sum(me);
    $('aiC').textContent = ai.length; $('aiT').textContent = sum(ai);
    $('tk').textContent = eng.tick;
  }

  $('restart').onclick = start;
  $('again').onclick = start;
  $('ai').onchange = start;
  start();
})();
</script>
</body>
</html>
`;
fs.writeFileSync(path.join(root, 'mp_local.html'), html);
console.log('생성 완료: mp_local.html (자체완결, ' + Math.round(html.length/1024) + 'KB)');
