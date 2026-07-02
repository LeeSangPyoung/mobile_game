// tools/build_prototype_mp.mjs — prototype.html(원본 무수정)에 멀티 훅을 덧붙여 prototype_mp.html 생성.
//   방식: 전역(update/castles/armies/camX/zoom/showMsg/onCampaignButton…)을 몽키패치·인터셉트만 함.
//   UX: 출정 → showMsg 모달[싱글 대전 / 멀티 대전] → (멀티) 호스트/게스트.
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
<script>
(function(){
  if (window._mpInstalled) return; window._mpInstalled = true;
  var BC = new BroadcastChannel('samgukgi-realmp');
  var MP = window.MP = { role:null, last:null, lastBcast:0, tx:0, rx:0 };

  // ---- 상태 칩(좌하단, 역할 선택 후 표시) ----
  var chip;
  function setChip(html, color){
    if(!chip){ chip=document.createElement('div');
      chip.style.cssText='position:fixed;left:8px;bottom:8px;z-index:2147483647;background:rgba(10,15,22,.88);border:1px solid #2b3543;border-radius:8px;color:#e6edf3;font:12px system-ui;padding:5px 9px;pointer-events:none;box-shadow:0 3px 12px rgba(0,0,0,.5)';
      (document.body||document.documentElement).appendChild(chip); }
    chip.style.display='block'; chip.innerHTML=html; if(color) chip.style.color=color;
  }
  function hideChip(){ if(chip) chip.style.display='none'; }

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

  // ---- update 몽키패치: 호스트=정상시뮬+방송 / 게스트=시뮬생략+상태적용 / 그외=원본 ----
  var _origUpdate = update;
  update = function(dt){
    if(MP.role==='host'){
      _origUpdate(dt);
      var now = performance.now();
      if(now - MP.lastBcast > 90){ MP.lastBcast = now; try{ BC.postMessage({t:'S', s:MP.serialize()}); MP.tx++; }catch(_){}}
      if((MP.tx & 7)===0) setChip('🔵 <b>호스트</b> · 방송중 (부대 '+armies.length+')', '#58a6ff');
    } else if(MP.role==='guest'){
      if(!document.body.classList.contains('in-game')) return;
      MP.apply(MP.last);
      camX += (window._targetCamX - camX)*0.15;
      camY += (window._targetCamY - camY)*0.15;
      zoom += (window._targetZoom - zoom)*0.1;
    } else {
      _origUpdate(dt);
    }
  };
  BC.onmessage = function(e){
    var m = e.data; if(!m) return;
    if(m.t==='S'){ MP.last = m.s; MP.rx++;
      if(MP.role==='guest' && (MP.rx & 7)===0) setChip('🔴 <b>게스트</b> · 수신중 (부대 '+m.s.a.length+')', '#f85149'); }
  };

  // ---- 출정 → 대전 방식 선택 모달 (showMsg = 튜토리얼 팝업과 동일 스타일) ----
  function deployMenu(){
    showMsg('⚔ 출정 — 대전 방식을 선택하세요', undefined, [
      { text:'싱글 대전 (캠페인)', variant:'primary', action:function(){ MP.role=null; hideChip(); onCampaignButton(); } },
      { text:'멀티 대전 (실시간 1v1)', variant:'secondary', action:function(){ multiMenu(); } },
    ], undefined, undefined);
  }
  function multiMenu(){
    showMsg('🌐 멀티 대전 — 역할을 선택하세요', undefined, [
      { text:'🔵 방 만들기 (호스트)', variant:'primary', action:function(){ MP.role='host'; setChip('🔵 <b>호스트</b> 준비 — 스테이지를 시작하세요','#58a6ff'); goToStageSelect(); } },
      { text:'🔴 참가하기 (게스트·관전)', variant:'secondary', action:function(){ MP.role='guest'; setChip('🔴 <b>게스트</b> 준비 — 호스트와 같은 스테이지를 시작','#f85149'); goToStageSelect(); } },
      { text:'← 뒤로', variant:'tertiary', action:function(){ deployMenu(); } },
    ], undefined, undefined);
  }

  // ---- 출정 버튼(btnCampaign/btnCampaign2)을 캡처 단계에서 가로채 우리 모달로 ----
  function isDeploy(t){ return t && ((t.id==='btnCampaign'||t.id==='btnCampaign2') || (t.closest && t.closest('#btnCampaign,#btnCampaign2'))); }
  ['click','touchend'].forEach(function(type){
    document.addEventListener(type, function(e){
      if(!isDeploy(e.target)) return;
      if(typeof msgShown!=='undefined' && msgShown) return; // 모달 떠있으면 무시
      e.stopImmediatePropagation(); e.preventDefault();
      deployMenu();
    }, true); // capture: 원본 bindTap 핸들러보다 먼저 잡아 차단
  });
})();
</script>
`;

const out = src.replace(/<\/body>\s*<\/html>\s*$/i, MP + '\n</body>\n</html>\n');
if (out === src) { console.error('경고: </body> 주입 지점을 못 찾음'); process.exit(1); }
fs.writeFileSync(path.join(root, 'prototype_mp.html'), out);
console.log('생성 완료: prototype_mp.html (원본+MP훅, ' + Math.round(out.length/1024) + 'KB)');
