// tools/build_mp_server_client.mjs — 중계서버(mp_server.js)에 붙는 실그림 1v1 클라이언트 생성.
//   engine.js + netmatch.js 인라인. 전송=WebSocket(서버 중계). 닉네임 등록 + 전적 표시 + 서버 매칭.
//   출력: server/public/mp_game.html, server/public/mp_game_2view.html + 필요한 자산 복사.
//   실행: node tools/build_mp_server_client.mjs
import fs from 'fs';
import path from 'path';
import { fileURLToPath } from 'url';

const root = path.dirname(path.dirname(fileURLToPath(import.meta.url)));
const engineSrc = fs.readFileSync(path.join(root, 'engine.js'), 'utf8').replace(/^export\s+/gm, '');
const netSrc = fs.readFileSync(path.join(root, 'netmatch.js'), 'utf8').replace(/^import[^\n]*\n/gm, '').replace(/^export\s+/gm, '');
const metaSrc = fs.readFileSync(path.join(root, 'meta.js'), 'utf8').replace(/^import[^\n]*\n/gm, '').replace(/^export\s+/gm, '');
const pub = path.join(root, 'server', 'public');

// 필요한 자산만 복사(용량 최소)
function copy(rel) { const src = path.join(root, rel), dst = path.join(pub, rel); fs.mkdirSync(path.dirname(dst), { recursive: true }); fs.copyFileSync(src, dst); }
fs.mkdirSync(pub, { recursive: true });
['assets/battle/bg_battle_02_snow.jpg', 'assets/battle/intro_duel_bg_cityfire.png', 'assets/result/result_victory_bg.png', 'assets/result/result_defeat_burning_city.png', 'assets/castles/castle_ally.png', 'assets/castles/castle_enemy.png', 'assets/castles/castle_neutral.png',
  'assets/generals/roster_200.js'].forEach(copy);

const html = `<!doctype html>
<html lang="ko">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1, maximum-scale=1, user-scalable=no">
<title>손가락삼국지 — 실시간 1v1</title>
<style>
  :root { color-scheme: dark; } * { box-sizing: border-box; }
  html,body { margin:0; height:100%; background:#07090d; color:#f4ead8; font:14px/1.4 'Noto Sans KR',system-ui,sans-serif; overscroll-behavior:none; -webkit-user-select:none; user-select:none; }
  #wrap { display:flex; flex-direction:column; height:100%; }
  #hud { display:none; gap:14px; padding:7px 12px; align-items:center; border-bottom:1px solid #1c2430; font-variant-numeric:tabular-nums; }
  .me { color:#58a6ff; font-weight:700; } .en { color:#f85149; font-weight:700; }
  #hud .sp { flex:1; }
  #stage { position:relative; flex:1; display:flex; align-items:center; justify-content:center; touch-action:none; overflow:hidden; }
  canvas { display:block; touch-action:none; }
  .panel { position:absolute; inset:0; display:flex; align-items:center; justify-content:center; flex-direction:column; gap:16px; background:radial-gradient(circle at 50% 30%,rgba(20,32,58,.6),rgba(5,8,13,.94)); z-index:10; text-align:center; padding:20px; }
  .panel.lobby-panel,
  .panel.nick-panel,
  .panel.rank-panel {
    justify-content:flex-start;
    gap:0;
    padding:54px 10px 12px;
    background:
      linear-gradient(180deg, rgba(3,8,14,.66) 0%, rgba(5,9,15,.7) 44%, rgba(3,6,10,.84) 100%),
      radial-gradient(circle at 50% 0%, rgba(58,77,105,.34), transparent 40%),
      url('assets/battle/intro_duel_bg_cityfire.png') center / cover no-repeat,
      linear-gradient(180deg, #08111d 0%, #050a12 100%);
  }
  .panel.lobby-panel::before,
  .panel.nick-panel::before,
  .panel.rank-panel::before {
    content:"";
    position:absolute;
    inset:0;
    pointer-events:none;
    background:
      linear-gradient(90deg, rgba(0,0,0,.22), transparent 14%, transparent 86%, rgba(0,0,0,.22)),
      radial-gradient(circle at 50% 50%, transparent 42%, rgba(0,0,0,.26) 100%);
  }
  .lobby-shell,
  .nick-shell,
  .rank-shell {
    position:relative;
    width:min(620px, calc(100vw - 18px));
    color:#f8ead1;
    text-align:center;
  }
  .lobby-shell {
    display:grid;
    gap:10px;
    padding:12px;
    border:2px solid #d2a128;
    border-radius:18px;
    background:
      linear-gradient(180deg, rgba(19,31,47,.98), rgba(8,15,26,.99));
    box-shadow:0 0 0 1px rgba(0,0,0,.75), 0 18px 38px rgba(0,0,0,.62), inset 0 1px 0 rgba(255,255,255,.06);
  }
  .lobby-top {
    display:grid;
    grid-template-columns: minmax(0,1fr);
    gap:5px;
    justify-items:center;
    padding:10px 12px 12px;
    border:1px solid rgba(212,161,40,.58);
    border-radius:12px;
    background:linear-gradient(180deg, #1e2d42 0%, #101a29 58%, #0a111d 100%);
    box-shadow:inset 0 1px 0 rgba(255,255,255,.1);
  }
  .lobby-kicker {
    display:inline-grid;
    place-items:center;
    min-width:138px;
    height:30px;
    border:1px solid #8e6b1c;
    border-radius:9px;
    color:#2b1604;
    background:linear-gradient(180deg,#fff1a8 0%,#f2b736 48%,#d48b13 100%);
    font:800 12px/1 'Noto Serif KR',serif;
    letter-spacing:2px;
    box-shadow:0 3px 0 #7b4f0f, inset 0 1px 0 rgba(255,255,255,.65);
  }
  .lobby-title {
    font:900 27px/1.05 'Noto Serif KR',serif;
    letter-spacing:3px;
    color:#fff0bd;
    text-shadow:0 2px 0 #111927, 0 0 10px rgba(242,183,54,.22);
  }
  .lobby-sub { color:#d6deea; font:800 12px/1.3 'Noto Serif KR',serif; letter-spacing:.2px; }
  .record-strip {
    display:grid;
    grid-template-columns:repeat(5, 1fr);
    gap:0;
    padding:8px 4px;
    border:1px solid rgba(151,119,43,.6);
    border-radius:10px;
    background:#070d16;
    box-shadow:inset 0 1px 0 rgba(255,255,255,.05);
  }
  .record-cell { min-width:0; }
  .record-cell b { display:block; font:900 19px/1 'Noto Serif KR',serif; color:#fff0bd; }
  .record-cell span { display:block; margin-top:4px; color:#c7cfda; font-size:10px; font-weight:900; letter-spacing:1px; }
  .war-board {
    display:grid;
    gap:11px;
    padding:14px;
    border:1px solid rgba(212,161,40,.64);
    border-radius:12px;
    background:linear-gradient(180deg, #142235 0%, #0c1523 100%);
    box-shadow:inset 0 1px 0 rgba(255,255,255,.07);
  }
  .war-board-head { display:flex; align-items:center; justify-content:space-between; gap:10px; }
  .war-board-head strong { font:900 18px/1 'Noto Serif KR',serif; letter-spacing:1px; color:#fff0bd; }
  .live-pill {
    position:relative;
    padding:6px 9px 6px 20px;
    border:1px solid #ff5148;
    color:#fff4f1;
    background:linear-gradient(180deg,#d7362f 0%,#8e1f1e 58%,#4a1012 100%);
    font:900 10px/1 monospace;
    letter-spacing:1px;
    text-shadow:0 1px 0 rgba(0,0,0,.55);
    box-shadow:0 0 0 1px rgba(70,0,0,.7), 0 0 12px rgba(255,48,38,.52), inset 0 1px 0 rgba(255,255,255,.22);
  }
  .live-pill::before {
    content:"";
    position:absolute;
    left:8px;
    top:50%;
    width:7px;
    height:7px;
    border-radius:50%;
    background:#ff2d25;
    transform:translateY(-50%);
    box-shadow:0 0 8px #ff4b43;
    animation:liveBlink 1.1s ease-in-out infinite;
  }
  .loadout-grid { display:grid; grid-template-columns:1fr 1fr; gap:8px; }
  .loadout-stat {
    padding:11px 10px;
    border:1px solid rgba(72,91,116,.9);
    border-radius:0;
    background:#08101b;
    text-align:left;
  }
  .loadout-stat span { display:block; color:#aeb7c3; font-size:11px; font-weight:900; letter-spacing:.3px; }
  .loadout-stat b { display:block; margin-top:5px; color:#ffd451; font:900 23px/1 'Noto Serif KR',serif; white-space:nowrap; }
  .loadout-stat b em { font:inherit; font-style:normal; color:inherit; }
  .lobby-note { margin:0; color:#c2cbd7; font-size:12px; line-height:1.45; text-align:left; }
  .find-main {
    width:100%;
    min-height:58px;
    display:grid;
    place-items:center;
    gap:4px;
    margin-top:2px;
    padding:12px 18px;
    border-radius:10px;
    font-family:'Noto Serif KR',serif;
    background:radial-gradient(circle at 50% 0%, rgba(255,255,255,.58), transparent 34%), linear-gradient(180deg,#fff0a6 0%,#f2b534 52%,#d88e13 100%);
    border-color:#8b6119;
    box-shadow:0 4px 0 #7c4f0e, inset 0 1px 0 rgba(255,255,255,.6);
  }
  .find-main span { font-size:21px; font-weight:900; letter-spacing:4px; }
  .find-main em { font-style:normal; font-size:11px; font-weight:900; letter-spacing:1px; color:rgba(50,21,5,.76); }
  .find-row { display:flex; gap:8px; margin-top:2px; }
  .find-row .find-main { flex:1; min-height:58px; margin-top:0; }
  .find-row .find-main span { font-size:18px; letter-spacing:2px; }
  .find-random {
    background:radial-gradient(circle at 50% 0%, rgba(255,255,255,.4), transparent 34%), linear-gradient(180deg,#6ba4f0 0%,#3f74c6 52%,#274f96 100%);
    border-color:#254a7f;
    box-shadow:0 3px 0 #1b3a68, inset 0 1px 0 rgba(255,255,255,.28);
    color:#f2f7ff;
  }
  .find-random span { color:#ffffff; }
  .find-random em { color:rgba(255,255,255,.82); }
  .queue-msg {
    width:100%;
    padding:13px 14px;
    border:1px solid rgba(212,161,40,.62);
    border-radius:10px;
    background:#111b2a;
    color:#cbffd2;
    font-weight:900;
  }
  .queue-dot {
    display:inline-block;
    width:8px;
    height:8px;
    margin-right:7px;
    border-radius:50%;
    background:#5fe876;
    box-shadow:0 0 12px #5fe876;
    animation:queuePulse 1s ease-in-out infinite;
  }
  .lobby-actions { display:flex; gap:9px; }
  .ghost-btn {
    width:100%;
    padding:13px 14px;
    border-radius:10px;
    background:linear-gradient(180deg,#263447 0%,#172231 100%);
    color:#f1f5fb;
    border:1px solid #4b5b70;
    box-shadow:0 3px 0 rgba(0,0,0,.38), inset 0 1px 0 rgba(255,255,255,.08);
    font-size:15px;
  }
  .rank-btn {
    position:relative;
    color:#fff2c2;
    border-color:#d2a128;
    background:
      radial-gradient(circle at 20% 0%, rgba(255,244,184,.22), transparent 36%),
      linear-gradient(180deg,#2d4260 0%,#1b2c47 56%,#111d31 100%);
    box-shadow:0 3px 0 #53370d, 0 0 12px rgba(210,161,40,.18), inset 0 1px 0 rgba(255,255,255,.14);
    text-shadow:0 1px 0 rgba(0,0,0,.65);
  }
  .rank-btn::before {
    content:"♛";
    display:inline-block;
    margin-right:7px;
    color:#ffd85b;
    font-size:16px;
    line-height:1;
    vertical-align:-1px;
    text-shadow:0 1px 0 #4c2e06, 0 0 8px rgba(255,216,91,.35);
  }
  .nick-shell {
    padding:22px 18px 18px;
    border:1px solid rgba(255,211,122,.56);
    border-radius:8px;
    background:linear-gradient(180deg, rgba(39,27,19,.94), rgba(11,15,22,.97));
    box-shadow:0 0 0 2px rgba(36,16,6,.88), 0 24px 60px rgba(0,0,0,.68);
  }
  .nick-shell h1,
  .rank-shell h1 { margin-bottom:9px; }
  .rank-shell {
    display:grid;
    gap:10px;
    padding:12px;
    border:2px solid #d2a128;
    border-radius:18px;
    background:linear-gradient(180deg, rgba(19,31,47,.98), rgba(8,15,26,.99));
    box-shadow:0 0 0 1px rgba(0,0,0,.75), 0 18px 38px rgba(0,0,0,.62), inset 0 1px 0 rgba(255,255,255,.06);
  }
  .rank-head {
    display:grid;
    gap:5px;
    justify-items:center;
    padding:10px 12px 12px;
    border:1px solid rgba(212,161,40,.58);
    border-radius:12px;
    background:linear-gradient(180deg, #1e2d42 0%, #101a29 58%, #0a111d 100%);
    box-shadow:inset 0 1px 0 rgba(255,255,255,.1);
  }
  @keyframes queuePulse { 0%,100%{transform:scale(.8);opacity:.55} 50%{transform:scale(1.18);opacity:1} }
  @keyframes liveBlink { 0%,100%{opacity:.45} 50%{opacity:1} }
  h1 { font:900 26px 'Noto Serif KR',serif; color:#fff1b8; margin:0; text-shadow:0 2px 0 rgba(0,0,0,.6); }
  input { background:#0b0f16; color:#e6edf3; border:2px solid #2b3543; border-radius:10px; padding:12px 14px; font-size:18px; text-align:center; width:220px; }
  button { background:linear-gradient(180deg,#f2b536,#d58716); color:#2a1206; border:2px solid #8a5a13; border-radius:12px; padding:14px 28px; font:800 18px 'Noto Serif KR',serif; cursor:pointer; box-shadow:0 4px 0 #7a4e12; }
  button:active { transform:translateY(2px); box-shadow:0 2px 0 #7a4e12; }
  button:disabled { opacity:.5; }
  .muted { color:#8b949e; font-size:13px; }
  .err { color:#ff8080; font-size:13px; min-height:18px; }
  .stat { color:#cbd5e1; font-size:15px; }
  #banner {
    overflow:hidden;
    padding:22px;
    background:#05070b;
  }
  #banner::before {
    content:"";
    position:absolute;
    inset:0;
    background:
      linear-gradient(180deg, rgba(0,0,0,.06), rgba(0,0,0,.08) 38%, rgba(0,0,0,.38) 100%),
      var(--result-bg, none) center / cover no-repeat;
    filter:saturate(1.12) brightness(1.16);
    transform:scale(1.01);
  }
  #banner::after {
    content:"";
    position:absolute;
    inset:0;
    pointer-events:none;
    background:
      radial-gradient(circle at 50% 22%, rgba(255,220,127,.12), transparent 34%),
      linear-gradient(90deg, rgba(0,0,0,.24), transparent 18%, transparent 82%, rgba(0,0,0,.24));
  }
  #banner.is-win { --result-bg:url('assets/result/result_victory_bg.png'); --result-accent:#f4c13a; --result-title:#ffe9a6; }
  #banner.is-loss { --result-bg:url('assets/result/result_defeat_burning_city.png'); --result-accent:#d44638; --result-title:#ffb1ac; }
  .result-card {
    position:relative;
    z-index:1;
    width:min(560px, calc(100vw - 36px));
    margin-top:min(7vh, 62px);
    padding:22px 18px 18px;
    border:2px solid var(--result-accent);
    border-radius:18px;
    background:linear-gradient(180deg, rgba(17,29,45,.78), rgba(5,9,15,.86));
    box-shadow:0 0 0 1px rgba(0,0,0,.72), 0 22px 46px rgba(0,0,0,.56), inset 0 1px 0 rgba(255,255,255,.09);
  }
  .result-kicker {
    display:inline-flex;
    align-items:center;
    justify-content:center;
    min-width:128px;
    height:32px;
    padding:0 18px;
    border-radius:8px;
    background:linear-gradient(180deg,#ffe78b,#d28b16);
    color:#351705;
    border:1px solid rgba(99,54,9,.8);
    box-shadow:0 3px 0 rgba(101,58,8,.85), inset 0 1px 0 rgba(255,255,255,.52);
    font:900 15px 'Noto Serif KR',serif;
  }
  #banner h2 {
    font:900 clamp(42px, 12vw, 74px)/1 'Noto Serif KR',serif;
    margin:14px 0 8px;
    color:var(--result-title);
    text-shadow:0 3px 0 rgba(0,0,0,.65), 0 0 18px color-mix(in srgb, var(--result-accent) 62%, transparent);
    letter-spacing:0;
  }
  .result-sub {
    color:#fff2c8;
    font-weight:900;
    text-shadow:0 2px 0 rgba(0,0,0,.52);
    margin-bottom:7px;
  }
  #banner .stat {
    color:#cfd8e3;
    font-size:14px;
    margin-bottom:14px;
  }
  #again {
    min-width:112px;
    border-radius:10px;
  }
  #tip { display:none; padding:6px 12px; color:#6e7681; font-size:12px; border-top:1px solid #1c2430; }
  #conn { display:none !important; }
  #backMain { position:fixed; left:10px; top:10px; z-index:30; display:none; padding:8px 12px; border-radius:8px; background:rgba(4,8,12,.62); border:1px solid rgba(255,211,122,.28); color:#f3e1bb; font-size:13px; font-weight:900; cursor:pointer; }
  .myrank { width:100%; background:linear-gradient(180deg,#203654,#18283f); border:1px solid #42638f; border-radius:12px; padding:12px 14px; display:flex; align-items:center; gap:12px; box-shadow:inset 0 1px 0 rgba(255,255,255,.08); }
  .myrank .rk { font-size:26px; font-weight:900; color:#9dc4ff; min-width:64px; text-align:center; font-family:'Noto Serif KR',serif; }
  .myrank .info { text-align:left; flex:1; min-width:0; } .myrank .info .nm { font-weight:900; font-size:16px; overflow:hidden; text-overflow:ellipsis; color:#f4ead8; } .myrank .info .sub { color:#aeb7c3; font-size:12px; margin-top:3px; }
  .myrank .pt { font-size:22px; font-weight:900; color:#48d869; white-space:nowrap; font-family:'Noto Serif KR',serif; }
  .ranklist { width:100%; max-height:min(48vh, 410px); overflow:auto; border:1px solid #3b4d66; border-radius:12px; background:#080e17; }
  .ranklist table { width:100%; border-collapse:collapse; font-size:13px; font-variant-numeric:tabular-nums; }
  .ranklist th { position:sticky; top:0; background:#121c2a; color:#aeb7c3; font-size:11px; font-weight:900; padding:9px 10px; text-align:left; z-index:1; }
  .ranklist td { padding:10px; border-top:1px solid #1b2636; text-align:left; color:#eee6d7; font-weight:800; }
  .ranklist td.n, .ranklist th.n { text-align:right; }
  .ranklist tr.me td { background:#1a2b47; color:#dbe8ff; font-weight:900; }
  .ranklist .rk { color:#7d8998; width:52px; text-align:center; vertical-align:middle; }
  .rank-mark {
    position:relative;
    display:inline-grid;
    place-items:center;
    width:34px;
    height:30px;
    font:900 13px/1 'Noto Serif KR',serif;
    color:#9aa6b7;
    margin:0 auto;
  }
  .rank-mark.top {
    color:#271204;
    text-shadow:0 1px 0 rgba(255,255,255,.45);
  }
  .rank-mark.top::before {
    content:"";
    position:absolute;
    inset:2px 4px 3px;
    clip-path:polygon(50% 0, 91% 14%, 100% 46%, 82% 83%, 50% 100%, 18% 83%, 0 46%, 9% 14%);
    background:linear-gradient(180deg,#fff3a6,#d99b18 56%,#8e4c0a);
    box-shadow:0 2px 0 rgba(0,0,0,.38), inset 0 1px 0 rgba(255,255,255,.65), inset 0 -5px 9px rgba(0,0,0,.18);
  }
  .rank-mark.top::after {
    content:"";
    position:absolute;
    inset:7px 9px 10px;
    clip-path:polygon(50% 0, 61% 35%, 100% 35%, 69% 57%, 80% 100%, 50% 73%, 20% 100%, 31% 57%, 0 35%, 39% 35%);
    background:rgba(255,255,255,.38);
    mix-blend-mode:screen;
  }
  .rank-mark span { position:relative; z-index:1; }
  .rank-mark.r1::before { background:linear-gradient(180deg,#fff6b9 0%,#f4c13a 52%,#a6610d 100%); }
  .rank-mark.r2::before { background:linear-gradient(180deg,#f6f9ff 0%,#b3c5db 52%,#5d7088 100%); }
  .rank-mark.r3::before { background:linear-gradient(180deg,#ffd8a6 0%,#cb7a35 52%,#743817 100%); }
  .ranklist .empty { padding:20px; text-align:center; color:#6e7681; }
</style>
</head>
<body>
<div id="wrap">
  <div id="hud">
    <span class="me">🔵 아군 <b id="meC">-</b>성 <b id="meT">-</b></span>
    <span class="en">🔴 적 <b id="enC">-</b>성 <b id="enT">-</b></span>
    <span class="sp"></span>
    <span style="color:#8b949e">⏱ <b id="tk">0</b></span>
    <button id="surr" style="padding:5px 12px;font-size:13px;box-shadow:none;border-radius:8px">항복</button>
  </div>
  <div id="stage">
    <canvas id="cv"></canvas>
    <!-- 닉네임 -->
    <div class="panel nick-panel" id="pNick" style="display:none">
      <div class="nick-shell">
        <div class="lobby-kicker">실시간 멀티대전</div>
        <h1>군주 등록</h1>
        <div class="muted">전장에 남길 군주명을 정하십시오</div>
        <input id="nick" maxlength="16" placeholder="닉네임" autocomplete="off">
        <div class="err" id="nickErr"></div>
        <button id="regBtn" class="find-main"><span>입장</span><em>전장 로비로 이동</em></button>
      </div>
    </div>
    <!-- 로비 -->
    <div class="panel lobby-panel" id="pLobby" style="display:none">
      <div class="lobby-shell">
        <div class="lobby-top">
          <div class="lobby-kicker">실시간 멀티대전</div>
          <div class="lobby-title" id="hello">군주</div>
          <div class="lobby-sub">같은 전투력대의 상대와 1 대 1로 겨룹니다</div>
        </div>
        <div class="record-strip" aria-label="전적">
          <div class="record-cell"><b id="wins">0</b><span>승</span></div>
          <div class="record-cell"><b id="draws">0</b><span>무</span></div>
          <div class="record-cell"><b id="losses">0</b><span>패</span></div>
          <div class="record-cell"><b id="pts">0</b><span>점수</span></div>
          <div class="record-cell"><b id="lobbyRank">-</b><span>랭킹</span></div>
        </div>
        <div class="war-board">
          <div class="war-board-head">
            <strong>출전 전력</strong>
            <span class="live-pill">LIVE 1V1</span>
          </div>
          <div class="loadout-grid">
            <div class="loadout-stat"><span>전투력</span><b id="power">1000</b></div>
            <div class="loadout-stat"><span>출전 장수</span><b><em id="squad">0</em>명</b></div>
          </div>
          <p class="lobby-note" id="squadHint">본편에서 편성한 장수와 강화 수치가 실시간 대전에 반영됩니다.</p>
        </div>
        <div class="find-row" id="findRow">
          <button id="findBtn" class="find-main"><span>전투력 매칭</span><em>전투력 기반 매칭</em></button>
          <button id="findRandomBtn" class="find-main find-random"><span>랜덤 매칭</span><em>매칭 확률 높음</em></button>
        </div>
        <div class="queue-msg" id="findMsg" style="display:none"><span class="queue-dot"></span>상대 군주를 찾는 중</div>
        <div class="lobby-actions">
          <button id="cancelBtn" class="ghost-btn" style="display:none">매칭 취소</button>
          <button id="rankBtn" class="ghost-btn rank-btn">랭킹</button>
          <button id="lobbyBackBtn" class="ghost-btn">뒤로가기</button>
        </div>
      </div>
    </div>
    <!-- 랭킹 -->
    <div class="panel rank-panel" id="pRank" style="display:none">
      <div class="rank-shell">
        <div class="rank-head">
          <div class="lobby-kicker">명예의 전장</div>
          <h1 style="font-size:25px">랭킹</h1>
          <div class="muted">승 3점 · 무 1점 · 패 0점</div>
        </div>
        <div id="myRank" class="myrank"></div>
        <div id="rankList" class="ranklist"></div>
        <button id="rankBack" class="ghost-btn">돌아가기</button>
      </div>
    </div>
    <!-- 결과 -->
    <div class="panel result-panel" id="banner" style="display:none">
      <div class="result-card">
        <div class="result-kicker" id="bkicker">결과</div>
        <h2 id="bwin"></h2>
        <div class="result-sub" id="bsub"></div>
        <div class="stat" id="bstat"></div>
        <button id="again">로비로</button>
      </div>
    </div>
  </div>
  <div id="tip">내 성(파랑) 탭 → 목표 성 탭 = 전 병력 출진. 상대 본진(★) 함락 시 승리.</div>
</div>
<div id="backMain" onclick="location.href='index.html'">← 메인</div>
<div id="conn">연결 중…</div>

<script src="./assets/generals/roster_200.js"></script>
<script>
// ===== engine.js =====
${engineSrc}
// ===== netmatch.js =====
${netSrc}
// ===== meta.js (장수 로드아웃·전투력) =====
${metaSrc}
// ===== 서버 클라이언트 =====
(function(){
  var $=function(id){return document.getElementById(id);};
  var cv=$('cv'), ctx=cv.getContext('2d');
  var IMG={};
  function loadImg(k,s){ var im=new Image(); im.src=s; IMG[k]=im; }
  loadImg('bg','assets/battle/bg_battle_02_snow.jpg');
  loadImg('ally','assets/castles/castle_ally.png');
  loadImg('enemy','assets/castles/castle_enemy.png');
  loadImg('neutral','assets/castles/castle_neutral.png');
  var UNIT_C={spear:'#9fb0c4',cavalry:'#e0a54a',archer:'#5fb86a'};

  function pvpMap(){
    var home=function(x,y,o,n){return {x:x,y:y,owner:o,name:n,isHome:true,primary:'spear',troops:{spear:30,cavalry:8,archer:8},size:1.3,trait:'prod'};};
    var neu=function(x,y,t,p){return {x:x,y:y,owner:0,name:'',primary:p,troops:{spear:5,cavalry:4,archer:4},size:1.0,trait:t};};
    return { world:{w:1,h:1.7}, growthMult:1.0, humanFactions:[1,2], castles:[
      home(0.5,0.90,1,'아군본진'), home(0.5,0.10,2,'적본진'),
      neu(0.5,0.50,'def','archer'), neu(0.24,0.66,'atk','cavalry'), neu(0.76,0.34,'atk','cavalry'),
      neu(0.76,0.66,'prod','spear'), neu(0.24,0.34,'prod','spear'),
    ]};
  }

  // --- WebSocket 연결(같은 호스트, http→ws / https→wss) ---
  var ws=null, wsReady=false;
  var chan={ _hs:[], send:function(m){ if(ws&&wsReady) ws.send(JSON.stringify({t:'relay',m:m})); }, onMessage:function(cb){ this._hs.push(cb); }, _deliver:function(m){ for(var i=0;i<this._hs.length;i++) this._hs[i](m); } };
  var PROD_SERVER='wss://games.wooriban.org';  // APK/로컬 등 '서버 밖'에서 열릴 때 접속할 배포 서버
  function serverUrl(){
    var h=location.hostname;
    // 실제 서버에서 서빙된 경우(브라우저 직접접속) 같은 오리진, 그 외(APK localhost/file)엔 배포서버로 고정
    if((location.protocol==='http:'||location.protocol==='https:') && h && h!=='localhost' && h!=='127.0.0.1')
      return (location.protocol==='https:'?'wss:':'ws:')+'//'+location.host;
    return PROD_SERVER;
  }
  function connect(){
    ws=new WebSocket(serverUrl());
    ws.onopen=function(){ wsReady=true; $('conn').textContent='● 연결됨'; $('conn').style.color='#3fb950';
      var uid=localStorage.getItem('mp_uid');
      if(uid) ws.send(JSON.stringify({t:'hello',uid:uid}));  // 재로그인
    };
    ws.onclose=function(){ wsReady=false; $('conn').textContent='● 연결 끊김'; $('conn').style.color='#f85149'; setTimeout(connect,1500); };
    ws.onerror=function(){};
    ws.onmessage=function(e){ var m; try{m=JSON.parse(e.data);}catch(_){return;} onServer(m); };
  }
  function onServer(m){
    if(m.t==='welcome'){ myUid=m.uid; myNick=m.nick; localStorage.setItem('mp_uid',m.uid); lastStats={wins:m.wins,draws:m.draws||0,losses:m.losses}; showLobby(m.wins,m.losses); requestLobbyRank(); }
    else if(m.t==='error'){ if(m.code==='dup'||m.code==='nick'){ $('nickErr').textContent=m.msg; $('regBtn').disabled=false; } else if(m.code==='noauth'){ showNick(); } }
    else if(m.t==='queued'){ isQueued=true; $('findMsg').style.display='block'; $('cancelBtn').style.display=''; $('rankBtn').style.display='none'; $('lobbyBackBtn').style.display='none'; $('findRow').style.display='none'; }
    else if(m.t==='matched'){ oppNick=m.opp; startMatch(m.role); }
    else if(m.t==='stats'){ lastStats={wins:m.wins,draws:m.draws||0,losses:m.losses}; $('wins').textContent=m.wins; $('draws').textContent=m.draws||0; $('losses').textContent=m.losses; $('pts').textContent=(m.wins*3+(m.draws||0)); requestLobbyRank(); if(over) $('bstat').textContent='전적 '+m.wins+'승 '+(m.draws||0)+'무 '+m.losses+'패'; }
    else if(m.t==='rank'){ renderRank(m); }
    else if(m.t==='oppLeft'){ if(role && !over){ endBanner(mySide,'상대가 나갔습니다'); } }
    else if(m.t==='relay'){ chan._deliver(m.m); }
  }

  var myUid=null, myNick=null, oppNick=null, lastStats={wins:0,draws:0,losses:0};
  // '메인으로' 버튼: index.html(메인게임)은 앱·웹 모두 존재하므로 항상 노출(대전 중엔 숨김).
  function showBack(on){ var b=$('backMain'); if(b) b.style.display=on?'block':'none'; }

  // --- 메타: 본편 SAVE(localStorage 'save')에서 장수 로드아웃·전투력 산출 ---
  var myLoadout={upg:{},generals:[]}, myPower=1000, mpRoster=[];
  try { mpRoster = buildRoster(window.GENERALS_200); } catch(_) { mpRoster = buildRoster(null); }
  function refreshLoadout(){
    var save={};
    try { save=JSON.parse(localStorage.getItem('save')||'{}'); } catch(_) { save={}; }
    try { myLoadout=computeLoadout(save, mpRoster); myPower=computePower(myLoadout); }
    catch(_) { myLoadout={upg:{},generals:[]}; myPower=1000; }
    if($('power')) $('power').textContent=myPower;
    if($('squad')) $('squad').textContent=(myLoadout.generals||[]).length;
  }

  function showNick(){ $('pNick').style.display='flex'; $('pLobby').style.display='none'; $('banner').style.display='none'; $('banner').classList.remove('is-win','is-loss'); showBack(true); $('nick').focus&&$('nick').focus(); }
  function showLobby(w,l){ $('pNick').style.display='none'; $('pLobby').style.display='flex'; $('pRank').style.display='none'; $('banner').style.display='none'; $('banner').classList.remove('is-win','is-loss'); showBack(true); $('hello').textContent='군주 '+myNick; var d=lastStats.draws||0; $('wins').textContent=w; $('draws').textContent=d; $('losses').textContent=l; $('pts').textContent=(w*3+d); lastStats={wins:w,draws:d,losses:l}; if(isQueued){ $('findRow').style.display='none'; $('findMsg').style.display='block'; $('cancelBtn').style.display=''; $('rankBtn').style.display='none'; $('lobbyBackBtn').style.display='none'; } else { $('findRow').style.display=''; $('findMsg').style.display='none'; $('cancelBtn').style.display='none'; $('rankBtn').style.display=''; $('lobbyBackBtn').style.display=''; } refreshLoadout(); }
  // 랭킹 화면
  function requestLobbyRank(){ if(ws&&wsReady&&myUid) ws.send(JSON.stringify({t:'rank'})); }
  function showRank(){ if(isQueued) return; $('pLobby').style.display='none'; $('pRank').style.display='flex'; showBack(true); $('myRank').innerHTML='<div class="info">불러오는 중…</div>'; $('rankList').innerHTML=''; if(ws&&wsReady) ws.send(JSON.stringify({t:'rank'})); }
  function esc(s){ return String(s==null?'':s).replace(/[&<>"]/g,function(c){return{'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;'}[c];}); }
  function renderRank(m){
    var me=m.me;
    if($('lobbyRank')) $('lobbyRank').textContent = me ? (me.rank+'위') : '-';
    $('myRank').innerHTML = me
      ? '<div class="rk">'+me.rank+'위</div><div class="info"><div class="nm">'+esc(me.nick)+' <span style="color:#8fb6f5">(나)</span></div><div class="sub">'+me.wins+'승 '+me.draws+'무 '+me.losses+'패 · 전체 '+me.total+'명</div></div><div class="pt">'+me.pts+'점</div>'
      : '<div class="info">닉네임 등록 후 순위가 집계됩니다.</div>';
    var top=m.top||[];
    if(!top.length){ $('rankList').innerHTML='<div class="empty">아직 대전 기록이 없습니다.</div>'; return; }
    var rows=top.map(function(u,i){ var rk=u.rank||(i+1); var badge='<span class="rank-mark '+(rk<=3?'top r'+rk:'')+'"><span>'+rk+'</span></span>'; var isMe=u.mine||(me&&u.nick===me.nick);
      return '<tr class="'+(isMe?'me':'')+'"><td class="rk">'+badge+'</td><td>'+esc(u.nick)+'</td><td class="n">'+u.wins+'/'+u.draws+'/'+u.losses+'</td><td class="n" style="color:#3fb950;font-weight:800">'+u.pts+'</td></tr>'; }).join('');
    $('rankList').innerHTML='<table><thead><tr><th class="rk">#</th><th>닉네임</th><th class="n">승/무/패</th><th class="n">점수</th></tr></thead><tbody>'+rows+'</tbody></table>';
  }

  // --- 매치 ---
  var role=null, host=null, guest=null, mySide=null, gmap=null, over=false, selected=-1, flip=false, isQueued=false;
  var STEP=1/15, acc=0, lastT=0, raf=null;
  function startMatch(r){
    role=r; over=false; selected=-1; isQueued=false;
    $('pLobby').style.display='none'; $('pRank').style.display='none'; $('pNick').style.display='none'; $('banner').style.display='none'; showBack(false);
    $('hud').style.display='flex'; $('tip').style.display='block';
    if(r==='host'){ mySide=1; gmap=pvpMap(); host=new HostMatch(gmap,(Math.random()*2e9)>>>0,chan,{hostSide:1,guestSide:2,snapEvery:1,hostLoadout:myLoadout}); host.start(); flip=homeIsTop(); resize(); }
    else { guest=new GuestMatch(chan,{ loadout:myLoadout, onStart:function(mm){ mySide=mm.youSide; gmap=mm.map; flip=homeIsTop(); resize(); }, onEnd:function(mm){ endBanner(mm.winner); } }); guest.join(); }
    lastT=performance.now(); acc=0; if(!raf) loop();
    keepAlive();
  }
  function homeIsTop(){ if(!gmap||!mySide) return false; for(var i=0;i<gmap.castles.length;i++){ var c=gmap.castles[i]; if(c.isHome&&c.owner===mySide) return c.y<0.5; } return false; }
  function keepAlive(){ try{ if(window._ac)return; var AC=window.AudioContext||window.webkitAudioContext; if(!AC)return; var ac=new AC(); window._ac=ac; var o=ac.createOscillator(),g=ac.createGain(); g.gain.value=0.0006; o.frequency.value=40; o.connect(g); g.connect(ac.destination); o.start(); if(ac.state==='suspended')ac.resume(); }catch(_){}}
  document.addEventListener('pointerdown',function(){ if(role) keepAlive(); },true);

  // --- 렌더(mp_game과 동일) ---
  var pxW=1,pxH=1,curV=null,gWallMax=[];
  function computePx(){ if(role==='host'){ pxW=host.eng._pxW; pxH=host.eng._pxH; } else if(gmap){ var e=new SimEngine(gmap,0); pxW=e._pxW; pxH=e._pxH; gWallMax=e.castles.map(function(c){return c.wallMax;}); } }
  function castlesView(){ if(role==='host') return host.eng.castles; if(guest&&guest.snap&&gmap) return gmap.castles.map(function(mc,i){ var sc=guest.snap.castles[i]; return {x:mc.x,y:mc.y,isHome:mc.isHome,size:mc.size,owner:sc?sc.owner:mc.owner,primary:sc?sc.primary:mc.primary,troops:sc?sc.troops:mc.troops,wallHP:sc?sc.wallHP:0,wallMax:gWallMax[i]||60}; }); return []; }
  function armiesView(){ return role==='host'?host.eng.armies:(guest&&guest.snap?guest.snap.armies:[]); }
  function resize(){ var st=$('stage'); var W=st.clientWidth,H=st.clientHeight; var dpr=Math.min(2,window.devicePixelRatio||1); cv.width=W*dpr; cv.height=H*dpr; cv.style.width=W+'px'; cv.style.height=H+'px'; ctx.setTransform(dpr,0,0,dpr,0,0); cv._W=W; cv._H=H; }
  window.addEventListener('resize', resize);
  function view(){ computePx(); var W=cv._W||cv.width,H=cv._H||cv.height,pad=26; var s=Math.min((W-pad*2)/pxW,(H-pad*2)/pxH); return {s:s,ox:(W-pxW*s)/2,oy:(H-pxH*s)/2,W:W,H:H}; }
  function S(v){ var wx=v.x*pxW,wy=v.y*pxH,vv=curV; var sx=vv.ox+wx*vv.s, sy=vv.oy+wy*vv.s; if(flip){ sx=vv.W-sx; sy=vv.H-sy; } return {x:sx,y:sy}; }
  function ownerColor(o){ return o===0?'#8b949e':(o===mySide?'#58a6ff':'#f85149'); }
  function drawCover(img,x,y,w,h){ var iw=img.naturalWidth,ih=img.naturalHeight,r=Math.max(w/iw,h/ih),dw=iw*r,dh=ih*r; ctx.drawImage(img,x+(w-dw)/2,y+(h-dh)/2,dw,dh); }
  function castleImg(o){ if(o===0) return IMG.neutral; return o===mySide?IMG.ally:IMG.enemy; }
  function roundRect(x,y,w,h,r){ ctx.beginPath(); ctx.moveTo(x+r,y); ctx.arcTo(x+w,y,x+w,y+h,r); ctx.arcTo(x+w,y+h,x,y+h,r); ctx.arcTo(x,y+h,x,y,r); ctx.arcTo(x,y,x+w,y,r); ctx.closePath(); }
  function labelBadge(x,y,txt,col){ ctx.font='bold 15px system-ui'; ctx.textAlign='center'; ctx.textBaseline='middle'; var w=ctx.measureText(txt).width+14; ctx.fillStyle='rgba(8,12,20,.82)'; roundRect(x-w/2,y-12,w,24,7); ctx.fill(); ctx.strokeStyle=col; ctx.lineWidth=1.5; roundRect(x-w/2,y-12,w,24,7); ctx.stroke(); ctx.fillStyle='#fff'; ctx.fillText(txt,x,y+1); }
  function drawCastle(c,sel){ var p=S(c); var r=Math.max(26,34*(c.size||1)*curV.s); if(sel){ ctx.beginPath(); ctx.arc(p.x,p.y,r*1.15,0,Math.PI*2); ctx.strokeStyle='#ffd24a'; ctx.lineWidth=3; ctx.stroke(); } var wr=c.wallMax?Math.max(0,c.wallHP/c.wallMax):1; ctx.beginPath(); ctx.arc(p.x,p.y,r*1.02,-Math.PI/2,-Math.PI/2+Math.PI*2*wr); ctx.strokeStyle=ownerColor(c.owner); ctx.lineWidth=3; ctx.stroke(); var im=castleImg(c.owner); if(im.complete&&im.naturalWidth){ var d=r*2.1; ctx.drawImage(im,p.x-d/2,p.y-d/2,d,d); } else { ctx.beginPath(); ctx.arc(p.x,p.y,r,0,Math.PI*2); ctx.fillStyle=ownerColor(c.owner); ctx.fill(); } if(c.isHome){ ctx.fillStyle=(c.owner===mySide?'#ffd24a':'#ff9db0'); ctx.font='bold '+Math.round(r*0.7)+'px system-ui'; ctx.textAlign='center'; ctx.textBaseline='middle'; ctx.fillText('★',p.x,p.y-r*1.25); } var tot=(c.troops.spear|0)+(c.troops.cavalry|0)+(c.troops.archer|0); labelBadge(p.x,p.y-r*0.15,tot,ownerColor(c.owner)); }
  function drawArmy(a){ var p=S({x:a.x/pxW,y:a.y/pxH}); var n=Math.max(1,Math.min(12,Math.ceil(a.troops/3))); var col=ownerColor(a.owner),uc=UNIT_C[a.unit]||'#fff'; ctx.globalAlpha=a.dying?0.4:1; for(var i=0;i<n;i++){ var ang=(i/n)*Math.PI*2+a.x*0.01; var rr=(i?9+(i%3)*4:0)*curV.s*0.7; var sx=p.x+Math.cos(ang)*rr, sy=p.y+Math.sin(ang)*rr*0.7; ctx.beginPath(); ctx.arc(sx,sy,3.4,0,Math.PI*2); ctx.fillStyle=col; ctx.fill(); ctx.lineWidth=1.2; ctx.strokeStyle=uc; ctx.stroke(); } ctx.globalAlpha=1; ctx.fillStyle='#fff'; ctx.font='bold 11px system-ui'; ctx.textAlign='center'; ctx.textBaseline='middle'; ctx.strokeStyle='rgba(0,0,0,.7)'; ctx.lineWidth=3; ctx.strokeText(a.troops,p.x,p.y-14); ctx.fillText(a.troops,p.x,p.y-14); }
  function draw(){ curV=view(); var W=curV.W,H=curV.H; ctx.clearRect(0,0,W,H); if(IMG.bg.complete&&IMG.bg.naturalWidth) drawCover(IMG.bg,0,0,W,H); else { ctx.fillStyle='#dfe7ee'; ctx.fillRect(0,0,W,H); } var cs=castlesView(),av=armiesView(); for(var i=0;i<av.length;i++) drawArmy(av[i]); for(var j=0;j<cs.length;j++) drawCastle(cs[j],j===selected); hud(cs,av); }
  function hud(cs,av){ var enemy=mySide===1?2:1; var mc=cs.filter(function(c){return c.owner===mySide;}),ec=cs.filter(function(c){return c.owner===enemy;}); var sum=function(arr,o){ return arr.reduce(function(s,c){return s+(c.troops.spear|0)+(c.troops.cavalry|0)+(c.troops.archer|0);},0)+av.filter(function(a){return a.owner===o;}).reduce(function(s,a){return s+a.troops;},0); }; $('meC').textContent=mc.length; $('meT').textContent=sum(mc,mySide); $('enC').textContent=ec.length; $('enT').textContent=sum(ec,enemy); $('tk').textContent=role==='host'?host.eng.tick:(guest&&guest.snap?guest.snap.tick:0); }

  function loop(){ raf=requestAnimationFrame(loop); var now=performance.now(); var dt=Math.min((now-lastT)/1000,0.5); lastT=now; if(role==='host'&&!host.over){ acc+=dt; while(acc>=STEP){ host.tick(); acc-=STEP; if(host.over)break; } if(host.over&&!over) endBanner(host.eng.winner); } if(role&&!over) draw(); }

  function castleAt(px,py){ var cs=castlesView(),best=-1,bd=40*curV.s*0.9+18; for(var i=0;i<cs.length;i++){ var p=S(cs[i]); var d=Math.hypot(px-p.x,py-p.y); if(d<bd){bd=d;best=i;} } return best; }
  cv.addEventListener('pointerdown',function(e){ if(over||!role) return; var r=cv.getBoundingClientRect(); var px=(e.clientX-r.left),py=(e.clientY-r.top); var hit=castleAt(px,py); var cs=castlesView(); if(hit<0){ selected=-1; return; } if(selected<0){ if(cs[hit].owner===mySide) selected=hit; } else if(hit===selected){ selected=-1; } else { var src=cs[selected]; ['spear','cavalry','archer'].forEach(function(u){ if((src.troops[u]|0)>0){ var cmd={type:'SEND_ARMY',fromId:selected,toId:hit,unit:u}; if(role==='host') host.hostCommand(cmd); else guest.command(cmd); } }); selected=-1; } });

  function endBanner(winner,note){ if(over) return; over=true; var win=winner===mySide, b=$('banner'); b.classList.remove('is-win','is-loss'); b.classList.add(win?'is-win':'is-loss'); $('bkicker').textContent=win?'승전 결과':'전투 결과'; $('bwin').textContent=win?'승리':'패배'; $('bsub').textContent=note||(win?'장수들이 승전고를 울렸습니다':'성을 정비하고 다시 출정하십시오'); $('bstat').textContent='전적 '+lastStats.wins+'승 '+(lastStats.draws||0)+'무 '+lastStats.losses+'패'; b.style.display='flex'; $('hud').style.display='none'; $('tip').style.display='none'; if(role==='host'&&winner!=null){ try{ ws.send(JSON.stringify({t:'result',winner:winner})); }catch(_){} } }

  // --- UI 이벤트 ---
  $('regBtn').onclick=function(){ var n=$('nick').value.trim(); if(!n){ $('nickErr').textContent='닉네임을 입력하세요'; return; } $('nickErr').textContent=''; $('regBtn').disabled=true; ws.send(JSON.stringify({t:'hello',nick:n})); setTimeout(function(){$('regBtn').disabled=false;},1500); };
  $('nick').addEventListener('keydown',function(e){ if(e.key==='Enter') $('regBtn').click(); });
  $('findBtn').onclick=function(){ refreshLoadout(); ws.send(JSON.stringify({t:'queue', power:myPower, mode:'ranked'})); };
  $('findRandomBtn').onclick=function(){ refreshLoadout(); ws.send(JSON.stringify({t:'queue', power:myPower, mode:'random'})); };
  $('cancelBtn').onclick=function(){ isQueued=false; ws.send(JSON.stringify({t:'cancel'})); $('findMsg').style.display='none'; $('cancelBtn').style.display='none'; $('rankBtn').style.display=''; $('lobbyBackBtn').style.display=''; $('findRow').style.display=''; };
  $('again').onclick=function(){ role=null; host=null; guest=null; over=false; $('banner').style.display='none'; $('banner').classList.remove('is-win','is-loss'); $('hud').style.display='none'; ws.send(JSON.stringify({t:'stats'})); showLobby(lastStats.wins,lastStats.losses); };
  $('surr').onclick=function(){ if(role==='guest') guest.surrender(); else if(role==='host') host._forceWin(2,'surrender'); };
  $('rankBtn').onclick=function(){ showRank(); };
  $('lobbyBackBtn').onclick=function(){ location.href='index.html'; };
  $('rankBack').onclick=function(){ showLobby(lastStats.wins,lastStats.losses); };

  // 최초: uid 있으면 자동 로그인, 없으면 닉네임 화면
  if(!localStorage.getItem('mp_uid')) showNick();
  resize();
  connect();
})();
</script>
</body>
</html>
`;
fs.writeFileSync(path.join(pub, 'mp_game.html'), html);

const twoView = `<!doctype html><html lang="ko"><head><meta charset="utf-8"><title>1v1 2뷰</title>
<style>html,body{margin:0;height:100%;background:#0b0f16;overflow:hidden}
.bar{height:26px;color:#ffd24a;font:12px system-ui;display:flex;align-items:center;padding:0 10px;background:#131a24}
.w{display:flex;height:calc(100vh - 27px);gap:3px;background:#263041}iframe{flex:1;height:100%;border:0}</style></head>
<body><div class="bar">한 창 2뷰 테스트 — 각 화면 닉네임 등록 후 '대전 찾기'</div>
<div class="w"><iframe src="mp_game.html" allow="autoplay"></iframe><iframe src="mp_game.html" allow="autoplay"></iframe></div></body></html>`;
fs.writeFileSync(path.join(pub, 'mp_game_2view.html'), twoView);

console.log('생성 완료: server/public/mp_game.html (' + Math.round(html.length/1024) + 'KB) + mp_game_2view.html + 자산 복사');
