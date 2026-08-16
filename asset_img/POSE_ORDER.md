# 일기토 추가 동작 7컷 — 발주서

지금 duel_v2 에 **없는** 동작만 뽑는다. 공격 3종·걷기는 이미 있다.
이 7컷만 들어와도 "맞는 건지 모르겠다"는 문제가 사라진다.

## 왜 이 7컷인가

현재 게임은 피격·경직·KO 그림이 **하나도 없어서** 포즈 시트의 *포효하는 자세*를
대신 쓰고 있다. 그래서 맞아도 자세가 안 변하고, 히트스톱·화면흔들림 코드가
이미 들어가 있는데도 타격감이 안 났다. 맞는 쪽이 반응해야 때린 게 보인다.

---

## 공통 규격 (⚠ 이걸 어기면 지금 문제가 그대로 재발한다)

지금 게임이 어색한 근본 원인은 **컷마다 따로 그려져서** 키·발끝·무기 길이가
제각각인 것이다. 아래를 못박지 않으면 7컷을 더 그려도 똑같아진다.

```
캔버스        768 × 768, 배경 완전 투명 (PNG, 알파)
캐릭터 키     620px 고정          ← 컷마다 달라지면 안 된다
발끝 y좌표    700px 고정          ← 지면. 공중 동작만 예외
몸통 중심 x   384px (캔버스 중앙)  ← 넘어지는 동작만 예외
바라보는 방향  오른쪽 (레퍼런스와 동일)
```

**반드시 지킬 것**
- 1 이미지 = 1 포즈. 여러 컷을 한 장에 나열하지 말 것(지금 에셋이 그래서 잘렸다)
- 라벨·테두리·배경·바닥그림자를 그림에 굽지 말 것
- 창 길이, 망토 크기, 갑옷 디테일, 얼굴을 레퍼런스와 **동일하게** 유지
- 무기·망토가 캔버스 밖으로 나가지 않게 (잘리면 못 쓴다)

**첨부할 레퍼런스**
- `ref/zhao_yun_reference_768.png` — 규격대로 배치된 기준 이미지. 모든 생성에 첨부
- `ref/zhao_yun_reference_768_guide.png` — 기준선 표시(빨강=발끝, 파랑=중심, 노랑=머리끝). 사람 확인용

---

## 프롬프트

각 프롬프트 앞에 아래 공통 블록을 붙인다.

```
Use the attached reference image as the exact character identity and art style.
Same character: Chinese Three Kingdoms general Zhao Yun, chibi proportions,
ornate silver-and-gold armor with blue accents, white flowing cape,
long spear, white plume on helmet. Keep face, armor detail, spear length,
and cape size IDENTICAL to the reference.

Output: single character on a FULLY TRANSPARENT background, 768x768 canvas.
Character height exactly 620px, feet touching y=700, body centered at x=384.
Facing right. No text, no labels, no frame, no background, no ground shadow.
Do not draw multiple poses. One pose only.
```

### 1. `guard_ready` — 가드 자세
```
POSE: Defensive stance. Body crouched low and turned side-on, weight on the
back leg. The spear shaft is held diagonally across the chest as a barrier,
both hands gripping. Head tucked slightly, eyes forward and alert.
Cape pulled tight against the back. Compact, braced silhouette.
```

### 2. `guard_just` — 저스트가드 (튕겨내는 순간)
```
POSE: The instant of a perfect parry. Same crouched guard stance but the
spear shaft is snapped sharply outward to deflect, arms extended, torso
rotating into the block. Sparks of impact where the shaft meets the attack.
Head up, defiant expression. Cape flaring backward from the sudden motion.
```

### 3. `hurt_light` — 피격 (약)
```
POSE: Taking a light hit. Upper body recoils backward, head snapped back and
to the side, one arm flying up. Feet still planted, knees flexed absorbing
the blow. Spear still held but loose in the grip. Cape whipping forward past
the body from the backward momentum. Pained grimace.
```

### 4. `hurt_heavy` — 피격 (강타)
```
POSE: Taking a heavy hit. Whole body thrown backward and bent at the waist,
head thrown far back, both arms flung outward, spear nearly slipping from
the hand. Back foot skidding, front foot lifted off the ground. Cape torn
forward violently. Mouth open in pain. Maximum recoil.
```

### 5. `stunned` — 경직 (무방비)
```
POSE: Stunned and defenseless. Body slumped FORWARD, knees buckled and
sagging, shoulders dropped. Head hanging down, dazed half-closed eyes.
Arms limp, spear tip dragging toward the ground. Cape hanging straight down.
Off-balance, about to collapse. Clearly a defenseless opening.
```

### 6. `ko_fall` — 쓰러지는 중
```
POSE: Mid-fall after a fatal blow. Body tipped backward about 45 degrees,
feet leaving the ground, arms thrown up and back, spear flying loose out of
the hand. Head back, eyes shut. Cape streaming upward. Caught mid-air,
the moment before hitting the ground.
```

### 7. `ko_down` — 바닥에 쓰러짐
```
POSE: Collapsed on the ground, defeated. Body lying on its back/side along
the ground, limbs sprawled, head turned aside, eyes closed. The spear lies
separately on the ground beside the body. Cape spread flat underneath.
Completely still.

NOTE: this is the only pose where the body is horizontal — ignore the
"feet at y=700" rule and instead place the BODY resting on y=700.
```

---

## 받은 뒤 할 일

1. 규격 검수 — 키·발끝·중심이 맞는지 자동 확인 (안 맞으면 정규화로 보정)
2. `assets/arcade_duel/` 에 배치, `duel_v2.html` 의 `META.player` 에 연결
3. 히트스톱·화면흔들림과 물려서 타격감 확인

1번은 스크립트로 처리한다 — 생성 모델이 규격을 정확히 지키는 경우가 드물어서
발끝·키 정렬은 어차피 한 번 더 잡아야 한다.
