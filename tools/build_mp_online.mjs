// tools/build_mp_online.mjs — 2탭(같은 PC) 실시간 1v1 대전 페이지 생성.
//   전송=BroadcastChannel(같은 브라우저 탭 간). 넷코드=netmatch.js(호스트 권위).
//   목적: WebRTC/Firebase 얹기 전, 호스트 권위 대전이 '두 클라이언트' 사이에서 도는지 확인.
//   engine.js + netmatch.js 인라인(단일 소스). 실행: node tools/build_mp_online.mjs → mp_online.html
import fs from 'fs';
import path from 'path';
import { fileURLToPath } from 'url';

const root = path.dirname(path.dirname(fileURLToPath(import.meta.url)));
const engineSrc = fs.readFileSync(path.join(root, 'engine.js'), 'utf8').replace(/^export\s+/gm, '');
const netSrc = fs.readFileSync(path.join(root, 'netmatch.js'), 'utf8')
  .replace(/^import[^\n]*\n/gm, '')   // import 제거(SimEngine 전역)
  .replace(/^export\s+/gm, '');

const html = `<!doctype html>
<html lang="ko">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1, maximum-scale=1, user-scalable=no">
<title>손가락삼국지 — 실시간 1v1 (2탭 대전)</title>
<style>
  :root { color-scheme: dark; } * { box-sizing: border-box; }
  html,body { margin:0; height:100%; background:#0b0f16; color:#e6edf3; font:14px/1.4 system-ui,sans-serif; overscroll-behavior:none; }
  #wrap { display:flex; flex-direction:column; height:100%; }
  header { padding:8px 12px; border-bottom:1px solid #1c2430; display:flex; gap:8px; align-items:center; flex-wrap:wrap; }
  h1 { font-size:14px; margin:0; font-weight:700; }
  .spacer { flex:1; }
  button { background:#1c2430; color:#e6edf3; border:1px solid #2b3543; border-radius:6px; padding:6px 12px; cursor:pointer; font-size:13px; }
  button:hover { background:#263041; } button:disabled { opacity:.4; cursor:default; }
  .role { font-weight:700; } .rhost { color:#58a6ff; } .rguest { color:#f85149; }
  #hud { display:flex; gap:14px; padding:6px 12px; font-variant-numeric:tabular-nums; border-bottom:1px solid #1c2430; }
  #stage { position:relative; flex:1; display:flex; align-items:center; justify-content:center; touch-action:none; }
  canvas { background:radial-gradient(circle at 50% 50%,#14203a 0%,#0b0f16 80%); border:1px solid #1c2430; border-radius:10px; touch-action:none; }
  #banner { position:absolute; inset:0; display:none; align-items:center; justify-content:center; flex-direction:column; gap:12px; background:rgba(5,8,13,.72); }
  #banner h2 { font-size:38px; margin:0; }
  #tip { padding:6px 12px; color:#6e7681; font-size:12px; border-top:1px solid #1c2430; }
  #lobby { position:absolute; inset:0; display:flex; align-items:center; justify-content:center; flex-direction:column; gap:14px; background:#0b0f16; }
  #lobby p { color:#8b949e; max-width:320px; text-align:center; }
</style>
</head>
<body>
<div id="wrap">
  <header>
    <h1>⚔ 실시간 1v1 <span style="color:#6e7681;font-weight:400">host-authoritative</span></h1>
    <span id="roleTag" class="role"></span>
    <div class="spacer"></div>
    <span id="conn" style="color:#8b949e">대기</span>
    <span id="ping" style="color:#6e7681"></span>
  </header>
  <div id="hud">
    <div style="color:#58a6ff">🔵 진영1 성 <b id="c1">-</b> 병력 <b id="t1">-</b></div>
    <div style="color:#f85149">🔴 진영2 성 <b id="c2">-</b> 병력 <b id="t2">-</b></div>
    <div class="spacer"></div>
    <div style="color:#8b949e">tick <b id="tk">0</b></div>
    <button id="surrender" style="display:none">항복</button>
  </div>
  <div id="stage">
    <canvas id="cv" width="420" height="720"></canvas>
    <div id="lobby">
      <h2 style="margin:0">2탭 대전</h2>
      <p>이 페이지를 <b>탭(창) 2개</b>로 여세요. 한쪽은 <b>호스트로 시작</b>, 다른쪽은 <b>게스트로 참가</b>.<br>같은 브라우저의 두 탭이 BroadcastChannel로 연결됩니다.</p>
      <div style="display:flex;gap:10px">
        <button id="beHost">🔵 호스트로 시작</button>
        <button id="beGuest">🔴 게스트로 참가</button>
      </div>
      <label style="color:#8b949e">seed <input id="seed" type="number" value="777" style="width:70px;background:#0b0f16;color:#e6edf3;border:1px solid #2b3543;border-radius:4px;padding:4px"></label>
    </div>
    <div id="banner"><h2 id="bwin"></h2><button id="again">로비로</button></div>
  </div>
  <div id="tip">내 진영 색 성 탭 → 목표 성 탭 = 전 병력 출진. 상대 본진(★) 함락 시 승리. 호스트가 권위 시뮬을 돌리고 게스트는 스냅샷을 렌더.</div>
</div>

<script>
// ===== engine.js =====
${engineSrc}
// ===== netmatch.js =====
${netSrc}
// ===== 2탭 대전 (BroadcastChannel 전송) =====
(function(){
  const C = { 0:'#8b949e', 1:'#58a6ff', 2:'#f85149' };
  const UNIT_C = { spear:'#9fb0c4', cavalry:'#e0a54a', archer:'#5fb86a' };
  const $ = (id) => document.getElementById(id);
  const cv = $('cv'), ctx = cv.getContext('2d');

  function pvpMap(seed){
    const home=(x,y,o,n)=>({x,y,owner:o,name:n,isHome:true,primary:'spear',troops:{spear:30,cavalry:8,archer:8},size:1.25,trait:'prod'});
    const neu=(x,y,t,p)=>({x,y,owner:0,name:'',primary:p,troops:{spear:5,cavalry:4,archer:4},size:0.95,trait:t});
    return { world:{w:1,h:1.7}, growthMult:1.0, humanFactions:[1,2], castles:[
      home(0.5,0.90,1,'진영1본진'), home(0.5,0.10,2,'진영2본진'),
      neu(0.5,0.50,'def','archer'),
      neu(0.24,0.66,'atk','cavalry'), neu(0.76,0.34,'atk','cavalry'),
      neu(0.76,0.66,'prod','spear'), neu(0.24,0.34,'prod','spear'),
    ]};
  }

  // BroadcastChannel 전송 래퍼 (같은-브라우저 2탭). 자기 메시지는 에코 안 됨 → 사실상 point-to-point.
  function bcChannel(name){
    const bc = new BroadcastChannel(name);
    let cb = null;
    bc.onmessage = (e) => { if (cb) cb(e.data); };
    return { send:(m)=>bc.postMessage(m), onMessage:(f)=>{ cb=f; }, _bc:bc };
  }

  let role=null, host=null, guest=null, mySide=null, map=null, raf=null, acc=0, lastT=0, selected=-1, over=false;
  // 렌더 소스: 호스트는 host.eng(권위), 게스트는 guest.snap+guest.map
  function castlesView(){
    if (role==='host') return host.eng.castles;
    if (guest && guest.snap && guest.map) return guest.map.castles.map((mc,i)=>({ x:mc.x,y:mc.y,isHome:mc.isHome,size:mc.size,owner:guest.snap.castles[i].owner,troops:guest.snap.castles[i].troops,wallHP:guest.snap.castles[i].wallHP,wallMax:host?0:0 }));
    return [];
  }
  function pxW(){ return role==='host'? host.eng._pxW : (mapPx.w); }
  function pxH(){ return role==='host'? host.eng._pxH : (mapPx.h); }
  let mapPx = { w:1, h:1 };

  function fitScale(){ const pad=30; return { s:Math.min((cv.width-pad*2)/pxW(),(cv.height-pad*2)/pxH()), pad }; }
  const SX=(wx)=>{const{s,pad}=fitScale();return pad+wx*s;};
  const SY=(wy)=>{const{s,pad}=fitScale();return pad+wy*s;};
  const WX=(c)=>c.x*pxW(), WY=(c)=>c.y*pxH();

  function startHost(){
    role='host'; mySide=1;
    const seed=(parseInt($('seed').value,10)||1)>>>0;
    map=pvpMap(seed);
    const ch=bcChannel('samgukgi-mp');
    host=new HostMatch(map, seed, ch, { hostSide:1, guestSide:2, snapEvery:2 });
    mapPx={ w:host.eng._pxW, h:host.eng._pxH };
    host.start();
    enterGame('🔵 호스트 (진영1)', 'rhost');
    // 15Hz 호스트 루프
    lastT=performance.now(); acc=0; loop();
  }
  function startGuest(){
    role='guest';
    const ch=bcChannel('samgukgi-mp');
    guest=new GuestMatch(ch, {
      onStart:(m)=>{ mySide=m.youSide; map=m.map; const e=new SimEngine(map,0); mapPx={w:e._pxW,h:e._pxH};
        enterGame('🔴 게스트 (진영'+m.youSide+')', 'rguest'); $('conn').textContent='연결됨'; },
      onEnd:(m)=>{ endBanner(m.winner); },
    });
    guest.join();
    enterGame('… 호스트 대기중', 'rguest');
    lastT=performance.now(); loop();
  }
  function enterGame(label, cls){
    $('lobby').style.display='none';
    $('roleTag').textContent=label; $('roleTag').className='role '+cls;
    $('surrender').style.display='inline-block';
    over=false; selected=-1; $('banner').style.display='none';
  }

  function loop(){
    raf=requestAnimationFrame(loop);
    const now=performance.now(); let dt=Math.min((now-lastT)/1000,0.1); lastT=now;
    if (role==='host' && !host.over){
      acc+=dt; const STEP=1/15;
      while(acc>=STEP){ host.tick(); acc-=STEP; if(host.over)break; }
      if (host.over && !over) endBanner(host.eng.winner);
      $('conn').textContent='진행중(권위)';
    }
    render();
  }

  function castleAt(px,py){
    const cs=castlesView(); let best=-1,bd=26;
    cs.forEach((c,i)=>{ const d=Math.hypot(px-SX(WX(c)),py-SY(WY(c))); if(d<bd){bd=d;best=i;} });
    return best;
  }
  function onTap(e){
    if(over||!role)return;
    const r=cv.getBoundingClientRect();
    const px=(e.clientX-r.left)*(cv.width/r.width), py=(e.clientY-r.top)*(cv.height/r.height);
    const hit=castleAt(px,py); const cs=castlesView();
    if(hit<0){ selected=-1; return; }
    if(selected<0){ if(cs[hit].owner===mySide) selected=hit; }
    else if(hit===selected){ selected=-1; }
    else {
      const src=cs[selected];
      for(const u of ['spear','cavalry','archer']){
        if((src.troops[u]|0)>0){
          const cmd={ type:'SEND_ARMY', fromId:selected, toId:hit, unit:u };
          if(role==='host') host.hostCommand(cmd); else guest.command(cmd);
        }
      }
      selected=-1;
    }
  }
  cv.addEventListener('pointerdown', onTap);

  function armiesView(){ return role==='host'? host.eng.armies : (guest&&guest.snap?guest.snap.armies:[]); }

  function render(){
    ctx.clearRect(0,0,cv.width,cv.height);
    for(const a of armiesView()){
      const x=SX(a.x), y=SY(a.y);
      ctx.beginPath(); ctx.arc(x,y,a.dying?3:5.5,0,Math.PI*2);
      ctx.fillStyle=C[a.owner]||'#888'; ctx.globalAlpha=a.dying?0.35:1; ctx.fill();
      ctx.strokeStyle=UNIT_C[a.unit]||'#fff'; ctx.lineWidth=1.5; ctx.stroke(); ctx.globalAlpha=1;
      ctx.fillStyle='#dfe7f0'; ctx.font='9px system-ui'; ctx.textAlign='center'; ctx.textBaseline='middle';
      ctx.fillText(a.troops, x, y-10);
    }
    const cs=castlesView();
    cs.forEach((c,i)=>{
      const x=SX(WX(c)), y=SY(WY(c)), r=15*(c.size||1);
      if(i===selected){ ctx.beginPath(); ctx.arc(x,y,r+9,0,Math.PI*2); ctx.strokeStyle='#ffd24a'; ctx.lineWidth=2.5; ctx.stroke(); }
      const wr = (c.wallMax? c.wallHP/c.wallMax : 1);
      ctx.beginPath(); ctx.arc(x,y,r+4,-Math.PI/2,-Math.PI/2+Math.PI*2*Math.max(0,wr));
      ctx.strokeStyle='#c9d4e0'; ctx.lineWidth=2.5; ctx.stroke();
      ctx.beginPath(); ctx.arc(x,y,r,0,Math.PI*2); ctx.fillStyle=C[c.owner]||'#888'; ctx.fill();
      const tot=c.troops.spear+c.troops.cavalry+c.troops.archer;
      ctx.fillStyle='#0b0f16'; ctx.font='bold 12px system-ui'; ctx.textAlign='center'; ctx.textBaseline='middle'; ctx.fillText(tot,x,y);
      if(c.isHome){ ctx.fillStyle= (c.owner===mySide)?'#ffd24a':'#ff9db0'; ctx.font='13px system-ui'; ctx.fillText('★',x,y-r-9); }
    });
    // HUD
    const c1=cs.filter(c=>c.owner===1), c2=cs.filter(c=>c.owner===2);
    const av=armiesView();
    const sum=(cc,o)=>cc.reduce((s,c)=>s+c.troops.spear+c.troops.cavalry+c.troops.archer,0)+av.filter(a=>a.owner===o).reduce((s,a)=>s+a.troops,0);
    $('c1').textContent=c1.length; $('t1').textContent=sum(c1,1);
    $('c2').textContent=c2.length; $('t2').textContent=sum(c2,2);
    $('tk').textContent = role==='host'? host.eng.tick : (guest&&guest.snap?guest.snap.tick:0);
  }

  function endBanner(winner){
    over=true;
    const win = winner===mySide;
    $('bwin').textContent = win?'🏆 승리!':'💀 패배…';
    $('bwin').style.color = win?'#58a6ff':'#f85149';
    $('banner').style.display='flex';
    $('conn').textContent='종료';
  }

  $('beHost').onclick=startHost;
  $('beGuest').onclick=startGuest;
  $('surrender').onclick=()=>{ if(role==='guest') guest.surrender(); else if(role==='host'){ host._forceWin(2,'surrender'); } };
  $('again').onclick=()=>location.reload();
})();
</script>
</body>
</html>
`;
fs.writeFileSync(path.join(root, 'mp_online.html'), html);
console.log('생성 완료: mp_online.html (자체완결, ' + Math.round(html.length/1024) + 'KB)');
