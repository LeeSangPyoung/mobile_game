// tools/build_prototype_mp.mjs — prototype.html(원본 무수정)에 멀티 훅 스크립트를 덧붙여 prototype_mp.html 생성.
//   방식: 기존 전역(update/castles/armies/camX/zoom…)을 '몽키패치'만 함(소스 편집 0).
//   1단계(현재): 스펙테이터 미러 — 호스트가 실제 게임을 돌리고 상태 방송, 게스트는 진짜 렌더러로 미러.
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
  var MP = window.MP = { role:null, last:null, lastBcast:0, rx:0, tx:0 };

  // --- 작은 조작 패널 ---
  function panel(){
    var d = document.createElement('div');
    d.style.cssText = 'position:fixed;top:6px;left:50%;transform:translateX(-50%);z-index:2147483647;background:rgba(10,15,22,.9);color:#e6edf3;font:12px system-ui;padding:6px 10px;border:1px solid #2b3543;border-radius:8px;display:flex;gap:8px;align-items:center;box-shadow:0 4px 16px rgba(0,0,0,.5)';
    d.innerHTML = '<b style="color:#ffd24a">MP</b>'
      + '<button id="_mpHost" style="background:#1c2430;color:#58a6ff;border:1px solid #2b3543;border-radius:5px;padding:4px 8px;cursor:pointer">🔵 호스트</button>'
      + '<button id="_mpGuest" style="background:#1c2430;color:#f85149;border:1px solid #2b3543;border-radius:5px;padding:4px 8px;cursor:pointer">🔴 게스트(관전)</button>'
      + '<span id="_mpStat" style="color:#8b949e">두 창 모두 같은 스테이지 시작 후 역할 선택</span>';
    (document.body||document.documentElement).appendChild(d);
  }
  function stat(m){ var e=document.getElementById('_mpStat'); if(e) e.textContent=m; }

  // --- 상태 직렬화/적용 (전역 castles/armies 사용) ---
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

  // --- update 몽키패치: 호스트=정상시뮬+방송 / 게스트=시뮬생략+상태적용 ---
  var _origUpdate = update;
  update = function(dt){
    if(MP.role==='host'){
      _origUpdate(dt);
      var now = performance.now();
      if(now - MP.lastBcast > 90){ MP.lastBcast = now; try{ BC.postMessage({t:'S', s:MP.serialize()}); MP.tx++; }catch(_){}}
      if((MP.tx & 15)===0) stat('🔵 호스트 방송중 · 성'+castles.length+' 부대'+armies.length+' (송신'+MP.tx+')');
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
      if(MP.role==='guest' && (MP.rx & 15)===0) stat('🔴 게스트 수신중 · 성'+(m.s.ck)+' 부대'+m.s.a.length+' (수신'+MP.rx+')');
    }
  };

  function ready(){
    panel();
    document.getElementById('_mpHost').onclick = function(){ MP.role='host'; stat('🔵 호스트(권위) — 지금부터 이 창이 진짜 게임'); };
    document.getElementById('_mpGuest').onclick = function(){ MP.role='guest'; stat('🔴 게스트(관전) — 호스트 화면 미러'); };
  }
  if(document.readyState==='loading') document.addEventListener('DOMContentLoaded', ready); else ready();
})();
</script>
`;

// 마지막 </body> 앞에 주입
const out = src.replace(/<\/body>\s*<\/html>\s*$/i, MP + '\n</body>\n</html>\n');
if (out === src) { console.error('경고: </body> 주입 지점을 못 찾음'); process.exit(1); }
fs.writeFileSync(path.join(root, 'prototype_mp.html'), out);
console.log('생성 완료: prototype_mp.html (원본+MP훅, ' + Math.round(out.length/1024) + 'KB)');
