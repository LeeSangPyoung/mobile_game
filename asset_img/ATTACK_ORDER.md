# 조운 공격 10컷 — ChatGPT 발주 지침

## 왜 한 번에 하나씩인가

10컷을 한 장에 요구하면 **크기가 제각각으로 나온다.** 지금 게임이 어색한 원인이
바로 그것이고, 이미 두 번 겪었다. 한 번에 하나씩 뽑으면 각 컷의 품질과 프레이밍을
통제할 수 있고, 어긋나도 그 컷 하나만 다시 뽑으면 된다.

## 진행 방법

1. **ChatGPT 대화 하나를 새로 연다.** 10컷을 전부 그 대화 안에서 뽑는다.
   대화가 바뀌면 캐릭터가 변한다.
2. 첫 메시지에 **레퍼런스 이미지를 첨부**한다.
   → `asset_img/조운/zhao_yun_states_green.png` (초록 배경 7컷짜리)
   지금 게임에 들어간 가드·피격 포즈가 이 그림이라, 여기에 맞춰야 의상이 안 바뀐다.
3. 아래 **[고정 블록]** 을 먼저 한 번 보낸다.
4. 그다음 **[포즈 01] ~ [포즈 10]** 을 하나씩 순서대로 보낸다.
   한 번에 하나. 답으로 이미지가 나오면 다음 것을 보낸다.
5. 결과가 이상하면 그 자리에서 "다시" 라고 하거나, 아래 [수정 요청문] 을 쓴다.

## 파일 정리

받은 이미지를 `asset_img/조운/` 에 넣는다. 파일명은 순서만 알 수 있으면 된다.
(`01.png`, `02.png` … 또는 다운로드된 이름 그대로. 순서만 알려주면 된다.)

---

# [고정 블록] — 맨 처음 한 번만

```
You are helping me produce game sprite art for a Three Kingdoms mobile game.

The attached image is my CHARACTER REFERENCE: Zhao Yun, chibi proportions,
silver-and-gold ornate armor with blue accents, cream-white flowing cape,
a long spear with a blue-glowing blade, white plume on the helmet.

I will ask you for 10 poses, ONE AT A TIME. For every single one of them,
these rules apply without exception:

1. ONE character in ONE pose. Never a grid, never a sheet, never variations.
2. Background: solid pure green (#00FF00). Completely flat. No gradient,
   no texture, no vignette, no ground, no shadow.
3. Square image. The character is centered horizontally, standing on the
   lower part of the frame, and the FULL BODY occupies about 80% of the
   frame height. Use this same framing for every pose so all 10 come out
   at the same size.
4. Nothing cropped. The spear tip, the spear butt, and the cape must all
   be fully inside the frame with clear green margin around them.
5. Character only. No slash trails, no motion blur, no impact sparks,
   no dust, no text, no labels, no borders.
6. Facing right.
7. Identical costume every time: same face, same helmet plume, same armor
   pattern, same cape shape and size, same spear length and blade glow.

Confirm you understand, then wait for my first pose request.
```

---

# 포즈 10개 — 하나씩 보낼 것

각 포즈는 아래 문장 그대로 보내면 된다. 앞에 아무 말도 붙이지 않아도 된다.

### [포즈 01] 중립 대기 → `idle`
```
Pose 1 of 10 — NEUTRAL IDLE.
Standing ready in a side-on combat stance. Weight evenly balanced, knees
slightly bent. The spear is held diagonally across the body with both hands,
tip angled forward and down. Calm, alert, watching the opponent.
This is the resting pose the character returns to between attacks.
Apply all the rules from my first message.
```

### [포즈 02] 베기 예비 → `slash_windup`
```
Pose 2 of 10 — SLASH WINDUP.
The spear is pulled back over the rear shoulder, held in both hands. The
torso is coiled away from the target, weight shifted onto the back leg,
front foot light. Wound up like a spring, not yet released.
Apply all the rules from my first message.
```

### [포즈 03] 베기 타격 → `slash_impact`
```
Pose 3 of 10 — SLASH IMPACT.
The spear has been swept forward through a HORIZONTAL arc and is now at
full extension in front of the character. The torso has rotated fully into
the swing, arms extended, front foot planted hard on the ground.
The single frame of maximum force.
Apply all the rules from my first message.
```

### [포즈 04] 베기 후딜 → `slash_recovery`
```
Pose 4 of 10 — SLASH RECOVERY.
Immediately after the swing. The spear has travelled past the target and
is now low and across the far side of the body. The torso is over-rotated,
balance not yet regained, guard open. Vulnerable.
Apply all the rules from my first message.
```

### [포즈 05] 찌르기 예비 → `thrust_windup`
```
Pose 5 of 10 — THRUST WINDUP.
The spear is drawn straight back beside the hip, both hands gripping the
shaft, elbow behind the body. The stance is compressed and low, shoulders
squared toward the target, aiming forward. Coiled, about to explode forward.
Apply all the rules from my first message.
```

### [포즈 06] 찌르기 타격 → `thrust_impact`
```
Pose 6 of 10 — THRUST IMPACT.
A deep forward lunge. The spear is driven straight forward at maximum
reach, arms fully extended. The back leg is stretched out far behind, the
front knee deeply bent. Body, arms and spear form one straight line
pointing forward. The longest-reaching pose of all 10.
Apply all the rules from my first message.
```

### [포즈 07] 찌르기 후딜 → `thrust_recovery`
```
Pose 7 of 10 — THRUST RECOVERY.
Pulling the spear back after the lunge. The front leg is still forward and
the body is still extended, but the arms are drawing in and the weight is
settling back. Still over-committed and open.
Apply all the rules from my first message.
```

### [포즈 08] 강베기 예비 → `heavy_windup`
```
Pose 8 of 10 — HEAVY WINDUP.
The spear is raised HIGH OVERHEAD with both hands, the body stretched
upward and leaning back, chest open, heels rising. The biggest, most
obvious wind-up of all the attacks — the opponent should be able to read
it from across the arena.
Apply all the rules from my first message.
```

### [포즈 09] 강베기 타격 → `heavy_impact`
```
Pose 9 of 10 — HEAVY IMPACT.
The spear has been smashed DOWNWARD through a vertical arc and the blade
is now near the ground in front of the character. The body has dropped into
a deep crouch, both arms driving down, every bit of weight committed to
the blow. The heaviest pose of all 10.
Apply all the rules from my first message.
```

### [포즈 10] 강베기 후딜 → `heavy_recovery`
```
Pose 10 of 10 — HEAVY RECOVERY.
Just after the heavy blow landed. The spear tip rests on the ground, the
body is bent forward over it, shoulders heaving, slow to straighten up.
Completely open — this is the punish window.
Apply all the rules from my first message.
```

---

# [수정 요청문] — 결과가 어긋났을 때

**크기가 다르게 나왔을 때**
```
The character came out at a different size from the previous pose.
Redraw it so the full body occupies about 80% of the frame height,
exactly like the earlier poses. Same framing, same distance.
```

**창이나 망토가 잘렸을 때**
```
The spear tip is cut off at the edge of the frame. Redraw with more green
margin around the character so the entire spear and cape are inside.
```

**의상이 바뀌었을 때**
```
The armor and spear changed. Go back to the exact costume in my reference
image: silver-and-gold armor with blue accents, cream-white cape,
blue-glowing spear blade, white plume. Same face.
```

**배경이 단색이 아닐 때**
```
The background has a gradient. It must be one flat solid green (#00FF00),
completely uniform, with no shading or texture anywhere.
```

**이펙트가 그려져 나왔을 때**
```
Remove the slash trail and impact effects. I need the character only —
the effects are added by the game engine.
```

---

# 보내기 전 체크리스트

10장이 모이면 아래만 확인하면 된다. 하나라도 어긋나면 그 컷만 다시 뽑으면 된다.

- [ ] 배경이 전부 같은 초록 단색인가
- [ ] 10장의 캐릭터 크기가 서로 비슷한가 (눈대중으로 충분)
- [ ] 창끝·물미·망토가 잘린 컷이 없는가
- [ ] 의상이 10장 모두 같은가 (특히 망토 색, 창날 발광)
- [ ] 참격 이펙트가 그려진 컷이 없는가

크기는 내가 마지막에 한 번 더 맞춘다. 다만 **너무 크게 어긋나면 보정이 티가 나므로**,
눈에 띄게 다른 컷은 다시 뽑는 편이 낫다.
