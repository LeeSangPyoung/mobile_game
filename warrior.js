// warrior.js — 일기토용 도트(픽셀) 기마 무장 렌더러
//
// 톤 기준: 코에이 삼국지 영걸전 계열 — 말 탄 무장이 마주 서서 겨루는 장면.
// 이미지 자산 0. 장수를 파라미터로 정의하고 '저해상도 픽셀 단위'로 그린다.
//   → 호출부가 저해상도 버퍼에 그린 뒤 imageSmoothingEnabled=false 로 확대하면 도트 아트가 된다.
//     (매끄러운 벡터로 그리면 '동그라미·네모로 만든 사람'처럼 유치해진다 — 확대가 핵심)
//
// 좌표 단위 = 아트 픽셀 1개. 원점 = 말발굽 접지선 중앙, 위쪽이 -y.
// 기마 1기 전체 높이 ≈ 36px (말 26 + 기수 상체·투구). face: +1 오른쪽 / -1 왼쪽.

// ── 팔레트 유틸 ─────────────────────────────────────────────────────────────
function hex(h) {
  const n = parseInt(h.slice(1), 16);
  return [(n >> 16) & 255, (n >> 8) & 255, n & 255];
}
function mix(h, target, amt) {
  const [r, g, b] = hex(h);
  const t = target;
  const c = (a, bb) => Math.round(a + (bb - a) * amt);
  return `rgb(${c(r, t[0])},${c(g, t[1])},${c(b, t[2])})`;
}
const lit = (h, a = .34) => mix(h, [255, 250, 235], a);
const dim = (h, a = .38) => mix(h, [18, 14, 22], a);
const OUT = '#14100e';

// ── 픽셀 프리미티브 ─────────────────────────────────────────────────────────
function P(c, x, y, w, h, col) {
  c.fillStyle = col;
  c.fillRect(Math.round(x), Math.round(y), Math.max(1, Math.round(w)), Math.max(1, Math.round(h)));
}
// 3톤 블록: 위 1px 하이라이트, 아래 1px 음영
function Blk(c, x, y, w, h, col, outline = true) {
  x = Math.round(x); y = Math.round(y); w = Math.max(1, Math.round(w)); h = Math.max(1, Math.round(h));
  if (outline) P(c, x - 1, y - 1, w + 2, h + 2, OUT);
  P(c, x, y, w, h, col);
  if (h >= 3) { P(c, x, y, w, 1, lit(col)); P(c, x, y + h - 1, w, 1, dim(col)); }
}
// 픽셀 라인(두께 w) — 다리·창·팔에 사용. 계단 픽셀이 그대로 살아야 도트 느낌이 난다.
function Line(c, x0, y0, x1, y1, w, col, outline = true) {
  const dx = x1 - x0, dy = y1 - y0;
  const n = Math.max(1, Math.ceil(Math.max(Math.abs(dx), Math.abs(dy))));
  if (outline) {
    for (let i = 0; i <= n; i++) {
      const t = i / n;
      P(c, x0 + dx * t - w / 2 - 1, y0 + dy * t - w / 2 - 1, w + 2, w + 2, OUT);
    }
  }
  for (let i = 0; i <= n; i++) {
    const t = i / n;
    const col2 = i < n * .45 ? lit(col, .18) : i > n * .8 ? dim(col, .2) : col;
    P(c, x0 + dx * t - w / 2, y0 + dy * t - w / 2, w, w, col2);
  }
}

// ── 장수 spec ───────────────────────────────────────────────────────────────
// weapon: spear(장창) | glaive(언월도) | halberd(방천화극) | sword(검) | mace(철퇴) | fan(부채)
// helmet: crown(관식) | horn(뿔) | wing(익형) | cap(전립) | scholar(학사관)
export const WARRIOR_SPECS = {
  lu_bu:       { armor:'#31353f', trim:'#c9a227', cloth:'#7d1f2b', cape:'#8e1b2a', horse:'#2f2a28', helmet:'horn',    plume:'#c9a227', weapon:'halberd', beard:'short', banner:'#c9a227', bulk:1 },
  zhang_fei:   { armor:'#463027', trim:'#b8792b', cloth:'#22303f', cape:'#2b3a4a', horse:'#1f1b1a', helmet:'horn',    plume:'#e8e2d4', weapon:'spear',   beard:'full',  banner:null,      bulk:1 },
  guan_yu:     { armor:'#1f5c3a', trim:'#c9a227', cloth:'#123a26', cape:'#17563a', horse:'#8a3a2a', helmet:'crown',   plume:'#c9a227', weapon:'glaive',  beard:'long',  banner:'#1f5c3a', bulk:1 },
  ma_chao:     { armor:'#cfd4dd', trim:'#8f98a8', cloth:'#2b3a55', cape:'#e6e9ef', horse:'#e0dcd4', helmet:'wing',    plume:'#e04b3a', weapon:'spear',   beard:'none',  banner:'#e04b3a', bulk:0 },
  zhao_yun:    { armor:'#dde2ea', trim:'#8f98a8', cloth:'#26426b', cape:'#f2f4f8', horse:'#d8d2c8', helmet:'wing',    plume:'#3f7fd0', weapon:'spear',   beard:'none',  banner:'#3f7fd0', bulk:0 },
  xu_chu:      { armor:'#54402c', trim:'#8a6a3a', cloth:'#3a2f24', cape:null,      horse:'#5a4632', helmet:'cap',     plume:null,      weapon:'mace',    beard:'short', banner:null,      bulk:2 },
  dian_wei:    { armor:'#463826', trim:'#9a7a3a', cloth:'#2f2822', cape:null,      horse:'#4a3a2a', helmet:'cap',     plume:null,      weapon:'mace',    beard:'full',  banner:null,      bulk:2 },
  taishi_ci:   { armor:'#2f4a6b', trim:'#b8a05a', cloth:'#22364d', cape:'#365a80', horse:'#6b5240', helmet:'crown',   plume:'#b8a05a', weapon:'spear',   beard:'short', banner:null,      bulk:1 },
  zhang_liao:  { armor:'#33507a', trim:'#c2b070', cloth:'#243a58', cape:'#3d5f8c', horse:'#3f342c', helmet:'crown',   plume:'#c2b070', weapon:'glaive',  beard:'short', banner:'#33507a', bulk:1 },
  huang_zhong: { armor:'#5f4c2a', trim:'#c9a227', cloth:'#3f3520', cape:null,      horse:'#7a6248', helmet:'cap',     plume:'#c9a227', weapon:'sword',   beard:'long',  banner:null,      bulk:1 },
  dong_zhuo:   { armor:'#4f3157', trim:'#c9a227', cloth:'#3a2440', cape:'#5e3a68', horse:'#453a34', helmet:'crown',   plume:'#c9a227', weapon:'sword',   beard:'full',  banner:'#c9a227', bulk:2 },
  cao_cao:     { armor:'#2b4a70', trim:'#c9a227', cloth:'#1f3450', cape:'#35618f', horse:'#2a2622', helmet:'crown',   plume:'#c9a227', weapon:'sword',   beard:'short', banner:'#c9a227', bulk:1 },
  sima_yi:     { armor:'#5a606e', trim:'#9aa0ae', cloth:'#464c58', cape:'#6a7180', horse:'#4a4a48', helmet:'scholar', plume:null,      weapon:'fan',     beard:'short', banner:null,      bulk:0 },
  zhuge_liang: { armor:'#e6e3d8', trim:'#c9c4b2', cloth:'#dcd8c8', cape:'#f2f0e6', horse:'#e8e4da', helmet:'scholar', plume:null,      weapon:'fan',     beard:'short', banner:null,      bulk:0 },
};
const FALLBACK = { armor:'#4a5162', trim:'#9aa0ae', cloth:'#39404e', cape:null, horse:'#5a4632',
  helmet:'cap', plume:null, weapon:'spear', beard:'short', banner:null, bulk:1 };
const SKIN = '#e0b088';

export function specFor(id) { return { skin: SKIN, ...FALLBACK, ...(WARRIOR_SPECS[id] || {}) }; }

// ── 포즈(리깅) ──────────────────────────────────────────────────────────────
// idle | ready | gallop | windup | strike | hurt | ko | win
function pose(state, p, t) {
  const ease = (x) => 1 - Math.pow(1 - x, 3);
  const breathe = Math.sin(t * 2.1);
  const base = {
    bodyY: 0, rear: 0, gallop: 0, lean: 0,
    torso: 0, headTilt: 0, arm: -0.55, wRot: -1.35,
    riderFall: 0, riderRot: 0, dustBurst: 0,
  };
  switch (state) {
    case 'ready':
      return { ...base, bodyY: breathe * .3, torso: .05, arm: -.85, wRot: -1.9 };
    case 'gallop': {
      const g = t * 9;
      return { ...base, gallop: g, bodyY: -Math.abs(Math.sin(g)) * 1.6,
        lean: .16, torso: .12, arm: -1.15, wRot: -2.2, dustBurst: 1 };
    }
    case 'windup': {
      const e = ease(p);
      return { ...base, bodyY: -e * .8, torso: -.22 * e, lean: -.1 * e,
        arm: -.55 - 1.15 * e, wRot: -1.35 - 1.5 * e, rear: e * .18 };
    }
    case 'strike': {
      const e = ease(Math.min(1, p * 1.4));
      return { ...base, torso: .3 * e, lean: .22 * e, rear: Math.sin(p * Math.PI) * .5,
        bodyY: -Math.sin(p * Math.PI) * 2.2,
        arm: -1.7 + 2.5 * e, wRot: -2.85 + 4.3 * e };
    }
    case 'hurt': {
      const k = Math.sin(Math.min(1, p) * Math.PI);
      return { ...base, torso: -.5 * k, headTilt: -.4 * k, lean: -.2 * k,
        arm: -.2 + .7 * k, wRot: -.7 + 1.1 * k, bodyY: -k * 1.2, rear: -k * .12 };
    }
    case 'ko': {
      const e = ease(Math.min(1, p * 1.2));
      return { ...base, rear: .55 * (1 - e * .5), riderFall: e, riderRot: -1.5 * e,
        arm: .6, wRot: 1.1, bodyY: 0 };
    }
    case 'win': {
      const h = Math.abs(Math.sin(t * 3.4));
      return { ...base, rear: .35 + h * .2, torso: -.12, arm: -2.5, wRot: -2.95,
        bodyY: -h * 1.2 };
    }
    default:
      return { ...base, bodyY: breathe * .35, arm: -.55 + breathe * .04, wRot: -1.35 };
  }
}

// ── 무기 ────────────────────────────────────────────────────────────────────
function weapon(c, kind, hx, hy, a, spec) {
  const L = { spear: 26, glaive: 22, halberd: 24, sword: 11, mace: 12, fan: 7 }[kind] || 20;
  const dx = Math.cos(a), dy = Math.sin(a);
  const tx = hx + dx * L, ty = hy + dy * L;
  if (kind === 'fan') {                                       // 부채
    for (let i = -3; i <= 3; i++) {
      const th = a + i * .2;
      Line(c, hx, hy, hx + Math.cos(th) * L, hy + Math.sin(th) * L, 1, '#f2eee0', false);
    }
    P(c, hx - 1, hy - 1, 2, 2, '#7a5c3a');
    return { tx, ty };
  }
  // 자루
  Line(c, hx - dx * L * .3, hy - dy * L * .3, tx, ty, 2, '#6b4a2a');
  const nx = -dy, ny = dx;                                    // 법선
  if (kind === 'spear') {                                     // 장창: 날 + 붉은 술
    Line(c, tx - dx * 1, ty - dy * 1, tx + dx * 5, ty + dy * 5, 2, '#dfe6f0');
    P(c, tx + dx * 5, ty + dy * 5, 1, 1, '#ffffff');
    for (let i = 0; i < 4; i++)
      P(c, tx - dx * (2 + i) + nx * (i % 2 ? 1 : -1), ty - dy * (2 + i) + ny * (i % 2 ? 1 : -1), 1, 1, '#c0392b');
  } else if (kind === 'glaive') {                             // 언월도: 초승달 날
    for (let i = 0; i < 8; i++) {
      const th = a - .95 + i * .17, r = 8 - Math.abs(i - 3.5) * .6;
      Line(c, tx, ty, tx + Math.cos(th) * r, ty + Math.sin(th) * r, 2, '#e2e9f2', i === 0);
    }
    P(c, tx - dx * 2, ty - dy * 2, 2, 2, spec.trim);
  } else if (kind === 'halberd') {                            // 방천화극: 양쪽 초승달
    Line(c, tx - dx, ty - dy, tx + dx * 6, ty + dy * 6, 2, '#dfe6f0');
    [1, -1].forEach(s => {
      for (let i = 0; i < 5; i++) {
        const r = 3 + i * .8;
        P(c, tx + nx * s * r - dx * (i * .5), ty + ny * s * r - dy * (i * .5), 2, 2, '#cfd8e4');
      }
    });
    P(c, tx - dx * 3, ty - dy * 3, 2, 2, spec.trim);
  } else if (kind === 'sword') {
    Line(c, hx, hy, tx, ty, 2, '#e2e9f2');
    Line(c, hx + nx * 2, hy + ny * 2, hx - nx * 2, hy - ny * 2, 2, spec.trim, false);
  } else if (kind === 'mace') {
    P(c, tx - 3, ty - 3, 6, 6, OUT);
    P(c, tx - 2, ty - 2, 4, 4, '#9aa0ae');
    P(c, tx - 2, ty - 2, 4, 1, lit('#9aa0ae'));
    [[-4,0],[4,0],[0,-4],[0,4]].forEach(([ox,oy]) => P(c, tx+ox-1, ty+oy-1, 2, 2, '#6c7280'));
  }
  return { tx, ty };
}

// ── 얼굴(투구 아래) ─────────────────────────────────────────────────────────
function head(c, spec, hx, hy, mood) {
  const s = spec.skin;
  P(c, hx - 4, hy - 4, 8, 9, OUT);                            // 외곽
  P(c, hx - 3, hy - 3, 6, 7, s);                              // 얼굴
  P(c, hx - 3, hy - 3, 6, 1, lit(s, .2));
  // 눈 — 도트 2px, 노려보는 각
  if (mood === 'ko') {
    P(c, hx - 3, hy - 1, 2, 1, OUT); P(c, hx + 1, hy - 1, 2, 1, OUT);
  } else if (mood === 'hurt') {
    P(c, hx - 3, hy - 1, 2, 1, '#5a2a22'); P(c, hx + 1, hy - 1, 2, 1, '#5a2a22');
    P(c, hx - 1, hy + 2, 2, 1, '#8a3a30');
  } else {
    P(c, hx - 3, hy - 1, 2, 2, '#221a14'); P(c, hx + 1, hy - 1, 2, 2, '#221a14');
    P(c, hx - 3, hy - 2, 2, 1, '#3a2c1e'); P(c, hx + 1, hy - 2, 2, 1, '#3a2c1e');   // 눈썹
    if (mood === 'yell') P(c, hx - 1, hy + 2, 3, 2, '#7a2f26');
  }
  // 수염
  if (spec.beard !== 'none') {
    const bl = spec.beard === 'long' ? 7 : spec.beard === 'full' ? 4 : 2;
    const bw = spec.beard === 'full' ? 6 : 4;
    P(c, hx - bw / 2, hy + 3, bw, bl, '#2e2418');
    P(c, hx - bw / 2, hy + 3, bw, 1, dim('#2e2418', .2));
  }
  // 투구
  const k = spec.helmet;
  if (k === 'scholar') {
    P(c, hx - 5, hy - 8, 10, 5, OUT); P(c, hx - 4, hy - 7, 8, 3, spec.cloth);
    P(c, hx - 3, hy - 10, 6, 3, OUT); P(c, hx - 2, hy - 9, 4, 2, spec.cloth);
    return;
  }
  P(c, hx - 5, hy - 7, 10, 6, OUT);
  P(c, hx - 4, hy - 6, 8, 4, spec.armor);
  P(c, hx - 4, hy - 6, 8, 1, lit(spec.armor));
  P(c, hx - 5, hy - 3, 10, 2, OUT); P(c, hx - 4, hy - 3, 8, 1, spec.trim);   // 이마 띠
  P(c, hx - 5, hy - 2, 2, 5, spec.armor); P(c, hx + 3, hy - 2, 2, 5, spec.armor);  // 볼가리개
  if (k === 'horn') {
    [1, -1].forEach(s2 => {
      for (let i = 0; i < 4; i++)
        P(c, hx + s2 * (3 + i * .8), hy - 7 - i * 1.6, 2, 2, spec.trim);
    });
  } else if (k === 'wing') {
    [1, -1].forEach(s2 => {
      for (let i = 0; i < 4; i++)
        P(c, hx + s2 * (4 + i), hy - 6 - i * .5, 2, 2, spec.trim);
    });
  } else if (k === 'crown' && spec.plume) {
    for (let i = 0; i < 5; i++) P(c, hx - 1, hy - 8 - i, 2, 2, spec.plume);
    P(c, hx - 2, hy - 13, 4, 2, spec.plume);
  } else if (k === 'cap') {
    P(c, hx - 5, hy - 8, 10, 2, dim(spec.armor, .25));
  }
}

// ── 말 ─────────────────────────────────────────────────────────────────────
function horse(c, spec, P0, face) {
  const hc = spec.horse, bulk = spec.bulk;
  const bodyW = 24 + bulk, bodyH = 9 + (bulk > 1 ? 1 : 0);
  const bodyTop = -19 - P0.bodyY;
  const rear = P0.rear;                                        // 앞다리 들기
  const g = P0.gallop;

  // 뒷다리 2개
  const legs = [[-9, .0], [-6, .5], [8, 1.6], [10, 2.1]];
  legs.forEach(([lx, ph], i) => {
    const front = i >= 2;
    let sw = P0.gallop ? Math.sin(g + ph) * .9 : 0;
    let lift = 0;
    if (front && rear > 0) { sw = -1.15 * rear; lift = 5 * rear; }
    const L = 10;
    const x0 = lx, y0 = bodyTop + bodyH - 1 - lift;
    Line(c, x0, y0, x0 + Math.sin(sw) * L * .7, y0 + Math.cos(sw) * L, 3, hc);
    P(c, x0 + Math.sin(sw) * L * .7 - 1, y0 + Math.cos(sw) * L, 3, 2, dim(hc, .5));  // 발굽
  });
  // 몸통
  const rot = -rear * .5;
  c.save();
  c.translate(0, bodyTop + bodyH / 2);
  c.rotate(rot * face * 0 + rot);       // 앞다리 들면 몸 뒤로 젖힘
  Blk(c, -bodyW / 2 - 1, -bodyH / 2, bodyW, bodyH, hc);
  P(c, -bodyW / 2 + 1, -bodyH / 2 + 2, bodyW - 3, 1, lit(hc, .18));
  // 안장 + 말갑주
  Blk(c, -3, -bodyH / 2 - 2, 9, 3, spec.cloth, false);
  P(c, -1, -bodyH / 2 - 3, 5, 1, spec.trim);
  P(c, -bodyW / 2 + 1, bodyH / 2 - 3, 6, 3, dim(spec.cloth, .2));
  // 꼬리
  for (let i = 0; i < 7; i++) {
    const w = Math.sin(i * .5 + (P0.gallop || 0)) * 1.4;
    P(c, -bodyW / 2 - 1 - i * .7 + w, -1 + i * 1.1, 2, 2, dim(hc, .35));
  }
  // 목 + 머리
  const nx0 = bodyW / 2 - 3, ny0 = -bodyH / 2 + 1;
  const nAng = -1.15 - rear * .25;
  const nL = 9;
  const hxx = nx0 + Math.cos(nAng) * nL, hyy = ny0 + Math.sin(nAng) * nL;
  Line(c, nx0, ny0, hxx, hyy, 5, hc);
  for (let i = 0; i < 6; i++) {                                // 갈기
    const t2 = i / 5;
    P(c, nx0 + (hxx - nx0) * t2 - 2, ny0 + (hyy - ny0) * t2 - 2, 2, 3, dim(hc, .55));
  }
  Blk(c, hxx - 1, hyy - 4, 7, 5, hc);                          // 머리
  P(c, hxx + 5, hyy - 1, 3, 3, dim(hc, .2));                   // 주둥이
  P(c, hxx + 1, hyy - 2, 2, 2, '#1a1614');                     // 눈
  P(c, hxx, hyy - 6, 2, 3, hc); P(c, hxx + 3, hyy - 6, 2, 3, hc);  // 귀
  if (spec.trim) P(c, hxx + 1, hyy - 5, 4, 1, spec.trim);      // 이마 장식
  // 고삐
  c.fillStyle = OUT;
  for (let i = 0; i < 7; i++) P(c, hxx - i * 1.4, hyy + 1 + i * .5, 1, 1, '#3a2a1e');
  c.restore();
  return { seatX: 1, seatY: bodyTop - 2 };
}

// ── 메인: 기마 무장 1기 ─────────────────────────────────────────────────────
// scale: 아트 픽셀 배율(1 = 기본 36px 높이). 위치 x,y는 접지선.
export function drawMounted(c, spec, o) {
  const { x, y, face = 1, state = 'idle', p = 0, t = 0, scale = 1 } = o;
  const P0 = pose(state, p, t);
  c.save();
  c.translate(Math.round(x), Math.round(y));
  c.scale(face * scale, scale);
  c.imageSmoothingEnabled = false;

  // 그림자
  P(c, -14, -1, 28, 2, 'rgba(0,0,0,0.28)');

  const seat = horse(c, spec, P0, face);

  // ── 기수 ──
  c.save();
  c.translate(seat.seatX, seat.seatY + P0.riderFall * 9);
  c.rotate(P0.torso * .6 + P0.riderRot);
  // 망토
  if (spec.cape) {
    for (let i = 0; i < 7; i++) {
      const sw = Math.sin(i * .45 + t * 3) * 1.3 + P0.lean * 4;
      P(c, -3 - i * .8 + sw, -3 + i * 1.5, 4, 3, i < 2 ? spec.cape : dim(spec.cape, .18));
    }
  }
  // 다리(등자에 걸린)
  Line(c, 0, -2, 3, 5, 3, spec.cloth);
  P(c, 3, 4, 3, 2, dim(spec.cloth, .4));
  // 상체
  Blk(c, -4, -12, 8, 11, spec.armor);
  P(c, -3, -9, 6, 1, spec.trim);                       // 흉갑 라인
  P(c, -4, -3, 8, 2, OUT); P(c, -3, -3, 6, 1, spec.trim);   // 허리띠
  [1, -1].forEach(s2 => { Blk(c, s2 > 0 ? 3 : -6, -12, 3, 4, spec.trim, false); });  // 견갑
  // 등에 깃발
  if (spec.banner) {
    Line(c, -4, -11, -7, -26, 1, '#5a4028');
    P(c, -12, -26, 6, 9, OUT); P(c, -11, -25, 4, 7, spec.banner);
    P(c, -11, -25, 4, 1, lit(spec.banner));
  }
  // 뒤팔
  Line(c, -3, -10, -3 + Math.sin(P0.arm * .6) * 6, -10 + Math.cos(P0.arm * .6) * 6, 3, spec.armor);
  // 앞팔 + 무기
  const armL = 7;
  const hx = 3 + Math.sin(P0.arm) * armL, hy = -10 + Math.cos(P0.arm) * armL;
  weapon(c, spec.weapon, hx, hy, P0.wRot, spec);
  Line(c, 3, -10, hx, hy, 3, spec.armor);
  P(c, hx - 1, hy - 1, 3, 3, spec.skin);               // 손
  // 머리
  const mood = state === 'strike' || state === 'windup' || state === 'win' ? 'yell'
    : state === 'hurt' ? 'hurt' : state === 'ko' ? 'ko' : 'idle';
  c.save();
  c.translate(0, -16);
  c.rotate(P0.headTilt);
  head(c, spec, 0, 0, mood);
  c.restore();
  c.restore();

  c.restore();
  return { pose: P0, seatY: seat.seatY };
}

// ── 참격 궤적(무기가 지나간 호) ─────────────────────────────────────────────
export function drawArc(c, o) {
  const { x, y, face = 1, p, scale = 1, color = '#dff0ff' } = o;
  const prog = Math.min(1, p * 1.35);
  const fade = Math.max(0, 1 - Math.max(0, (prog - .5) / .5));
  if (fade <= 0) return;
  c.save();
  c.translate(Math.round(x), Math.round(y));
  c.scale(face * scale, scale);
  const cy = -26, R = 24;
  const a0 = -2.6, a1 = .6;
  for (let i = 0; i < 3; i++) {
    const r = R - i * 3;
    const steps = 22;
    for (let s = 0; s <= steps * prog; s++) {
      const th = a0 + (a1 - a0) * (s / steps);
      P(c, Math.cos(th) * r, cy + Math.sin(th) * r, 2, 2,
        i === 0 ? `rgba(255,255,255,${fade})` : color);
    }
  }
  c.restore();
}

// ── 초상(대사창용) — 머리 확대 ──────────────────────────────────────────────
export function drawPortrait(c, spec, o) {
  const { x, y, scale = 4 } = o;
  c.save();
  c.translate(x, y);
  c.scale(scale, scale);
  c.imageSmoothingEnabled = false;
  Blk(c, -6, -1, 12, 8, spec.armor, false);            // 어깨
  P(c, -4, 0, 8, 1, spec.trim);
  head(c, spec, 0, -6, 'idle');
  c.restore();
}
