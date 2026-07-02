// tools/build_prototype_mp.mjs — prototype.html(원본 무수정)에 멀티 훅을 덧붙여 prototype_mp.html 생성.
//   방식: 전역(update/castles/armies/camX/zoom/showMsg/onCampaignButton/startStage…)을 몽키패치·인터셉트.
//   UX: 출정 → 모달[싱글 대전 / 멀티 대전(1v1)]. 멀티 → 큐 입장 → "상대방 찾는 중(취소)"
//       → 먼저 들어온 쪽=호스트, 뒤=게스트 자동배정 → 매칭 시 자동 전투 시작.
//   미러(1단계): 호스트=정상 시뮬+상태 방송, 게스트=시뮬 생략+호스트 상태를 진짜 렌더러로 그림.
//   전송=BroadcastChannel(같은 브라우저 창 2개). 이후 게스트 조작·AI오프·WebRTC로 확장.
//   실행: node tools/build_prototype_mp.mjs → prototype_mp.html
import fs from 'fs';
import path from 'path';
import { fileURLToPath } from 'url';

const root = path.dirname(path.dirname(fileURLToPath(import.meta.url)));
const src = fs.readFileSync(path.join(root, 'prototype.html'), 'utf8');

const MP = `
<!-- ===== [MP] 멀티 훅 (build_prototype_mp.mjs 주입 — prototype.html 원본 무수정) ===== -->
<style>
  /* 대전 모드 모달 — 승패 모달(showMsg) 재사용, 배지="모드" + 버튼 확대 */
  #msg[data-result="mpmode"]::before, #msg[data-result="mpwait"]::before {
    content: "모드";
    top: -24px !important; width: 138px !important; height: 74px !important;
    padding: 0 0 4px !important; border-radius: 16px !important; clip-path: none !important;
    background:
      radial-gradient(ellipse at 50% 13%, rgba(255,255,255,0.5), transparent 42%),
      linear-gradient(180deg, #ffe58d 0%, #f2b536 58%, #d58716 100%) !important;
    color: #2a1206 !important; font-size: 33px !important; letter-spacing: 6px !important; line-height: 1 !important;
    text-shadow: 0 2px 0 rgba(255,236,180,0.72) !important; border: 3px solid #2a1206 !important;
    box-shadow: 0 4px 0 #8a5a13, 0 11px 18px rgba(0,0,0,0.36), inset 0 2px 0 rgba(255,250,220,0.55), inset 0 -9px 16px rgba(80,40,4,0.18) !important;
  }
  #msg[data-result="mpwait"]::before { content: "매칭" !important; letter-spacing: 4px !important; }
  #msg[data-result="mpmode"] #msgText, #msg[data-result="mpwait"] #msgText {
    color: #f4ead3 !important; font-size: 22px !important; font-weight: 800 !important;
    line-height: 1.5 !important; margin: 6px 0 4px !important;
  }
  #msg[data-result="mpwait"] #msgText { animation: mpPulse 1.15s ease-in-out infinite !important; }
  @keyframes mpPulse { 0%,100%{opacity:.55} 50%{opacity:1} }
  #msg[data-result="mpmode"] #msgButtons, #msg[data-result="mpwait"] #msgButtons {
    display: flex !important; flex-direction: column !important; gap: 18px !important; margin-top: 14px !important;
  }
  #msg[data-result="mpmode"] #msgButtons button, #msg[data-result="mpwait"] #msgButtons button {
    min-height: 78px !important; font-size: 22px !important; font-weight: 800 !important; letter-spacing: 1px !important;
  }
</style>
<script>
(function(){
  if (window._mpInstalled) return; window._mpInstalled = true;

  // ---- 화면 에러 오버레이 (F12 없이 스샷으로 진단) ----
  function mpErr(msg){
    var box = document.getElementById('_mpErr');
    if(!box){ box=document.createElement('div'); box.id='_mpErr';
      box.style.cssText='position:fixed;right:8px;bottom:8px;max-width:48vw;max-height:42vh;overflow:auto;z-index:2147483647;background:rgba(60,8,8,.95);color:#ffd2d2;font:11px/1.4 monospace;padding:8px 10px;border:1px solid #b44;border-radius:6px;white-space:pre-wrap;box-shadow:0 4px 16px rgba(0,0,0,.6)';
      (document.body||document.documentElement).appendChild(box); }
    box.textContent = ('▶ '+msg+'\\n\\n'+box.textContent).slice(0,1400);
  }
  window.addEventListener('error', function(ev){ try{ mpErr((ev.message||'')+'  @'+String(ev.filename||'').split('/').pop()+':'+ev.lineno+':'+ev.colno); }catch(_){}});
  window.addEventListener('unhandledrejection', function(ev){ try{ mpErr('Promise: '+((ev.reason&&ev.reason.message)||ev.reason)); }catch(_){}});
  window._mpErr = mpErr;

  var BC = new BroadcastChannel('samgukgi-realmp');
  var MP = window.MP = { role:null, last:null, lastBcast:0, tx:0, rx:0, qid:null, inQueue:false, qTimer:null, peer:null };

  // ---- 상태 칩(좌하단) ----
  var chip;
  function setChip(html, color){
    if(!chip){ chip=document.createElement('div');
      chip.style.cssText='position:fixed;left:8px;bottom:8px;z-index:2147483647;background:rgba(10,15,22,.88);border:1px solid #2b3543;border-radius:8px;color:#e6edf3;font:12px system-ui;padding:5px 9px;pointer-events:none;box-shadow:0 3px 12px rgba(0,0,0,.5)';
      (document.body||document.documentElement).appendChild(chip); }
    chip.style.display='block'; chip.innerHTML=html; if(color) chip.style.color=color;
  }
  function hideChip(){ if(chip) chip.style.display='none'; }
  function closeModal(){ try{ msgShown=false; var el=document.getElementById('msg'); if(el){el.classList.remove('show'); el.style.display='none';} var bd=document.getElementById('msgBackdrop'); if(bd) bd.classList.remove('show'); }catch(_){} }

  // ---- 상태 직렬화/적용 (전역 castles/armies) ----
  MP.serialize = function(){
    return {
      c: castles.map(function(c){ return { o:c.owner, p:c.primary, w:Math.round(c.wallHP), t:[c.troops.spear|0,c.troops.cavalry|0,c.troops.archer|0], x:!!c._contested }; }),
      a: armies.map(function(a){ return { o:a.owner, u:a.unit, r:a.troops, x:Math.round(a.x), y:Math.round(a.y), s:a.seed, m:a._marchAngle, d:a.dying?1:0, fa:a.fallAngle, dt:a.deathT, dr:a._deathTroops, sh:a.shooting?1:0, st:a._start, tg:(a.target?castles.indexOf(a.target):-1) }; }),
      ck: castles.length
    };
  };
  MP.apply = function(s){
    if(!s || !castles.length) return;
    var n = Math.min(s.c.length, castles.length);
    for(var i=0;i<n;i++){ var sc=s.c[i], c=castles[i]; c.owner=sc.o; c.primary=sc.p; c.wallHP=sc.w; c.troops={spear:sc.t[0],cavalry:sc.t[1],archer:sc.t[2]}; c._contested=sc.x; }
    armies.length = 0;
    for(var j=0;j<s.a.length;j++){ var sa=s.a[j];
      armies.push({ owner:sa.o, unit:sa.u, troops:sa.r, x:sa.x, y:sa.y, seed:sa.s, _marchAngle:sa.m,
        dying:!!sa.d, fallAngle:sa.fa, deathT:sa.dt, _deathTroops:sa.dr, shooting:!!sa.sh, _start:sa.st,
        target:(sa.tg>=0?castles[sa.tg]:castles[0])||castles[0], isArmy:true, atkBonus:1 });
    }
  };

  // ---- update 몽키패치 ----
  //  호스트: 시뮬+방송은 '워커 하트비트'가 전담(포커스/가려짐 무관하게 항상 구동).
  //          rAF가 부르는 update는 시뮬을 스킵(중복 방지) → loop이 이어서 render만 수행.
  //  게스트: 시뮬 생략 + 호스트 상태 적용(진짜 렌더러로 미러).
  var _origUpdate = update;
  update = function(dt){
    if(MP.role==='host'){
      // rAF(활성 시)·워커(비활성 시) 아무나 부르되, 타임스탬프 게이트로 1회만 시뮬(중복 방지)
      var now = performance.now();
      var gap = now - (MP._lastSim||0);
      if(gap < 28) return;
      var sdt = Math.min(gap/1000, 0.1); MP._lastSim = now;
      _origUpdate(sdt);
      if(now - MP.lastBcast > 80){ MP.lastBcast = now; try{ BC.postMessage({t:'S', s:MP.serialize()}); MP.tx++; }catch(_){}}
      if((MP.tx & 15)===0) setChip('🔵 <b>호스트</b> · 방송중 (부대 '+armies.length+')', '#58a6ff');
    } else if(MP.role==='guest'){
      if(!document.body.classList.contains('in-game')){ setChip('🔴 게스트 · 인게임 아님','#f85149'); return; }
      try{ MP.apply(MP.last); }catch(err){ if(window._mpErr) window._mpErr('apply: '+(err&&err.message)); }
      // 카메라: 컷씬 무시하고 매 프레임 전체 성이 보이게 fit (게스트는 자기 시점)
      try{
        var mnx=1e9,mny=1e9,mxx=-1e9,mxy=-1e9;
        for(var _i=0;_i<castles.length;_i++){ var _px=castles[_i].x*worldPxW(), _py=castles[_i].y*worldPxH(); if(_px<mnx)mnx=_px; if(_py<mny)mny=_py; if(_px>mxx)mxx=_px; if(_py>mxy)mxy=_py; }
        if(isFinite(mnx)){ camX=(mnx+mxx)/2; camY=(mny+mxy)/2; var _bw=(mxx-mnx)+120*DPR(), _bh=(mxy-mny)+200*DPR(); var _z=Math.min(W/_bw,H/_bh); zoom=Math.min(2.2,Math.max(0.3,_z*0.92)); }
      }catch(_){}
      // 진단 칩
      var _c0 = castles[0];
      var _lc = MP.last ? MP.last.c.length : -1;
      var _mt = _c0 ? (_c0.troops.spear+_c0.troops.cavalry+_c0.troops.archer) : -1;
      setChip('🔴 게스트 rx'+MP.rx+' last성'+_lc+' 내성'+castles.length+' c0.o='+(_c0?_c0.owner:'-')+' t'+_mt, '#f85149');
    } else {
      _origUpdate(dt);
    }
  };

  // ---- 워커 하트비트: 호스트 시뮬 클럭(창 비활성/가려짐에도 계속). ~30Hz ----
  try {
    var _wk = new Worker(URL.createObjectURL(new Blob(['setInterval(function(){postMessage(1)},33)'], {type:'text/javascript'})));
    _wk.onmessage = function(){
      if(MP.role!=='host') return;
      if(!document.body.classList.contains('in-game')) return;
      if(typeof msgShown!=='undefined' && msgShown) return;
      try{ update(0); }catch(err){ if(window._mpErr) window._mpErr('host tick: '+(err&&err.message)); }  // 게이트가 중복/간격 처리
    };
  } catch(_){}

  // ---- 매칭 큐 (먼저 들어온 쪽=호스트) ----
  function pvpStageIndex(){ try{ return (typeof campaignOffset==='function') ? campaignOffset() : 0; }catch(_){ return 0; } }
  function broadcastQ(){ if(MP.inQueue) try{ BC.postMessage({t:'Q', id:MP.qid}); }catch(_){}}
  function leaveQueue(){ MP.inQueue=false; if(MP.qTimer){ clearInterval(MP.qTimer); MP.qTimer=null; } }
  // 무음 오디오 킵얼라이브 — 크롬은 오디오 재생 중인 페이지를 백그라운드에서도 감속하지 않음.
  //   (버튼 클릭=유저 제스처에서 시작해야 autoplay 정책 통과)
  function keepAlive(){
    try{
      if(MP._ac){ if(MP._ac.state==='suspended') MP._ac.resume(); return; }
      var AC = window.AudioContext || window.webkitAudioContext; if(!AC) return;
      var ac = new AC(); MP._ac = ac;
      var osc = ac.createOscillator(), g = ac.createGain();
      g.gain.value = 0.0006;                    // 사실상 무음(들리지 않음)이지만 '재생중'으로 인식됨
      osc.frequency.value = 40; osc.type='sine';
      osc.connect(g); g.connect(ac.destination); osc.start();
      if(ac.state==='suspended') ac.resume();
    }catch(_){}
  }
  // 어떤 클릭에서든 오디오 재개(정지 상태 방지) — 비활성 창 감속 방지의 핵심
  document.addEventListener('pointerdown', function(){ if(MP.role) keepAlive(); }, true);

  function enterQueue(){
    keepAlive();
    MP.qid = (Math.random()*2000000000)>>>0;
    MP.inQueue = true; MP.role=null; MP.peer=null;
    waitingModal();
    broadcastQ();
    MP.qTimer = setInterval(broadcastQ, 400);
  }
  function cancelQueue(){ leaveQueue(); MP.role=null; hideChip(); }   // 모달은 취소버튼이 닫음
  function becomeHost(peerId){
    keepAlive(); leaveQueue(); MP.role='host'; MP.peer=peerId; MP._lastSim=performance.now();
    var stage = pvpStageIndex();
    closeModal(); setChip('🔵 <b>호스트</b> · 대전 시작','#58a6ff');
    var send=function(){ try{ BC.postMessage({t:'START_MP', stage:stage, host:MP.qid, guest:peerId}); }catch(_){}};
    send(); setTimeout(send,140); setTimeout(send,380);
    selectedStage = stage; startStage();
  }
  function onPeerQ(peerId){
    if(!MP.inQueue || MP.role || peerId===MP.qid) return;
    MP.peer = peerId;
    if(MP.qid < peerId) becomeHost(peerId);   // 작은 id = 먼저 온 것으로 간주 → 호스트
    // 큰 id면 대기 → 호스트의 START_MP 수신 시 게스트로
  }
  function becomeGuest(stage){
    if(MP.role==='host') return;
    leaveQueue(); MP.role='guest';
    if(!document.body.classList.contains('in-game')){ closeModal(); setChip('🔴 <b>게스트</b> · 연결중...','#f85149'); selectedStage=stage; startStage(); }
  }

  BC.onmessage = function(e){
    var m = e.data; if(!m) return;
    if(m.t==='Q'){ onPeerQ(m.id); }
    else if(m.t==='START_MP'){ becomeGuest(m.stage); }
    else if(m.t==='S'){ MP.last = m.s; MP.rx++;
      if(MP.role==='guest' && (MP.rx & 7)===0) setChip('🔴 <b>게스트</b> · 수신중 (부대 '+m.s.a.length+')', '#f85149'); }
  };

  // ---- 모달 ----
  function deployMenu(){
    showMsg('대전 방식을 선택하세요', undefined, [
      { text:'싱글 대전', variant:'primary', action:function(){ MP.role=null; hideChip(); onCampaignButton(); } },
      { text:'멀티 대전 (1 vs 1)', variant:'secondary', action:function(){ enterQueue(); } },
    ], undefined, 'mpmode');
  }
  function waitingModal(){
    showMsg('상대방을 찾는 중입니다...', undefined, [
      { text:'취소', variant:'tertiary', action:function(){ cancelQueue(); } },
    ], undefined, 'mpwait');
  }

  // ---- 출정 버튼 캡처 인터셉트 ----
  function isDeploy(t){ return t && ((t.id==='btnCampaign'||t.id==='btnCampaign2') || (t.closest && t.closest('#btnCampaign,#btnCampaign2'))); }
  ['click','touchend'].forEach(function(type){
    document.addEventListener(type, function(e){
      if(!isDeploy(e.target)) return;
      if(typeof msgShown!=='undefined' && msgShown) return;
      e.stopImmediatePropagation(); e.preventDefault();
      deployMenu();
    }, true);
  });
})();
</script>
`;

const out = src.replace(/<\/body>\s*<\/html>\s*$/i, MP + '\n</body>\n</html>\n');
if (out === src) { console.error('경고: </body> 주입 지점을 못 찾음'); process.exit(1); }
fs.writeFileSync(path.join(root, 'prototype_mp.html'), out);
console.log('생성 완료: prototype_mp.html (원본+MP훅, ' + Math.round(out.length/1024) + 'KB)');
