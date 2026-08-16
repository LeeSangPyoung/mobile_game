// 2D 컷아웃 퍼펫 — 조각을 각도/위치 숫자로 움직인다.
//
// 컷 넘기기와의 차이: 프레임 사이가 전부 보간되므로 칼이 실제로 호를 그린다.
// 모든 좌표는 '아트 공간' = 원본 컷아웃 픽셀 좌표(발끝 y=ground, 원점 좌상단).
// 화면 배치는 draw() 가 마지막에 한 번만 변환한다.

export const BONES = {
  // 자식 → 부모. 부모가 돌면 자식도 딸려 간다.
  upper:    null,
  head:     'upper',
  cape:     'upper',
  legBack:  null,
  legFront: null,
};

export async function loadRig(dir, version = '') {
  // 조각 파일은 이름이 그대로라 브라우저가 옛 그림을 계속 쓴다 — 버전을 붙여 강제로 새로 받는다
  const v = version ? `?v=${encodeURIComponent(version)}` : '';
  const meta = await (await fetch(`${dir}/rig.json${v}`, { cache: 'no-cache' })).json();
  await Promise.all(meta.parts.map(p => new Promise(res => {
    const img = new Image();
    img.onload = img.onerror = () => { p.img = img; res(); };
    img.src = `${dir}/${p.file}${v}`;
  })));
  meta.byName = Object.fromEntries(meta.parts.map(p => [p.name, p]));
  return meta;
}

// ── 포즈 ────────────────────────────────────────────────────────────
// 포즈 = 뼈 이름 → 각도(도). 여기에 root 가 몸 전체의 이동·기울기·스쿼시를 담는다.
export const NEUTRAL = {
  root: { x: 0, y: 0, rot: 0, sx: 1, sy: 1 },
  upper: 0, head: 0, cape: 0, legBack: 0, legFront: 0,
};

const EASE = {
  linear: t => t,
  in:     t => t * t,
  out:    t => 1 - (1 - t) * (1 - t),
  inout:  t => t < .5 ? 2 * t * t : 1 - 2 * (1 - t) * (1 - t),
  // 때리는 동작은 앞부분이 느리고 임팩트 직전에 폭발적으로 빨라져야 한다
  snap:   t => t * t * t,
  // 되돌아올 때 살짝 지나쳤다 돌아오면 무게가 실린다
  back:   t => 1 + 2.2 * Math.pow(t - 1, 3) + 1.2 * Math.pow(t - 1, 2),
};

function lerp(a, b, t) { return a + (b - a) * t; }

function blendRoot(a, b, t) {
  const A = { ...NEUTRAL.root, ...(a || {}) }, B = { ...NEUTRAL.root, ...(b || {}) };
  return { x: lerp(A.x, B.x, t), y: lerp(A.y, B.y, t), rot: lerp(A.rot, B.rot, t),
           sx: lerp(A.sx, B.sx, t), sy: lerp(A.sy, B.sy, t) };
}

// clip: { dur: 프레임수, loop, keys: [{ t: 0..1, ease, root:{}, upper: deg, ... }] }
export function samplePose(clip, frame) {
  const keys = clip.keys;
  let t = clip.dur ? frame / clip.dur : 0;
  t = clip.loop ? t % 1 : Math.min(t, 1);

  let i = 0;
  while (i < keys.length - 2 && keys[i + 1].t <= t) i++;
  const k0 = keys[i], k1 = keys[Math.min(i + 1, keys.length - 1)];
  const span = Math.max(1e-6, k1.t - k0.t);
  const raw = Math.min(1, Math.max(0, (t - k0.t) / span));
  const e = (EASE[k1.ease] || EASE.inout)(raw);

  const pose = { root: blendRoot(k0.root, k1.root, e) };
  for (const bone in BONES) {
    pose[bone] = lerp(k0[bone] ?? 0, k1[bone] ?? 0, e);
  }
  return pose;
}

// 두 포즈를 섞는다 — 상태 전환에서 뚝 끊기지 않게
export function blendPose(a, b, t) {
  const out = { root: blendRoot(a.root, b.root, t) };
  for (const bone in BONES) out[bone] = lerp(a[bone] ?? 0, b[bone] ?? 0, t);
  return out;
}

// 추가 회전(호흡, 반동 등)을 포즈 위에 얹는다
export function addPose(pose, extra) {
  const out = { root: { ...pose.root } };
  if (extra.root) for (const k in extra.root) out.root[k] += extra.root[k];
  for (const bone in BONES) out[bone] = (pose[bone] ?? 0) + (extra[bone] ?? 0);
  return out;
}

// ── 행렬 ────────────────────────────────────────────────────────────
// [a c e; b d f] — 캔버스 setTransform 순서와 동일
const M = {
  id: () => [1, 0, 0, 1, 0, 0],
  mul: (m, n) => [
    m[0] * n[0] + m[2] * n[1], m[1] * n[0] + m[3] * n[1],
    m[0] * n[2] + m[2] * n[3], m[1] * n[2] + m[3] * n[3],
    m[0] * n[4] + m[2] * n[5] + m[4], m[1] * n[4] + m[3] * n[5] + m[5],
  ],
  // 축(px,py)을 중심으로 회전
  pivot: (px, py, deg) => {
    const r = deg * Math.PI / 180, c = Math.cos(r), s = Math.sin(r);
    return [c, s, -s, c, px - c * px + s * py, py - s * px - c * py];
  },
  apply: (m, x, y) => [m[0] * x + m[2] * y + m[4], m[1] * x + m[3] * y + m[5]],
};

// 아트 공간 안에서 각 뼈의 누적 변환을 구한다.
//
// 부호 규칙: 포즈에 적는 각도는 항상 "양수 = 바라보는 쪽으로 숙임/휘두름"이다.
// 원본 그림이 왼쪽을 보면(faces=-1) 좌우 반전이 들어가 회전이 뒤집히므로,
// 여기서 faces 를 한 번 곱해 상쇄한다 — 포즈 데이터는 방향을 신경 쓰지 않아도 된다.
export function boneMatrices(rig, pose) {
  const s = rig.faces || 1;
  const out = {};
  const resolve = name => {
    if (out[name]) return out[name];
    const part = rig.byName[name];
    // 회전축을 아트 공간 좌표로 되돌린다 (ax,ay 는 발끝 원점 기준)
    const ax = part ? part.ax + rig.width / 2 : 0;
    const ay = part ? part.ay + rig.ground : 0;
    const local = M.pivot(ax, ay, (pose[name] ?? 0) * s);
    const parent = BONES[name] ? resolve(BONES[name]) : M.id();
    return (out[name] = M.mul(parent, local));
  };
  for (const b in BONES) resolve(b);
  return out;
}

// 아트 공간 → 화면. 리그 전체를 무대 위 한 지점에 놓는다.
export function worldMatrix(rig, pose, place) {
  const { x, y, dir = 1, scale = 1 } = place, r = pose.root;
  const s = rig.faces || 1, sx = dir * s;
  let m = [1, 0, 0, 1, x + r.x * scale * dir, y + r.y * scale];
  m = M.mul(m, [sx * scale * r.sx, 0, 0, scale * r.sy, 0, 0]);
  const rr = (r.rot * s) * Math.PI / 180;
  m = M.mul(m, [Math.cos(rr), Math.sin(rr), -Math.sin(rr), Math.cos(rr), 0, 0]);
  return M.mul(m, [1, 0, 0, 1, -rig.width / 2, -rig.ground]);
}

export function markerPos(rig, mats, name) {
  const mk = rig.markers[name];
  if (!mk) return null;
  return M.apply(mats[mk.bone] || M.id(), mk.x, mk.y);
}

// ── 그리기 ──────────────────────────────────────────────────────────
// place: { x, y(발끝), dir(1|-1), scale }
export function drawRig(ctx, rig, pose, place, opts = {}) {
  const mats = opts.mats || boneMatrices(rig, pose);
  const w = worldMatrix(rig, pose, place);

  ctx.save();
  ctx.transform(w[0], w[1], w[2], w[3], w[4], w[5]);
  for (const part of rig.parts) {
    const m = mats[part.name];
    if (!m) continue;
    ctx.save();
    ctx.transform(m[0], m[1], m[2], m[3], m[4], m[5]);
    const ax = part.ax + rig.width / 2, ay = part.ay + rig.ground;
    ctx.drawImage(part.img, ax - part.px, ay - part.py);
    ctx.restore();
  }
  ctx.restore();
}

// 화면 좌표계로 옮긴 마커 위치 — 궤적/사거리 계산용
export function markerScreen(rig, pose, place, name, mats) {
  const bm = mats || boneMatrices(rig, pose);
  const mk = rig.markers[name];
  if (!mk) return null;
  const full = M.mul(worldMatrix(rig, pose, place), bm[mk.bone] || M.id());
  return M.apply(full, mk.x, mk.y);
}
