// tools/build_mp_game.mjs — 검증된 engine.js + netmatch.js 위에 '실제 게임 그림'을 입힌 1v1 대전 페이지.
//   몽키패치 없음: 렌더링을 100% 새로 제어 → 미러 방식의 잔버그(순서/stale/멈춤) 원천 차단.
//   자산 재사용: assets/castles/castle_{ally,enemy,neutral}.png, assets/battle/bg_battle_02_snow.jpg
//   매칭: 먼저 큐 입장(Date.now 빠른 쪽)=호스트. 호스트=권위 시뮬(engine), 게스트=스냅샷 렌더.
//   진짜 1v1: 호스트=진영1, 게스트=진영2, AI오프, 각자 '내 편=파랑(ally 스프라이트)'.
//   실행: node tools/build_mp_game.mjs → mp_game.html
import fs from 'fs';
import path from 'path';
import { fileURLToPath } from 'url';

const root = path.dirname(path.dirname(fileURLToPath(import.meta.url)));
const engineSrc = fs.readFileSync(path.join(root, 'engine.js'), 'utf8').replace(/^export\s+/gm, '');
const netSrc = fs.readFileSync(path.join(root, 'netmatch.js'), 'utf8')
  .replace(/^import[^\n]*\n/gm, '').replace(/^export\s+/gm, '');

const html = `<!doctype html>
<html lang="ko">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1, maximum-scale=1, user-scalable=no">
<title>손가락삼국지 — 실시간 1v1</title>
<style>
  :root { color-scheme: dark; } * { box-sizing: border-box; }
  html,body { margin:0; height:100%; background:#0b0f16; color:#e6edf3; font:14px/1.4 'Noto Sans KR',system-ui,sans-serif; overscroll-behavior:none; user-select:none; -webkit-user-select:none; }
  #wrap { display:flex; flex-direction:column; height:100%; }
  #hud { display:flex; gap:14px; padding:7px 12px; align-items:center; border-bottom:1px solid #1c2430; font-variant-numeric:tabular-nums; }
  .me { color:#58a6ff; font-weight:700; } .en { color:#f85149; font-weight:700; }
  #hud .sp { flex:1; }
  #stage { position:relative; flex:1; display:flex; align-items:center; justify-content:center; touch-action:none; overflow:hidden; }
  canvas { display:block; touch-action:none; }
  #lobby, #banner { position:absolute; inset:0; display:flex; align-items:center; justify-content:center; flex-direction:column; gap:14px; background:rgba(5,8,13,.86); z-index:10; }
  #banner { display:none; }
  button { background:linear-gradient(180deg,#f2b536,#d58716); color:#2a1206; border:2px solid #8a5a13; border-radius:12px; padding:14px 26px; font:800 18px 'Noto Serif KR',serif; cursor:pointer; box-shadow:0 4px 0 #7a4e12; }
  button:active { transform:translateY(2px); box-shadow:0 2px 0 #7a4e12; }
  #lobby p { color:#8b949e; max-width:340px; text-align:center; margin:0; }
  #banner h2 { font-size:44px; margin:0; }
  #wait { color:#ffd24a; font-weight:700; font-size:16px; }
  #tip { padding:6px 12px; color:#6e7681; font-size:12px; border-top:1px solid #1c2430; }
  .chip { position:fixed; left:8px; bottom:8px; z-index:20; background:rgba(10,15,22,.85); border:1px solid #2b3543; border-radius:8px; padding:4px 9px; font:12px monospace; color:#8b949e; pointer-events:none; }
</style>
</head>
<body>
<div id="wrap">
  <div id="hud">
    <span class="me">🔵 아군 <b id="meC">-</b>성 <b id="meT">-</b></span>
    <span class="en">🔴 적 <b id="enC">-</b>성 <b id="enT">-</b></span>
    <span class="sp"></span>
    <span style="color:#8b949e">⏱ <b id="tk">0</b></span>
    <button id="surr" style="display:none;padding:5px 12px;font-size:13px;box-shadow:none;border-radius:8px">항복</button>
  </div>
  <div id="stage">
    <canvas id="cv"></canvas>
    <div id="lobby">
      <h2 style="margin:0;font-family:'Noto Serif KR',serif;color:#fff1b8">⚔ 실시간 1v1</h2>
      <p>이 페이지를 <b>두 곳</b>에서 열고 각자 <b>대전 시작</b>을 누르면 자동 매칭됩니다. (한 창 2뷰 테스트: <code>mp_game_2view.html</code>)</p>
      <button id="findBtn">대전 시작</button>
      <div id="wait" style="display:none">상대를 찾는 중…</div>
    </div>
    <div id="banner"><h2 id="bwin"></h2><button id="again" style="font-size:16px">다시</button></div>
  </div>
  <div id="tip">내 성(파랑) 탭 → 목표 성 탭 = 전 병력 출진. 상대 본진(★) 함락 시 승리.</div>
</div>
<div class="chip" id="chip"></div>

<script>
// ===== engine.js =====
${engineSrc}
// ===== netmatch.js =====
${netSrc}
// ===== 실그림 1v1 =====
(function(){
  var $=function(id){return document.getElementById(id);};
  var cv=$('cv'), ctx=cv.getContext('2d');

  // --- 자산 로드 ---
  var IMG={};
  function loadImg(key,src){ var im=new Image(); im.src=src; IMG[key]=im; }
  loadImg('bg','assets/battle/bg_battle_02_snow.jpg');
  loadImg('ally','assets/castles/castle_ally.png');
  loadImg('enemy','assets/castles/castle_enemy.png');
  loadImg('neutral','assets/castles/castle_neutral.png');
  var UNIT_C={spear:'#9fb0c4',cavalry:'#e0a54a',archer:'#5fb86a'};

  // --- 대칭 PvP 맵 ---
  function pvpMap(){
    var home=function(x,y,o,n){return {x:x,y:y,owner:o,name:n,isHome:true,primary:'spear',troops:{spear:30,cavalry:8,archer:8},size:1.3,trait:'prod'};};
    var neu=function(x,y,t,p){return {x:x,y:y,owner:0,name:'',primary:p,troops:{spear:5,cavalry:4,archer:4},size:1.0,trait:t};};
    return { world:{w:1,h:1.7}, growthMult:1.0, humanFactions:[1,2], castles:[
      home(0.5,0.90,1,'아군본진'), home(0.5,0.10,2,'적본진'),
      neu(0.5,0.50,'def','archer'),
      neu(0.24,0.66,'atk','cavalry'), neu(0.76,0.34,'atk','cavalry'),
      neu(0.76,0.66,'prod','spear'), neu(0.24,0.34,'prod','spear'),
    ]};
  }

  // --- 채널(BroadcastChannel, 다중 핸들러) ---
  function makeChannel(name){
    var bc=new BroadcastChannel(name); var hs=[];
    bc.onmessage=function(e){ for(var i=0;i<hs.length;i++) hs[i](e.data); };
    return { send:function(m){ bc.postMessage(m); }, onMessage:function(cb){ hs.push(cb); } };
  }

  // --- 상태 ---
  var role=null, host=null, guest=null, mySide=null, gmap=null, over=false, selected=-1, flip=false;
  var chan=null, qid=0, qtime=0, inQueue=false, qTimer=null;
  var STEP=1/15, acc=0, lastT=0, raf=null;

  // --- 매칭: 먼저 큐 입장(Date.now 빠른 쪽)=호스트 ---
  function startFind(){
    chan=makeChannel('samgukgi-game');
    chan.onMessage(onNet);
    qid=(Math.random()*2e9)>>>0; qtime=Date.now(); inQueue=true;
    $('findBtn').style.display='none'; $('wait').style.display='block';
    bcastQ(); qTimer=setInterval(bcastQ,350);
    keepAlive();
  }
  function bcastQ(){ if(inQueue) chan.send({t:'Q',id:qid,jt:qtime}); }
  function onNet(m){
    if(!m) return;
    if(m.t==='Q'){ onQ(m.id,m.jt); }
    else if(m.t==='START' && !role){ inQueue=false; clearInterval(qTimer); startGuest(); } // 호스트의 START 수신 → 게스트로
    // 그 외 netmatch 메시지(STATE/END/CMD)는 host/guest 객체 핸들러가 처리
  }
  function onQ(pid,pt){
    if(!inQueue || role || pid===qid) return;
    var iAmHost=(qtime<pt)||(qtime===pt && qid<pid);
    if(iAmHost){ inQueue=false; clearInterval(qTimer); startHost(); } // 먼저 온 쪽만 호스트로 확정
    // 아니면 대기 — 계속 Q 방송해서 상대가 나를 인지하게 하고, 호스트의 START를 기다림
  }
  function startHost(){
    role='host'; mySide=1;
    gmap=pvpMap();
    host=new HostMatch(gmap,(Math.random()*2e9)>>>0,chan,{hostSide:1,guestSide:2,snapEvery:1});
    host.start();
    enterGame();
    lastT=performance.now(); acc=0; loop();
  }
  function startGuest(){
    role='guest';
    guest=new GuestMatch(chan,{
      onStart:function(mm){ mySide=mm.youSide; gmap=mm.map; enterGame(); },
      onEnd:function(mm){ endBanner(mm.winner); },
    });
    guest.join();
    lastT=performance.now(); loop();
  }
  function enterGame(){
    flip = homeIsTop();     // 내 본진이 위면 화면 뒤집어 아래로
    $('lobby').style.display='none'; $('surr').style.display='inline-block';
    over=false; selected=-1; resize();
  }
  function homeIsTop(){ if(!gmap||!mySide) return false; for(var i=0;i<gmap.castles.length;i++){ var c=gmap.castles[i]; if(c.isHome && c.owner===mySide) return c.y<0.5; } return false; }

  // --- 무음 오디오 킵얼라이브(2뷰에서 비활성 창 감속 방지) ---
  function keepAlive(){ try{ if(window._ac)return; var AC=window.AudioContext||window.webkitAudioContext; if(!AC)return; var ac=new AC(); window._ac=ac; var o=ac.createOscillator(),g=ac.createGain(); g.gain.value=0.0006; o.frequency.value=40; o.connect(g); g.connect(ac.destination); o.start(); if(ac.state==='suspended')ac.resume(); }catch(_){}}
  document.addEventListener('pointerdown',function(){ if(role) keepAlive(); },true);

  // --- 좌표/렌더 소스 ---
  var pxW=1, pxH=1;
  function eng(){ return role==='host'?host.eng:null; }
  function castlesView(){
    if(role==='host') return host.eng.castles;
    if(guest && guest.snap && gmap) return gmap.castles.map(function(mc,i){ var sc=guest.snap.castles[i]; return {x:mc.x,y:mc.y,isHome:mc.isHome,size:mc.size,owner:sc?sc.owner:mc.owner,primary:sc?sc.primary:mc.primary,troops:sc?sc.troops:mc.troops,wallHP:sc?sc.wallHP:0,wallMax:gWallMax[i]||60}; });
    return [];
  }
  function armiesView(){ return role==='host'?host.eng.armies:(guest&&guest.snap?guest.snap.armies:[]); }
  var gWallMax=[];
  function computePx(){ if(role==='host'){ pxW=host.eng._pxW; pxH=host.eng._pxH; } else if(gmap){ var e=new SimEngine(gmap,0); pxW=e._pxW; pxH=e._pxH; gWallMax=e.castles.map(function(c){return c.wallMax;}); } }

  // --- 캔버스 크기 ---
  function resize(){
    var st=$('stage'); var W=st.clientWidth, H=st.clientHeight;
    var dpr=Math.min(2,window.devicePixelRatio||1);
    cv.width=W*dpr; cv.height=H*dpr; cv.style.width=W+'px'; cv.style.height=H+'px';
    ctx.setTransform(dpr,0,0,dpr,0,0); cv._W=W; cv._H=H;
  }
  window.addEventListener('resize', resize);

  // 월드→스크린 (fit + flip)
  function view(){
    computePx();
    var W=cv._W||cv.width, H=cv._H||cv.height, pad=26;
    var s=Math.min((W-pad*2)/pxW,(H-pad*2)/pxH);
    var ox=(W-pxW*s)/2, oy=(H-pxH*s)/2;
    return {s:s,ox:ox,oy:oy,W:W,H:H};
  }
  function S(v){ var wx=v.x*pxW, wy=v.y*pxH; var vv=curV; var sx=vv.ox+wx*vv.s, sy=vv.oy+wy*vv.s; if(flip){ sx=vv.W-sx; sy=vv.H-sy; } return {x:sx,y:sy}; }
  var curV=null;

  // --- 렌더 ---
  function draw(){
    curV=view();
    var W=curV.W, H=curV.H;
    ctx.clearRect(0,0,W,H);
    // 배경
    if(IMG.bg.complete && IMG.bg.naturalWidth){ ctx.globalAlpha=1; drawCover(IMG.bg,0,0,W,H); }
    else { ctx.fillStyle='#dfe7ee'; ctx.fillRect(0,0,W,H); }
    var cs=castlesView(), av=armiesView();
    // 부대(성 아래)
    for(var i=0;i<av.length;i++) drawArmy(av[i]);
    // 성
    for(var j=0;j<cs.length;j++) drawCastle(cs[j], j===selected);
    updateHUD(cs,av);
  }
  function drawCover(img,x,y,w,h){ var iw=img.naturalWidth, ih=img.naturalHeight; var r=Math.max(w/iw,h/ih); var dw=iw*r, dh=ih*r; ctx.drawImage(img, x+(w-dw)/2, y+(h-dh)/2, dw, dh); }

  function castleImg(owner){ if(owner===0) return IMG.neutral; return owner===mySide?IMG.ally:IMG.enemy; }
  function drawCastle(c, sel){
    var p=S(c); var r=Math.max(26, 34*(c.size||1)*curV.s/1.0);
    // 선택 링
    if(sel){ ctx.beginPath(); ctx.arc(p.x,p.y,r*1.15,0,Math.PI*2); ctx.strokeStyle='#ffd24a'; ctx.lineWidth=3; ctx.stroke(); }
    // 성벽 링
    var wr=c.wallMax?Math.max(0,c.wallHP/c.wallMax):1;
    ctx.beginPath(); ctx.arc(p.x,p.y,r*1.02,-Math.PI/2,-Math.PI/2+Math.PI*2*wr); ctx.strokeStyle=(ownerColor(c.owner)); ctx.lineWidth=3; ctx.stroke();
    // 스프라이트
    var im=castleImg(c.owner);
    if(im.complete && im.naturalWidth){ var d=r*2.1; ctx.drawImage(im, p.x-d/2, p.y-d/2, d, d); }
    else { ctx.beginPath(); ctx.arc(p.x,p.y,r,0,Math.PI*2); ctx.fillStyle=ownerColor(c.owner); ctx.fill(); }
    // 본진 ★
    if(c.isHome){ ctx.fillStyle=(c.owner===mySide?'#ffd24a':'#ff9db0'); ctx.font='bold '+Math.round(r*0.7)+'px system-ui'; ctx.textAlign='center'; ctx.textBaseline='middle'; ctx.fillText('★', p.x, p.y-r*1.25); }
    // 병력 라벨
    var tot=(c.troops.spear|0)+(c.troops.cavalry|0)+(c.troops.archer|0);
    labelBadge(p.x, p.y-r*0.15, tot, ownerColor(c.owner));
  }
  function labelBadge(x,y,txt,col){
    ctx.font='bold 15px system-ui'; ctx.textAlign='center'; ctx.textBaseline='middle';
    var w=ctx.measureText(txt).width+14;
    ctx.fillStyle='rgba(8,12,20,.82)'; roundRect(x-w/2,y-12,w,24,7); ctx.fill();
    ctx.strokeStyle=col; ctx.lineWidth=1.5; roundRect(x-w/2,y-12,w,24,7); ctx.stroke();
    ctx.fillStyle='#fff'; ctx.fillText(txt,x,y+1);
  }
  function roundRect(x,y,w,h,r){ ctx.beginPath(); ctx.moveTo(x+r,y); ctx.arcTo(x+w,y,x+w,y+h,r); ctx.arcTo(x+w,y+h,x,y+h,r); ctx.arcTo(x,y+h,x,y,r); ctx.arcTo(x,y,x+w,y,r); ctx.closePath(); }

  function drawArmy(a){
    var wx=a.x/pxW, wy=a.y/pxH; var p=S({x:wx,y:wy});
    var n=Math.max(1,Math.min(12, Math.ceil(a.troops/3)));
    var col=ownerColor(a.owner), uc=UNIT_C[a.unit]||'#fff';
    ctx.globalAlpha=a.dying?0.4:1;
    for(var i=0;i<n;i++){
      var ang=(i/n)*Math.PI*2 + a.x*0.01; var rr=(i===0?0:9+(i%3)*4)*curV.s/1.0*0.7+ (i? 6:0);
      var sx=p.x+Math.cos(ang)*rr, sy=p.y+Math.sin(ang)*rr*0.7;
      ctx.beginPath(); ctx.arc(sx,sy,3.4,0,Math.PI*2); ctx.fillStyle=col; ctx.fill();
      ctx.lineWidth=1.2; ctx.strokeStyle=uc; ctx.stroke();
    }
    ctx.globalAlpha=1;
    ctx.fillStyle='#fff'; ctx.font='bold 11px system-ui'; ctx.textAlign='center'; ctx.textBaseline='middle';
    ctx.strokeStyle='rgba(0,0,0,.7)'; ctx.lineWidth=3; ctx.strokeText(a.troops,p.x,p.y-14); ctx.fillText(a.troops,p.x,p.y-14);
  }
  function ownerColor(o){ return o===0?'#8b949e':(o===mySide?'#58a6ff':'#f85149'); }

  function updateHUD(cs,av){
    var enemy=mySide===1?2:1;
    var mc=cs.filter(function(c){return c.owner===mySide;}), ec=cs.filter(function(c){return c.owner===enemy;});
    var sum=function(arr,o){ return arr.reduce(function(s,c){return s+(c.troops.spear|0)+(c.troops.cavalry|0)+(c.troops.archer|0);},0)+av.filter(function(a){return a.owner===o;}).reduce(function(s,a){return s+a.troops;},0); };
    $('meC').textContent=mc.length; $('meT').textContent=sum(mc,mySide);
    $('enC').textContent=ec.length; $('enT').textContent=sum(ec,enemy);
    $('tk').textContent = role==='host'?host.eng.tick:(guest&&guest.snap?guest.snap.tick:0);
    $('chip').textContent='['+(role||'-')+'] side'+mySide+' 부대'+av.length;
  }

  // --- 루프 ---
  function loop(){
    raf=requestAnimationFrame(loop);
    var now=performance.now(); var dt=Math.min((now-lastT)/1000,0.5); lastT=now;
    if(role==='host' && !host.over){ acc+=dt; while(acc>=STEP){ host.tick(); acc-=STEP; if(host.over)break; } if(host.over&&!over) endBanner(host.eng.winner); }
    if(!over) draw();
  }

  // --- 입력 ---
  function castleAt(px,py){
    var cs=castlesView(), best=-1, bd=40*curV.s/1.0*0.9+18;
    for(var i=0;i<cs.length;i++){ var p=S(cs[i]); var d=Math.hypot(px-p.x,py-p.y); if(d<bd){bd=d;best=i;} }
    return best;
  }
  cv.addEventListener('pointerdown',function(e){
    if(over||!role) return;
    var r=cv.getBoundingClientRect();
    var px=(e.clientX-r.left), py=(e.clientY-r.top);
    var hit=castleAt(px,py); var cs=castlesView();
    if(hit<0){ selected=-1; return; }
    if(selected<0){ if(cs[hit].owner===mySide) selected=hit; }
    else if(hit===selected){ selected=-1; }
    else {
      var src=cs[selected];
      ['spear','cavalry','archer'].forEach(function(u){
        if((src.troops[u]|0)>0){
          var cmd={type:'SEND_ARMY',fromId:selected,toId:hit,unit:u};
          if(role==='host') host.hostCommand(cmd); else guest.command(cmd);
        }
      });
      selected=-1;
    }
  });

  function endBanner(winner){ over=true; var win=winner===mySide; $('bwin').textContent=win?'🏆 승리!':'💀 패배…'; $('bwin').style.color=win?'#58a6ff':'#f85149'; $('banner').style.display='flex'; }

  $('findBtn').onclick=startFind;
  $('again').onclick=function(){ location.reload(); };
  $('surr').onclick=function(){ if(role==='guest') guest.surrender(); else if(role==='host') host._forceWin(2,'surrender'); };
  resize();
})();
</script>
</body>
</html>
`;
fs.writeFileSync(path.join(root, 'mp_game.html'), html);
console.log('생성 완료: mp_game.html (' + Math.round(html.length/1024) + 'KB)');

// 2뷰 테스트 페이지도 생성
const twoView = `<!doctype html>
<html lang="ko"><head><meta charset="utf-8"><title>실시간 1v1 — 2뷰 테스트</title>
<style>html,body{margin:0;height:100%;background:#0b0f16;overflow:hidden}
.bar{height:28px;color:#ffd24a;font:12px system-ui;display:flex;align-items:center;padding:0 10px;background:#131a24;border-bottom:1px solid #263041}
.wrap{display:flex;height:calc(100vh - 29px);gap:3px;background:#263041}
iframe{flex:1;height:100%;border:0;background:#000}</style></head>
<body><div class="bar">한 창 2뷰 — 각 화면에서 '대전 시작' → 자동 매칭 (감속 없음)</div>
<div class="wrap"><iframe src="mp_game.html" allow="autoplay"></iframe><iframe src="mp_game.html" allow="autoplay"></iframe></div>
</body></html>`;
fs.writeFileSync(path.join(root, 'mp_game_2view.html'), twoView);
console.log('생성 완료: mp_game_2view.html');
