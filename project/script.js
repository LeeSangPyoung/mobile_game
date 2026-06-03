/* ============================================================
   三國 메인 화면 — JS 인터랙션
   - 모든 [data-click] 요소에 클릭 ripple + 토스트
   - 카드 hover 시 미세 tilt
   - 출정 버튼 클릭 시 강한 push 애니메이션
   ============================================================ */
(function () {
  'use strict';

  /* ---------- 0. atlas 이미지 사용 가능 여부 ---------- */
  function detectAtlas() {
    const root = document.documentElement;
    const probe = new Image();
    probe.onload = () => root.classList.add('atlas-ready');
    probe.onerror = () => root.classList.add('atlas-missing');
    probe.src = 'assets/ui_atlas.png';
  }
  detectAtlas();

  /* ---------- 1. 토스트 ---------- */
  const toastEl = document.getElementById('toast');
  let toastTimer = null;
  function toast(msg, dur = 1200) {
    if (!toastEl) return;
    toastEl.textContent = msg;
    toastEl.classList.add('is-show');
    clearTimeout(toastTimer);
    toastTimer = setTimeout(() => toastEl.classList.remove('is-show'), dur);
  }

  /* ---------- 2. 클릭 ripple ---------- */
  function spawnRipple(el, evt) {
    const rect = el.getBoundingClientRect();
    const x = (evt.clientX ?? rect.left + rect.width / 2) - rect.left;
    const y = (evt.clientY ?? rect.top + rect.height / 2) - rect.top;
    const size = Math.max(rect.width, rect.height);
    const r = document.createElement('span');
    r.className = 'ripple';
    r.style.width = r.style.height = size + 'px';
    r.style.left = (x - size / 2) + 'px';
    r.style.top  = (y - size / 2) + 'px';
    // 부모에 position이 정해져 있어야 하므로 inline 보장
    if (getComputedStyle(el).position === 'static') el.style.position = 'relative';
    if (getComputedStyle(el).overflow === 'visible') el.style.overflow = 'hidden';
    el.appendChild(r);
    setTimeout(() => r.remove(), 520);
  }

  /* ---------- 3. data-click 핸들러 매핑 ---------- */
  const HANDLERS = {
    'settings':     () => toast('⚙ 설정 (준비중)'),
    'mail':         () => toast('✉ 메일함 (0)'),
    'menu':         () => toast('☰ 더보기'),
    'buy-gold':     () => toast('💰 골드 충전'),
    'buy-gem':      () => toast('💎 보석 상점'),
    'pvp':          () => toast('⚔ 천하쟁패'),
    'tower':        () => toast('🏯 무한의 탑 — 120F 도전'),
    'guild':        () => toast('🛡 군단전'),
    'start':        () => onStart(),
    'nav-hero':     () => toast('🛡 장수'),
    'nav-formation':() => toast('📋 편성'),
    'nav-battle':   () => onStart(),
    'nav-territory':() => toast('🏯 영지'),
    'nav-bag':      () => toast('💼 가방'),
  };
  // 스테이지 노드 핸들러 (동적)
  const STAGE_RE = /^stage-(.+)$/;

  /* ---------- 4. 출정 버튼 동작 ---------- */
  function onStart() {
    const cta = document.getElementById('btnStart');
    if (cta) {
      cta.style.transition = 'transform 0.08s';
      cta.style.transform = 'translateY(6px) scale(0.96)';
      setTimeout(() => {
        cta.style.transform = '';
        cta.style.transition = '';
      }, 120);
    }
    const stage = document.getElementById('stageRange')?.textContent || '';
    toast(`⚔ 출정! ${stage}`);
  }

  /* ---------- 5. 글로벌 클릭 위임 ---------- */
  document.addEventListener('click', (e) => {
    const el = e.target.closest('[data-click]');
    if (!el) return;
    spawnRipple(el, e);
    const key = el.dataset.click;
    const stageMatch = STAGE_RE.exec(key);
    if (stageMatch) {
      const id = stageMatch[1];
      if (el.classList.contains('node--locked') || el.classList.contains('node-locked')) {
        toast(`🔒 스테이지 ${id} (잠김)`);
      } else {
        toast(`스테이지 ${id} 진입`);
      }
      return;
    }
    const fn = HANDLERS[key];
    if (fn) fn(); else toast(key);
  });

  /* ---------- 6. 카드 hover tilt (마우스 이동에 따라 살짝 기울임) ---------- */
  document.querySelectorAll('.mode-card, .character').forEach((card) => {
    card.addEventListener('mousemove', (e) => {
      const r = card.getBoundingClientRect();
      const cx = (e.clientX - r.left) / r.width  - 0.5;
      const cy = (e.clientY - r.top)  / r.height - 0.5;
      const max = 6; // 도(°)
      card.style.transition = 'transform 0.05s';
      card.style.transform = `perspective(400px) rotateY(${cx * max}deg) rotateX(${-cy * max}deg) translateY(-3px) scale(1.04)`;
    });
    card.addEventListener('mouseleave', () => {
      card.style.transition = '';
      card.style.transform = '';
    });
  });

  /* ---------- 7. 데모용 — 시작 시 살짝 등장 애니메이션 ---------- */
  function fadeInOnLoad() {
    const targets = [
      '.topbar', '.stage', '.side-panel', '.worldmap', '.navbar'
    ];
    targets.forEach((sel, i) => {
      const el = document.querySelector(sel);
      if (!el) return;
      el.style.opacity = '0';
      el.style.transform = 'translateY(8px)';
      el.style.transition = 'opacity 0.4s ease-out, transform 0.4s ease-out';
      setTimeout(() => {
        el.style.opacity = ''; el.style.transform = '';
      }, 60 + i * 80);
    });
  }
  fadeInOnLoad();

  /* ---------- 8. (옵션) 이미지 자동 로드 시도
        assets/{key}.png 파일이 존재하면 background-image 자동 주입.
        없으면 fallback CSS 그대로 사용.
        나중에 PNG를 /assets에 넣기만 하면 자동으로 적용됨.
     ---------- */
  function tryLoadAssets() {
    // ATLAS 적용된 요소(.atlas)는 background-image가 이미 ui_atlas.png로 셋팅되어 있으므로 skip
    document.querySelectorAll('[data-img]:not(.atlas)').forEach((el) => {
      const key = el.dataset.img;
      const url = `assets/${key}.png`;
      const probe = new Image();
      probe.onload = () => {
        el.style.backgroundImage = `url(${url})`;
        el.style.backgroundSize = 'cover';
        el.style.backgroundPosition = 'center';
        el.style.backgroundRepeat = 'no-repeat';
        // 텍스트가 있으면 살짝 가리기
        if (el.firstChild && el.firstChild.nodeType === 3) {
          // text node → keep
        }
      };
      probe.onerror = () => { /* asset 없음 — CSS placeholder 유지 */ };
      probe.src = url;
    });
  }
  tryLoadAssets();

  /* ---------- 9. 진입 로그 ---------- */
  console.log('[三國 main] 화면 로드 완료 (CSS-only placeholder)');
})();
