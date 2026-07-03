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
const pub = path.join(root, 'server', 'public');

// 필요한 자산만 복사(용량 최소)
function copy(rel) { const src = path.join(root, rel), dst = path.join(pub, rel); fs.mkdirSync(path.dirname(dst), { recursive: true }); fs.copyFileSync(src, dst); }
fs.mkdirSync(pub, { recursive: true });
['assets/battle/bg_battle_02_snow.jpg', 'assets/castles/castle_ally.png', 'assets/castles/castle_enemy.png', 'assets/castles/castle_neutral.png'].forEach(copy);

const html = `<!doctype html>
<html lang="ko">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1, maximum-scale=1, user-scalable=no">
<title>손가락삼국지 — 실시간 1v1</title>
<style>
  :root { color-scheme: dark; } * { box-sizing: border-box; }
  html,body { margin:0; height:100%; background:#0b0f16; color:#e6edf3; font:14px/1.4 'Noto Sans KR',system-ui,sans-serif; overscroll-behavior:none; -webkit-user-select:none; user-select:none; }
  #wrap { display:flex; flex-direction:column; height:100%; }
  #hud { display:none; gap:14px; padding:7px 12px; align-items:center; border-bottom:1px solid #1c2430; font-variant-numeric:tabular-nums; }
  .me { color:#58a6ff; font-weight:700; } .en { color:#f85149; font-weight:700; }
  #hud .sp { flex:1; }
  #stage { position:relative; flex:1; display:flex; align-items:center; justify-content:center; touch-action:none; overflow:hidden; }
  canvas { display:block; touch-action:none; }
  .panel { position:absolute; inset:0; display:flex; align-items:center; justify-content:center; flex-direction:column; gap:16px; background:radial-gradient(circle at 50% 30%,rgba(20,32,58,.6),rgba(5,8,13,.94)); z-index:10; text-align:center; padding:20px; }
  h1 { font:900 26px 'Noto Serif KR',serif; color:#fff1b8; margin:0; text-shadow:0 2px 0 rgba(0,0,0,.6); }
  input { background:#0b0f16; color:#e6edf3; border:2px solid #2b3543; border-radius:10px; padding:12px 14px; font-size:18px; text-align:center; width:220px; }
  button { background:linear-gradient(180deg,#f2b536,#d58716); color:#2a1206; border:2px solid #8a5a13; border-radius:12px; padding:14px 28px; font:800 18px 'Noto Serif KR',serif; cursor:pointer; box-shadow:0 4px 0 #7a4e12; }
  button:active { transform:translateY(2px); box-shadow:0 2px 0 #7a4e12; }
  button:disabled { opacity:.5; }
  .muted { color:#8b949e; font-size:13px; }
  .err { color:#ff8080; font-size:13px; min-height:18px; }
  .stat { color:#cbd5e1; font-size:15px; }
  #banner h2 { font-size:44px; margin:0; }
  #tip { display:none; padding:6px 12px; color:#6e7681; font-size:12px; border-top:1px solid #1c2430; }
  #conn { position:fixed; right:8px; top:8px; z-index:30; font:11px monospace; color:#6e7681; }
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
    <div class="panel" id="pNick">
      <h1>⚔ 실시간 1v1</h1>
      <div class="muted">처음이신가요? 닉네임을 정하세요</div>
      <input id="nick" maxlength="16" placeholder="닉네임" autocomplete="off">
      <div class="err" id="nickErr"></div>
      <button id="regBtn">시작</button>
    </div>
    <!-- 로비 -->
    <div class="panel" id="pLobby" style="display:none">
      <h1 id="hello">환영합니다</h1>
      <div class="stat">전적 <b id="wins" style="color:#58a6ff">0</b>승 <b id="losses" style="color:#f85149">0</b>패</div>
      <button id="findBtn">대전 찾기</button>
      <div class="muted" id="findMsg" style="display:none">상대를 찾는 중…</div>
      <button id="cancelBtn" style="display:none;background:#1c2430;color:#e6edf3;border-color:#2b3543;box-shadow:none">취소</button>
    </div>
    <!-- 결과 -->
    <div class="panel" id="banner" style="display:none">
      <h2 id="bwin"></h2>
      <div class="stat" id="bstat"></div>
      <button id="again">로비로</button>
    </div>
  </div>
  <div id="tip">내 성(파랑) 탭 → 목표 성 탭 = 전 병력 출진. 상대 본진(★) 함락 시 승리.</div>
</div>
<div id="conn">연결 중…</div>

<script>
// ===== engine.js =====
${engineSrc}
// ===== netmatch.js =====
${netSrc}
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
  function connect(){
    var proto=location.protocol==='https:'?'wss:':'ws:';
    ws=new WebSocket(proto+'//'+location.host);
    ws.onopen=function(){ wsReady=true; $('conn').textContent='● 연결됨'; $('conn').style.color='#3fb950';
      var uid=localStorage.getItem('mp_uid');
      if(uid) ws.send(JSON.stringify({t:'hello',uid:uid}));  // 재로그인
    };
    ws.onclose=function(){ wsReady=false; $('conn').textContent='● 연결 끊김'; $('conn').style.color='#f85149'; setTimeout(connect,1500); };
    ws.onerror=function(){};
    ws.onmessage=function(e){ var m; try{m=JSON.parse(e.data);}catch(_){return;} onServer(m); };
  }
  function onServer(m){
    if(m.t==='welcome'){ myUid=m.uid; myNick=m.nick; localStorage.setItem('mp_uid',m.uid); showLobby(m.wins,m.losses); }
    else if(m.t==='error'){ if(m.code==='dup'||m.code==='nick'){ $('nickErr').textContent=m.msg; $('regBtn').disabled=false; } else if(m.code==='noauth'){ showNick(); } }
    else if(m.t==='queued'){ $('findMsg').style.display='block'; $('cancelBtn').style.display='inline-block'; $('findBtn').style.display='none'; }
    else if(m.t==='matched'){ oppNick=m.opp; startMatch(m.role); }
    else if(m.t==='stats'){ lastStats={wins:m.wins,losses:m.losses}; $('wins').textContent=m.wins; $('losses').textContent=m.losses; if(over) $('bstat').textContent='전적 '+m.wins+'승 '+m.losses+'패'; }
    else if(m.t==='oppLeft'){ if(role && !over){ endBanner(mySide,'상대가 나갔습니다'); } }
    else if(m.t==='relay'){ chan._deliver(m.m); }
  }

  var myUid=null, myNick=null, oppNick=null, lastStats={wins:0,losses:0};
  function showNick(){ $('pNick').style.display='flex'; $('pLobby').style.display='none'; $('banner').style.display='none'; $('nick').focus&&$('nick').focus(); }
  function showLobby(w,l){ $('pNick').style.display='none'; $('pLobby').style.display='flex'; $('banner').style.display='none'; $('hello').textContent=myNick+' 님'; $('wins').textContent=w; $('losses').textContent=l; lastStats={wins:w,losses:l}; $('findBtn').style.display='inline-block'; $('findMsg').style.display='none'; $('cancelBtn').style.display='none'; }

  // --- 매치 ---
  var role=null, host=null, guest=null, mySide=null, gmap=null, over=false, selected=-1, flip=false;
  var STEP=1/15, acc=0, lastT=0, raf=null;
  function startMatch(r){
    role=r; over=false; selected=-1;
    $('pLobby').style.display='none'; $('pNick').style.display='none'; $('banner').style.display='none';
    $('hud').style.display='flex'; $('tip').style.display='block';
    if(r==='host'){ mySide=1; gmap=pvpMap(); host=new HostMatch(gmap,(Math.random()*2e9)>>>0,chan,{hostSide:1,guestSide:2,snapEvery:1}); host.start(); flip=homeIsTop(); resize(); }
    else { guest=new GuestMatch(chan,{ onStart:function(mm){ mySide=mm.youSide; gmap=mm.map; flip=homeIsTop(); resize(); }, onEnd:function(mm){ endBanner(mm.winner); } }); guest.join(); }
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

  function endBanner(winner,note){ if(over) return; over=true; var win=winner===mySide; $('bwin').textContent=win?'🏆 승리!':'💀 패배…'; $('bwin').style.color=win?'#58a6ff':'#f85149'; $('bstat').textContent=note||('전적 '+lastStats.wins+'승 '+lastStats.losses+'패'); $('banner').style.display='flex'; $('hud').style.display='none'; $('tip').style.display='none'; if(role==='host'&&winner!=null){ try{ ws.send(JSON.stringify({t:'result',winner:winner})); }catch(_){} } }

  // --- UI 이벤트 ---
  $('regBtn').onclick=function(){ var n=$('nick').value.trim(); if(!n){ $('nickErr').textContent='닉네임을 입력하세요'; return; } $('nickErr').textContent=''; $('regBtn').disabled=true; ws.send(JSON.stringify({t:'hello',nick:n})); setTimeout(function(){$('regBtn').disabled=false;},1500); };
  $('nick').addEventListener('keydown',function(e){ if(e.key==='Enter') $('regBtn').click(); });
  $('findBtn').onclick=function(){ ws.send(JSON.stringify({t:'queue'})); };
  $('cancelBtn').onclick=function(){ ws.send(JSON.stringify({t:'cancel'})); $('findMsg').style.display='none'; $('cancelBtn').style.display='none'; $('findBtn').style.display='inline-block'; };
  $('again').onclick=function(){ role=null; host=null; guest=null; over=false; $('banner').style.display='none'; $('hud').style.display='none'; ws.send(JSON.stringify({t:'stats'})); showLobby(lastStats.wins,lastStats.losses); };
  $('surr').onclick=function(){ if(role==='guest') guest.surrender(); else if(role==='host') host._forceWin(2,'surrender'); };

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
