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

// 살짝씩 어긋나게 — 같은 소리가 정확히 반복되면 무엇을 합성하든 '기계'로 들린다.
// 결투 10초에 스윙이 40번 넘게 난다. 이 흔들림이 없으면 그것만으로 깡통이다.
const jit = (v, amt = .07) => v * (1 + (Math.random() * 2 - 1) * amt);

// 쇳소리 — 고Q 밴드패스를 통과한 **잡음**의 공진이다.
//
// 예전엔 사인파 다섯 개를 비조화 배음비로 쌓고 0.3~0.6초 울렸다. 그건
// 쇠가 아니라 **깡통을 숟가락으로 친 소리**다 — 순음이 오래 남으면 귀는
// 그걸 '통(筒)'으로 듣는다. 게다가 이게 스윙과 타격에도 얹혀 있어서,
// 결투 내내 깡통 소리가 깔렸다.
//
// 진짜 칼 부딪는 소리에는 지속되는 음정이 없다. 넓은 잡음이 몇 개의
// 공진점에서 순간적으로 도드라졌다가 100ms 안에 사라진다. 그래서 잡음을
// 좁은 필터에 통과시킨다 — 금속의 '밝음'만 남고 '통'은 남지 않는다.
// 그리고 이 소리는 이제 **쇠끼리 부딪을 때(가드·합)만** 쓴다.
function clang(t0, { peak = .40, decay = .10, q = 18,
                     freqs = [2600, 4100, 6300, 9200] } = {}) {
  freqs.forEach((f, i) => {
    const src = noise();
    const flt = ctx.createBiquadFilter();
    flt.type = 'bandpass';
    flt.Q.value = q * (1 - i * .12);
    flt.frequency.setValueAtTime(jit(f, .05), t0);
    const g = ctx.createGain();
    const amp = peak / (i + 1.2);
    const d = Math.max(.03, decay * (1 - i * .18));
    g.gain.setValueAtTime(0.0001, t0);
    g.gain.exponentialRampToValueAtTime(Math.max(.0002, amp), t0 + .0015);
    g.gain.exponentialRampToValueAtTime(0.0001, t0 + d);
    src.connect(flt); flt.connect(g); g.connect(master);
    src.start(t0); src.stop(t0 + d + .04);
  });
}

export const SFX = {
  // 칼을 휘두르는 바람소리. 기술이 무거울수록 낮고 길다.
  swing(kind = 'light') {
    if (!ctx || muted) return;
    const t = now();
    // 휘두르는 건 **공기를 가르는 소리**다. 음정이 있으면 안 된다.
    // 칼이 우는 소리(clang)는 뭔가에 부딪혔을 때만 난다 — 허공을 가를 땐
    // 나지 않는다. 예전엔 스윙마다 쇳소리를 얹어서, 헛치든 맞든 늘
    // '깡' 하고 울렸다.
    if (kind === 'thrust') {
      // 찌르기: 짧고 날카롭다. 칼끝이 한 점을 뚫고 지나간다.
      whoosh(t, { dur: jit(.11), f0: 1100, fPeak: jit(4400), f1: 2100, peak: .30, q: 7 });
      noiseHit(t + .02, { type: 'highpass', f0: 7000, f1: 3400, q: 1,
                          peak: .13, attack: .002, decay: .045 });
    } else if (kind === 'heavy') {
      // 강베기: 큰 날이 무겁게 돈다. 저역이 실려야 '무겁다'가 읽힌다.
      whoosh(t, { dur: jit(.30), f0: 190, fPeak: jit(1150), f1: 170, peak: .52, q: 1.6 });
      tone(t + .02, { freq: jit(74), to: 38, peak: .20, attack: .03, decay: .30, type: 'triangle' });
    } else {
      // 베기: 가로로 훑고 지나간다.
      whoosh(t, { dur: jit(.17), f0: 620, fPeak: jit(3100), f1: 480, peak: .38, q: 3.2 });
    }
  },

  hit(heavy = false) {
    if (!ctx || muted) return;
    const t = now();
    // 칼이 몸에 들어가는 소리다. 쇳소리를 얹으면 안 된다 — 살은 울지 않는다.
    // 저역 충격(무게) + 베이는 잡음(살) + 아주 짧은 고역 어택(칼끝) 세 겹.
    tone(t, { freq: heavy ? jit(78) : jit(118), to: heavy ? 30 : 46,
              peak: heavy ? 1.0 : .70, attack: .002, decay: heavy ? .34 : .20 });
    noiseHit(t + .004, { type: 'bandpass', f0: heavy ? 1400 : 1900, f1: 260, q: 1.1,
                         peak: heavy ? .52 : .34, attack: .003,
                         decay: heavy ? .17 : .085 });
    noiseHit(t, { type: 'highpass', f0: 6200, f1: 2600, q: 1,
                  peak: heavy ? .22 : .15, attack: .0015, decay: .04 });
    // 강타에만 배 속을 치는 저역을 하나 더 — 이게 '크게 맞았다'를 만든다
    if (heavy) tone(t + .01, { freq: 52, to: 26, peak: .55, attack: .01, decay: .48 });
  },

  // 가드 — 금속끼리 부딪히는 짧고 단단한 소리
  guard(crush = false) {
    if (!ctx || muted) return;
    const t = now();
    // 여기가 쇳소리가 나야 할 자리다 — 칼이 칼(또는 방패)에 막힌 순간.
    // 짧게 끊는다. 길게 울리면 그 순간 깡통으로 돌아간다.
    clang(t, { peak: crush ? .58 : .42, decay: crush ? .13 : .085,
               q: crush ? 14 : 20 });
    tone(t, { freq: crush ? jit(190) : jit(300), to: 110,
              peak: crush ? .30 : .18, attack: .002, decay: .07, type: 'triangle' });
    if (crush) tone(t + .008, { freq: 64, to: 30, peak: .42, attack: .006, decay: .30 });
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
    // 合 — 한 판에 몇 번 안 나는 소리다. 여기서만 좀 길게 울려도 된다.
    // 두 번 겹쳐 친다: 날이 맞부딪는 순간 + 되튕기며 우는 여운.
    clang(t, { peak: .62, decay: .17, q: 16, freqs: [2900, 4600, 7000, 10500] });
    clang(t + .035, { peak: .30, decay: .26, q: 24, freqs: [3400, 5300, 8100] });
    tone(t, { freq: 240, to: 96, peak: .26, attack: .002, decay: .09, type: 'triangle' });
  },

  // 카운트다운 — 3·2·1 은 낮고 짧은 나무 타격음, FIGHT 는 위로 뻗는 신호.
  // 숫자가 같은 소리면 셋이 그냥 반복으로 들린다. 음을 조금씩 올려
  // '다가온다'를 만든다(392 → 440 → 494Hz).
  count(step = 0) {          // 0,1,2 = 3,2,1
    if (!ctx || muted) return;
    const t = now();
    const f = [392, 440, 494][step] || 392;
    tone(t, { freq: f, to: f * .5, peak: .34, attack: .003, decay: .16, type: 'triangle' });
    noiseHit(t, { type: 'bandpass', f0: 2400, f1: 900, q: 4, peak: .16, decay: .05 });
  },
  // 시작 — 낮은 데서 위로 뻗고 쇳소리가 한 번 갈린다
  go() {
    if (!ctx || muted) return;
    const t = now();
    const o = ctx.createOscillator();
    o.type = 'sawtooth';
    o.frequency.setValueAtTime(180, t);
    o.frequency.exponentialRampToValueAtTime(720, t + .18);
    const g = ctx.createGain();
    g.gain.setValueAtTime(0.0001, t);
    g.gain.exponentialRampToValueAtTime(.30, t + .02);
    g.gain.exponentialRampToValueAtTime(0.0001, t + .34);
    const flt = ctx.createBiquadFilter();
    flt.type = 'lowpass'; flt.frequency.setValueAtTime(2600, t);
    o.connect(flt); flt.connect(g); g.connect(master);
    o.start(t); o.stop(t + .40);
    clang(t + .02, { peak: .50, decay: .16, q: 15, freqs: [2800, 4400, 6800] });
    tone(t, { freq: 92, to: 40, peak: .52, attack: .004, decay: .34 });
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
