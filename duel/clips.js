// 동작 정의 — 그림이 아니라 숫자다.
//
// 각도 단위는 도(°). 부호 규칙은 하나뿐이다: **양수 = 바라보는 쪽(전방)**.
// 그림이 왼쪽을 보든 오른쪽을 보든 rig.js 가 알아서 뒤집으므로 여기선 신경 쓰지 않는다.
//
// head 는 upper 의 자식이라 상체 회전을 물려받는다. 그래서 head 값은 대개
// upper 와 **반대 부호**다 — 몸이 숙어도 시선은 상대를 향해야 하기 때문이다.
// (여기를 같은 부호로 주면 목이 꺾인다.)
//
// t 는 0..1 정규화 시간, dur 는 60fps 프레임 수 — duel_v2 프레임 데이터와 같은 단위.
// ease 가 손맛이다: snap = 임팩트 직전 폭발 가속, back = 살짝 지나쳤다 되돌아옴.

export const CLIPS = {
  idle: {
    loop: true, dur: 150,
    keys: [
      { t: 0,  root: { y: 0 },    upper: 0,    head: 0,   cape: 0,  legBack: 0, legFront: 0 },
      { t: .5, root: { y: -3 },   upper: -1.4, head: .8,  cape: -6, legBack: 0, legFront: 0 },
      { t: 1,  root: { y: 0 },    upper: 0,    head: 0,   cape: 0,  legBack: 0, legFront: 0 },
    ],
  },

  // 걷기 — 다리를 번갈아 흔들고 몸통이 위아래로 눌린다.
  // 컷 6장으로는 안 나오던 접지감이 여기서 나온다.
  walk: {
    loop: true, dur: 44,
    keys: [
      { t: 0,   root: { y: 0,  rot: 1.2 },  upper: 1.5, head: -1, cape: -12, legBack: -13, legFront: 12 },
      { t: .25, root: { y: -5 },            upper: 0,   head: 0,  cape: -4,  legBack: 0,   legFront: 0 },
      { t: .5,  root: { y: 0,  rot: -1.2 }, upper: 1.5, head: -1, cape: -16, legBack: 12,  legFront: -11 },
      { t: .75, root: { y: -5 },            upper: 0,   head: 0,  cape: -5,  legBack: 0,   legFront: 0 },
      { t: 1,   root: { y: 0,  rot: 1.2 },  upper: 1.5, head: -1, cape: -12, legBack: -13, legFront: 12 },
    ],
  },

  // ── 공격 3종. duel_v2 의 startup/active/recovery 를 그대로 쓴다 ──
  // 다리는 거의 안 돌린다: 엉덩이를 축으로 크게 돌리면 발이 지면에서 떠 버린다.
  // 전진은 회전이 아니라 root.x 로 만든다.

  // 베기 8/4/13 = 25f — 가볍고 빠르게
  light: {
    dur: 25,
    keys: [
      { t: 0,   root: { x: 0 },                                  upper: 0,   head: 0,  cape: 0 },
      { t: .32, root: { x: -16, y: 4, rot: -7, sy: .96 }, ease: 'out',
                                                                 upper: -10, head: 6,  cape: 20, legBack: -6, legFront: 4 },
      { t: .48, root: { x: 40, y: -2, rot: 11 }, ease: 'snap',   upper: 13,  head: -8, cape: -34, legFront: 20, legBack: -14 },
      { t: .62, root: { x: 36, rot: 9 },                         upper: 11,  head: -7, cape: -26, legFront: 17, legBack: -12 },
      { t: 1,   root: { x: 0 },   ease: 'back',                  upper: 0,   head: 0,  cape: 0 },
    ],
  },

  // 찌르기 13/5/19 = 37f — 몸을 통째로 앞으로 던진다. 이동 거리가 가장 크다.
  thrust: {
    dur: 37,
    keys: [
      { t: 0,   root: { x: 0 },                                    upper: 0,  head: 0,   cape: 0 },
      { t: .30, root: { x: -26, y: 8, rot: -9, sy: .93 }, ease: 'out',
                                                                   upper: -7, head: 5,   cape: 26, legBack: -10, legFront: 8 },
      { t: .43, root: { x: 88, y: 2, rot: 16, sx: 1.05 }, ease: 'snap',
                                                                   upper: 9,  head: -11, cape: -46, legFront: 34, legBack: -26 },
      { t: .58, root: { x: 84, rot: 15, sx: 1.04 },                upper: 8,  head: -10, cape: -36, legFront: 32, legBack: -24 },
      { t: 1,   root: { x: 0 },   ease: 'back',                    upper: 0,  head: 0,   cape: 0 },
    ],
  },

  // 강베기 21/6/26 = 53f — 크게 감았다가 온몸으로 내려친다.
  // 회전은 골반(upper)이 아니라 **발끝(root.rot)** 이 주력이다. 몸을 통째로 기울이면
  // 허리가 꺾이지 않으면서도 동작이 커 보인다 — 상체만 돌리면 20°만 넘어도 몸이 눕는다.
  // .28~.40 이 거의 정지: 이 '멈춤'이 상대가 읽는 예고(telegraph)다.
  heavy: {
    dur: 53,
    keys: [
      { t: 0,   root: { x: 0 },                                     upper: 0,   head: 0,   cape: 0 },
      { t: .28, root: { x: -40, y: 12, rot: -17, sy: .90 }, ease: 'out',
                                                                    upper: -14, head: 12,  cape: 44, legBack: -14, legFront: 12 },
      { t: .40, root: { x: -44, y: 14, rot: -19, sy: .89 },         upper: -15, head: 13,  cape: 40, legBack: -16, legFront: 13 },
      { t: .51, root: { x: 62, y: -6, rot: 22, sy: 1.03 }, ease: 'snap',
                                                                    upper: 15,  head: -16, cape: -54, legFront: 30, legBack: -22 },
      { t: .60, root: { x: 58, y: -2, rot: 20 },                    upper: 13,  head: -14, cape: -44, legFront: 27, legBack: -20 },
      { t: .80, root: { x: 24, rot: 8 },                            upper: 5,   head: -5,  cape: -14, legFront: 10, legBack: -8 },
      { t: 1,   root: { x: 0 },   ease: 'back',                     upper: 0,   head: 0,   cape: 0 },
    ],
  },

  // 가드 — 몸을 웅크리고 창대를 세운다
  guard: {
    loop: true, dur: 90,
    keys: [
      { t: 0,  root: { x: -7, y: 2, sy: .97 }, upper: -7, head: 6, cape: 10 },
      { t: .5, root: { x: -7, y: 0, sy: .97 }, upper: -5, head: 5, cape: 6 },
      { t: 1,  root: { x: -7, y: 2, sy: .97 }, upper: -7, head: 6, cape: 10 },
    ],
  },

  // ── 피격 / 경직 / KO 는 성격이 완전히 달라야 한다 ──────────────
  // 피격 = 짧고 날카롭다(찔끔 밀림, 바로 복귀)
  // 경직 = 길고 늘어진다(앞으로 무너지며 고개가 떨어짐, 무한 반복)
  // KO   = 뒤로 넘어가 바닥에 눕고 그대로 멈춘다
  // 셋을 같은 톤으로 만들면 화면에서 구별이 안 된다.

  // 피격 — 22f. 한 번 튕기고 끝. 뒤로 크게 밀린다.
  hurt: {
    dur: 22,
    keys: [
      { t: 0,   root: { x: 0 },                            upper: 0,   head: 0,   cape: 0 },
      { t: .16, root: { x: -38, y: -6, rot: -11 }, ease: 'out',
                                                           upper: -26, head: -20, cape: 46, legBack: 12, legFront: -16 },
      { t: .40, root: { x: -24, rot: -7 },                 upper: -17, head: -13, cape: 30, legBack: 8,  legFront: -10 },
      { t: 1,   root: { x: 0 },  ease: 'back',             upper: 0,   head: 0,   cape: 0 },
    ],
  },

  // 경직 — 무방비. 앞으로 무너지며 고개가 떨어지고, 중심을 못 잡고 느리게 흔들린다.
  // 피격과 반대 방향(앞으로)이라 한눈에 구별된다.
  stunned: {
    loop: true, dur: 78,
    keys: [
      { t: 0,   root: { x: 4,  y: 8, rot: 7,  sy: .93 }, upper: 16, head: 22, cape: -12, legBack: 6,  legFront: -8 },
      { t: .35, root: { x: -6, y: 11, rot: -5, sy: .91 }, upper: 11, head: 26, cape: 14, legBack: -7, legFront: 9 },
      { t: .68, root: { x: 8,  y: 7, rot: 9,  sy: .94 }, upper: 18, head: 20, cape: -16, legBack: 9,  legFront: -6 },
      { t: 1,   root: { x: 4,  y: 8, rot: 7,  sy: .93 }, upper: 16, head: 22, cape: -12, legBack: 6,  legFront: -8 },
    ],
  },

  // KO — 뒤로 넘어가 바닥에 눕는다. 마지막 자세에서 멈춘다(되돌아오지 않는다).
  ko: {
    dur: 46,
    keys: [
      { t: 0,   root: { x: 0, rot: 0 },                            upper: 0,   head: 0,   cape: 0 },
      { t: .22, root: { x: -20, y: -14, rot: -18 }, ease: 'out',   upper: -26, head: -16, cape: 44, legFront: -18 },
      { t: .55, root: { x: -46, y: -6, rot: -52 },  ease: 'in',    upper: -18, head: -22, cape: 30, legBack: -16, legFront: -28 },
      { t: 1,   root: { x: -78, y: 6, rot: -86 },   ease: 'out',   upper: -6,  head: -30, cape: 10, legBack: -26, legFront: -34 },
    ],
  },
};

// 공격의 판정 구간 — duel_v2 프레임 데이터와 1:1 대응
export const ATTACK_PHASES = {
  light:  { startup: 8,  active: 4, recovery: 13 },
  thrust: { startup: 13, active: 5, recovery: 19 },
  heavy:  { startup: 21, active: 6, recovery: 26 },
};
