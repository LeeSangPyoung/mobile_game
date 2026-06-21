# 손가락삼국지 — 스토어 크리에이티브 AI 생성 프롬프트

이미지 생성 AI(Midjourney / DALL·E / Nano Banana / Stable Diffusion 등)에 그대로 넣어 쓰세요.
**대부분의 이미지 AI는 영어 프롬프트가 품질이 좋습니다.** 한글 글자(로고·카피)는 AI가 자주 깨뜨리니,
**글자는 빼고 그림만 생성 → 글자는 따로 합성**을 권장합니다(우리 빌더가 글자 합성 담당).

공통 스타일 키워드(브랜드 톤): `bright, cheerful, casual mobile game art, Korean mobile game style, chibi-proportioned heroic general, ornate gold-and-jewel armor, clean rim light, vibrant warm palette, high contrast, glossy, soft cel shading, sticker-like, no text`

공통 네거티브: `dark, gloomy, gritty, realistic photo, blood, gore, lowres, blurry, watermark, signature, extra limbs, text, letters, ugly, deformed`

---

## 1. 앱 아이콘 (512×512, 글자 없음)
```
A cheerful casual mobile game app icon, a single iconic Three Kingdoms general
(Guan Yu, long black beard, green and gold ornate armor, holding a guandao glaive),
chibi-proportioned heroic style, big confident smile-frown, dynamic hero pose,
bright warm gradient background (cream to golden orange), soft circular glow,
thick rounded gold frame border, glossy cel-shaded, sticker-like, centered,
reads clearly at small size, vibrant, high contrast, no text --ar 1:1
```
대안 장수: Lu Bu(red plume helmet, halberd), Zhao Yun(silver-blue armor, spear), Cao Cao(black-gold-purple robe).

---

## 2. 피처 그래픽 / 키 비주얼 (1024×500 가로, 글자 자리 비우기)
```
Epic yet cheerful key art banner for a casual Three Kingdoms strategy mobile game,
three chibi-proportioned heroic generals standing together in dynamic heroic poses
(center: Lu Bu with halberd; left: Cao Cao in gold-black robe; right: Zhao Yun with spear),
ornate gold-and-jewel armor, glossy cel shading, bright golden gradient background with
soft cloud-like glow and clean curved decorative shapes, warm vibrant palette, soft rim light, clean composition with empty
space on the LEFT THIRD for a logo, high contrast, sticker-like, no text --ar 2:1
```
> 좌측 1/3은 비워서 거기에 "손가락삼국지" 로고를 따로 얹습니다.

---

## 3. 스크린샷 배경/캐릭터 컷 (1080×1920 세로, 장면별)
각 스크린샷은 `밝은 배경 + 명장 일러스트 + 한글 카피(따로 합성)` 구성. AI로는 **배경+캐릭터만** 뽑으세요.

### SS1 — 명장 수집 (Value)
```
A lineup of four cheerful chibi Three Kingdoms generals standing in a row
(Cao Cao, Lu Bu, Guan Yu, Zhao Yun), ornate gold armor, heroic poses, slight height
stagger, bright golden gradient background, soft glow, glossy cel-shaded, mobile game
gacha lineup style, vibrant, no text, empty space at top for a headline --ar 9:16
```
### SS2 — 실시간 출진 (Usage)
```
One cheerful chibi Three Kingdoms general (Zhang Fei) pointing forward commanding troops,
dynamic action pose, bright blue-sky gradient background, soft motion lines, glossy
cel-shaded, casual mobile game style, vibrant, no text, room for a screenshot card --ar 9:16
```
### SS3 — 병종 상성
```
Three cheerful chibi soldiers representing spear, cavalry, archer in a rock-paper-scissors
triangle, bright green gradient background, playful icons, glossy cel-shaded, casual mobile
game infographic style, vibrant, no text --ar 9:16
```
### SS4 — 회유(귀순)
```
A cheerful chibi enemy general kneeling and joining your side with a friendly gesture,
warm orange gradient background, sparkle effects, glossy cel-shaded, casual mobile game
style, vibrant, no text --ar 9:16
```
### SS5 — 장수 강화
```
A cheerful chibi general powering up with golden star particles and aura, level-up glow,
bright purple-gold gradient background, glossy cel-shaded, casual mobile game upgrade scene,
vibrant, no text --ar 9:16
```
### SS6 — 포메이션(천지인)
```
Three cheerful chibi generals arranged in a tactical formation with 天地人 banner motifs,
bright teal gradient background, clean layout, glossy cel-shaded, casual mobile game,
vibrant, no text --ar 9:16
```
### SS7 — 방대한 콘텐츠
```
A cheerful chibi general overlooking a stylized world map with many castle markers,
bright warm gradient background, adventure feel, glossy cel-shaded, casual mobile game,
vibrant, no text --ar 9:16
```
### SS8 — 신뢰(오프라인·가벼운 플레이)
```
A cheerful chibi general giving a thumbs up with a friendly smile, clean bright mint
gradient background, rounded badge/ribbon shapes, soft circular glow, glossy cel-shaded,
casual mobile game, trustworthy and friendly, vibrant, no text, no sun rays --ar 9:16
```

---

## 한글 카피(스크린샷 헤드라인 — 글자는 합성)
1. 삼국지 200 명장을 손가락으로 지휘!
2. 탭 한 번으로 출진 — 실시간 성 점령
3. 병종 상성으로 전투력 ×1.5 (창>기>궁)
4. 회유로 적장을 내 편으로!
5. 별을 모아 장수 강화·전투력 UP
6. 천·지·인 나만의 포메이션 편성
7. 10챕터 200스테이지 + 무한모드
8. 오프라인 지원 · 가볍게 플레이

---

## 팁
- Midjourney: 끝에 `--style raw --ar 1:1`(아이콘) / `--ar 2:1`(피처) / `--ar 9:16`(스크린샷).
- 캐릭터 일관성: 같은 화풍 유지하려면 한 번 잘 나온 컷을 `--cref`(캐릭터 참조)로 재사용.
- **글자는 AI에 맡기지 말 것** — 한글이 거의 항상 깨집니다. 그림만 뽑고, 카피는 `marketing2/_work/build.py`가 합성.
- 우리 게임의 기존 200 명장 일러스트(`assets/generals/fullbody_v6_aligned/*.webp`)를 i2i(image-to-image) 참조로 넣으면 화풍이 게임과 일치합니다.
