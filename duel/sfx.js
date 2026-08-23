// 일기토 효과음 — 파일 없이 WebAudio 로 합성한다.
//
// 왜 합성인가: 타격음은 '타이밍'이 전부다. 파일을 받아 쓰면 로딩·디코딩 지연이
// 붙고 용량도 늘어난다. 여기서 필요한 소리(쇳소리·바람·둔탁한 충격)는 전부
// 노이즈와 사인파 몇 개로 만들 수 있어서, 지연 0에 용량 0이다.
//
// 볼륨 규칙: 유효타 > 가드 > 헛스윙. 소리 크기가 곧 '중요도'라서
// 이 순서가 뒤집히면 무슨 일이 일어났는지 귀로 구분이 안 된다.

let ctx = null, master = null, muted = false;

export function init() {
  if (ctx) return ctx;
  const AC = window.AudioContext || window.webkitAudioContext;
  if (!AC) return null;
  ctx = new AC();
  master = ctx.createGain();
  master.gain.value = 0.9;
  master.connect(ctx.destination);
  return ctx;
}

// 브라우저는 사용자 조작 전에는 소리를 막는다 — 결투 시작 버튼에서 부른다
export function resume() { init(); if (ctx && ctx.state === 'suspended') ctx.resume(); }
export function setMuted(v) {
  muted = !!v;
  if (master) master.gain.value = muted ? 0 : 0.9;
  if (bgm) bgm.volume = muted ? 0 : 0.32;   // 음소거 버튼 하나로 BGM 까지
}
export function isMuted() { return muted; }

const now = () => ctx.currentTime;

// 짧은 잡음 버퍼 — 쇳소리·바람·파편의 재료
let noiseBuf = null;
function noise() {
  if (!noiseBuf) {
    const n = ctx.sampleRate * 0.5;
    noiseBuf = ctx.createBuffer(1, n, ctx.sampleRate);
    const d = noiseBuf.getChannelData(0);
    for (let i = 0; i < n; i++) d[i] = Math.random() * 2 - 1;
  }
  const src = ctx.createBufferSource();
  src.buffer = noiseBuf;
  src.loop = true;
  return src;
}

function env(node, t0, peak, attack, decay) {
  const g = ctx.createGain();
  g.gain.setValueAtTime(0.0001, t0);
  g.gain.exponentialRampToValueAtTime(Math.max(0.0002, peak), t0 + attack);
  g.gain.exponentialRampToValueAtTime(0.0001, t0 + attack + decay);
  node.connect(g);
  return g;
}

// 필터를 통과한 잡음 — 쇳소리/바람의 기본형
function noiseHit(t0, { peak = .5, attack = .004, decay = .18,
                        type = 'bandpass', f0 = 2200, f1 = 700, q = 3 } = {}) {
  const src = noise();
  const flt = ctx.createBiquadFilter();
  flt.type = type; flt.Q.value = q;
  flt.frequency.setValueAtTime(f0, t0);
  flt.frequency.exponentialRampToValueAtTime(Math.max(60, f1), t0 + attack + decay);
  src.connect(flt);
  env(flt, t0, peak, attack, decay).connect(master);
  src.start(t0); src.stop(t0 + attack + decay + .05);
}

// 휘두르는 바람소리 — 필터 주파수를 올렸다 내리며 도플러처럼 스쳐 지나간다.
// 짧은 노이즈 버스트(noiseHit)만 쓰면 '틱' 소리로만 들린다 — 공격할 때마다
// 울리는 소리라 이게 게임 전체의 인상을 정한다.
function whoosh(t0, { peak = .5, dur = .26, f0 = 400, fPeak = 2600, f1 = 300, q = 4 } = {}) {
  const src = noise();
  const flt = ctx.createBiquadFilter();
  flt.type = 'bandpass'; flt.Q.value = q;
  flt.frequency.setValueAtTime(f0, t0);
  flt.frequency.exponentialRampToValueAtTime(fPeak, t0 + dur * 0.42);
  flt.frequency.exponentialRampToValueAtTime(Math.max(60, f1), t0 + dur);
  const g = ctx.createGain();
  g.gain.setValueAtTime(0.0001, t0);
  g.gain.exponentialRampToValueAtTime(peak * 0.35, t0 + dur * 0.14);
  g.gain.exponentialRampToValueAtTime(peak, t0 + dur * 0.48);   // 스쳐 지나가는 정점
  g.gain.exponentialRampToValueAtTime(0.0001, t0 + dur);
  src.connect(flt); flt.connect(g); g.connect(master);
  src.start(t0); src.stop(t0 + dur + .05);
}

// 사인/삼각 톤 — 충격의 '무게'를 담당한다
function tone(t0, { freq = 160, to = 60, peak = .5, attack = .004, decay = .22, type = 'sine' } = {}) {
  const o = ctx.createOscillator();
  o.type = type;
  o.frequency.setValueAtTime(freq, t0);
  o.frequency.exponentialRampToValueAtTime(Math.max(20, to), t0 + attack + decay);
  env(o, t0, peak, attack, decay).connect(master);
  o.start(t0); o.stop(t0 + attack + decay + .05);
}

// ── 실제로 쓰는 소리들 ───────────────────────────────────────────
// 쇳소리 — 칼날이 우는 소리. 노이즈만 쓰면 '쉭/픽' 같은 바람소리로만 들린다.
// 금속은 배음이 정수배가 아니라(비조화) 여러 부분음이 제각각 감쇠한다.
// 그 비율을 흉내내야 '쇠'로 들린다.
function metal(t0, { f = 1900, peak = .30, decay = .40, spread = 1, parts = [1, 1.52, 2.13, 2.87, 3.61] } = {}) {
  parts.forEach((r, i) => {
    const o = ctx.createOscillator();
    o.type = 'sine';
    const fr = f * (1 + (r - 1) * spread);
    o.frequency.setValueAtTime(fr, t0);
    o.frequency.exponentialRampToValueAtTime(Math.max(40, fr * 0.86), t0 + decay);
    const g = ctx.createGain();
    const amp = peak / (i + 1.35);              // 높은 부분음일수록 작게
    const d = decay * (1 - i * 0.14);           // 그리고 빨리 죽는다
    g.gain.setValueAtTime(0.0001, t0);
    g.gain.exponentialRampToValueAtTime(Math.max(0.0002, amp), t0 + .004);
    g.gain.exponentialRampToValueAtTime(0.0001, t0 + Math.max(.05, d));
    o.connect(g); g.connect(master);
    o.start(t0); o.stop(t0 + decay + .06);
  });
}

export const SFX = {
  // 칼을 휘두르는 바람소리. 기술이 무거울수록 낮고 길다.
  swing(kind = 'light') {
    if (!ctx || muted) return;
    const t = now();
    // 세 기술이 귀로 구분돼야 한다 — 무엇을 눌렀는지 화면을 안 봐도 알게.
    if (kind === 'thrust') {
      // 찌르기: 짧고 높고 곧다. 칼끝이 공기를 가르며 '치잉' 하고 선다.
      whoosh(t, { dur: .13, f0: 900, fPeak: 5200, f1: 1800, peak: .26, q: 9 });
      metal(t + .01, { f: 3200, peak: .26, decay: .30, spread: .8 });
    } else if (kind === 'heavy') {
      // 강베기: 낮고 길다. 큰 날이 무겁게 돌며 '우웅' 하고 운다.
      whoosh(t, { dur: .34, f0: 260, fPeak: 1300, f1: 220, peak: .50, q: 2 });
      metal(t + .05, { f: 900, peak: .34, decay: .62, spread: 1.15 });
      tone(t, { freq: 132, to: 42, peak: .24, attack: .02, decay: .34, type: 'triangle' });
    } else {
      // 베기: 그 사이. 가로로 훑고 지나가며 '쉬잉' 하고 남는다.
      whoosh(t, { dur: .20, f0: 500, fPeak: 3000, f1: 420, peak: .36, q: 3.5 });
      metal(t + .02, { f: 1900, peak: .28, decay: .40 });
    }
  },

  hit(heavy = false) {
    if (!ctx || muted) return;
    const t = now();
    // 세 겹으로 쌓는다 — 저역 충격(북) + 중역 몸통(살) + 고역 쇳소리(칼).
    // 예전엔 톤 하나 + 노이즈 하나뿐이라 휘두르는 소리에 묻혔다.
    tone(t, { freq: heavy ? 96 : 150, to: heavy ? 34 : 52,
              peak: heavy ? 1.0 : .72, attack: .002, decay: heavy ? .40 : .24 });
    noiseHit(t, { type: 'lowpass', f0: heavy ? 900 : 1200, f1: 160, q: .8,
                  peak: heavy ? .60 : .38, decay: heavy ? .20 : .12 });
    noiseHit(t + .006, { type: 'highpass', f0: 5200, f1: 1800, q: 1.2,
                         peak: heavy ? .40 : .26, decay: heavy ? .16 : .10 });
    // 맞는 순간에도 쇠가 운다 — 살만 때리는 둔탁한 소리로는 칼싸움이 안 된다
    metal(t + .008, { f: heavy ? 1200 : 2200, peak: heavy ? .30 : .20,
                      decay: heavy ? .55 : .30, spread: heavy ? 1.2 : .9 });
  },

  // 가드 — 금속끼리 부딪히는 짧고 단단한 소리
  guard(crush = false) {
    if (!ctx || muted) return;
    const t = now();
    noiseHit(t, { type: 'bandpass', f0: 3400, f1: 1600, q: 6,
                  peak: crush ? .5 : .34, decay: crush ? .2 : .12 });
    tone(t, { freq: crush ? 220 : 320, to: 120, peak: .22, decay: .1, type: 'square' });
  },

  // 저스트가드 — 맑고 높게. 성공했다는 신호는 확실히 달라야 한다.
  just() {
    if (!ctx || muted) return;
    const t = now();
    for (const [f, d] of [[1760, .5], [2640, .34], [3520, .2]]) {
      const o = ctx.createOscillator();
      o.type = 'sine'; o.frequency.setValueAtTime(f, t);
      env(o, t, d * .5, .003, .5).connect(master);
      o.start(t); o.stop(t + .6);
    }
    noiseHit(t, { type: 'highpass', f0: 6000, f1: 3000, peak: .3, decay: .25 });
  },

  // 칼이 맞부딪힘(합)
  clash() {
    if (!ctx || muted) return;
    const t = now();
    noiseHit(t, { type: 'bandpass', f0: 5200, f1: 2200, q: 9, peak: .5, decay: .3 });
    noiseHit(t + .02, { type: 'bandpass', f0: 3800, f1: 1500, q: 7, peak: .3, decay: .22 });
  },

  // 경직 — 아래로 미끄러지는 톤. '무너졌다'가 귀로 읽힌다.
  stun() {
    if (!ctx || muted) return;
    const t = now();
    tone(t, { freq: 520, to: 90, peak: .34, attack: .01, decay: .55, type: 'triangle' });
  },

  // KO — 낮은 폭발 + 긴 여운
  ko() {
    if (!ctx || muted) return;
    const t = now();
    tone(t, { freq: 110, to: 28, peak: 1, attack: .003, decay: .9 });
    noiseHit(t, { type: 'lowpass', f0: 900, f1: 120, q: .7, peak: .6, decay: .8 });
  },

  // 발소리 — 아주 작게. 없으면 걷는 게 미끄러지는 느낌이 난다.
  step() {
    if (!ctx || muted) return;
    noiseHit(now(), { type: 'lowpass', f0: 700, f1: 180, q: .8, peak: .1, decay: .07 });
  },

  // 몸이 부딪힘 — 낮고 둔탁하게. 금속이 아니라 '몸'이라 고음이 없다.
  bump() {
    if (!ctx || muted) return;
    const t = now();
    tone(t, { freq: 96, to: 44, peak: .30, attack: .004, decay: .14, type: 'sine' });
    noiseHit(t, { type: 'lowpass', f0: 520, f1: 140, q: .7, peak: .18, decay: .1 });
  },

  // 서로 밀며 비비는 소리 — 접촉이 이어지는 동안 아주 작게
  scrape() {
    if (!ctx || muted) return;
    noiseHit(now(), { type: 'bandpass', f0: 1100, f1: 620, q: 2, peak: .07, decay: .09 });
  },

  // 대시 — 짧게 스치는 바람
  dash() {
    if (!ctx || muted) return;
    noiseHit(now(), { type: 'bandpass', f0: 900, f1: 2600, q: 1.5, peak: .16, decay: .16 });
  },
};

// ── 배경음 ──────────────────────────────────────────────────────────
// 효과음은 WebAudio 로 합성하지만 BGM 은 파일이다 — 합성으로 3분짜리 곡을
// 만들 수는 없다. assets/audio/battle_qazijamjam.mp3 (CC0, OpenGameArt).
// 효과음이 묻히지 않게 기본 볼륨을 0.32 로 낮게 잡았다.
let bgm = null;
export function bgmStart(src = './assets/audio/battle_qazijamjam.mp3', vol = 0.32) {
  try {
    if (!bgm) {
      bgm = new Audio(src);
      bgm.loop = true;
      bgm.preload = 'auto';
    }
    bgm.volume = muted ? 0 : vol;
    // 이미 재생 중이면 건드리지 않는다 — 라운드마다 처음으로 되감으면 거슬린다
    if (bgm.paused) bgm.play().catch(() => {});
  } catch {}
}
export function bgmState() { return bgm ? { src: bgm.src.split('/').pop(), paused: bgm.paused, vol: bgm.volume } : null; }
export function bgmStop(fade = 500) {
  if (!bgm || bgm.paused) return;
  const v0 = bgm.volume, t0 = performance.now();
  const step = () => {
    const k = Math.min(1, (performance.now() - t0) / fade);
    bgm.volume = v0 * (1 - k);
    if (k < 1) requestAnimationFrame(step); else { bgm.pause(); bgm.currentTime = 0; }
  };
  step();
}
