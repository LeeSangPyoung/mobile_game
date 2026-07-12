# 손가락 삼국지 — 플레이어블 광고(데모) 인수인계

> 마지막 업데이트: 2026-07 / 브랜치 `v2`
> 목적: **실제 게임 엔진으로 돌아가는 플레이어블 광고**(Google Ads 앱 캠페인 업로드용) 제작·유지

---

## 1. 결과물 (Deliverable)

| 파일 | 설명 |
|---|---|
| `mobile_game/playable/playable_ad.html` | **최종 업로드용 단일 HTML** (3.76MB, 자체완결) |
| `mobile_game/playable/game-showcase.html` | 웹 미리보기용(서버 로드 방식, 인라인 아님) |

- **스펙**: 단일 HTML ≤5MB(현 3.76MB), **네트워크 호출 0**, JS 에러 0, 소리 없음
- **미리보기 URL**:
  - 플레이어블: `https://app.wooriban.org/playable.html?ad=1`
  - 웹 데모: `https://app.wooriban.org/game-showcase.html?ad=1`
- **시나리오**: 공성(낙양) 점령 → 왼쪽 적(여포) → 오른쪽 적(동탁) → "천하통일" CTA. 아군이 항상 이기게 설계(압도적 병력). 손가락 가이드(👆)는 광고/튜토리얼 공용.

---

## 2. 구조 (어떻게 만들어지나)

플레이어블 = **`prototype.html`(실제 게임 엔진) + `inject.txt`(광고 주입 스크립트) + 인라인 자산/폰트**.

- `inject.txt` — 광고 로직 전체. `?ad=1`일 때 동작. 스테이지 정의(성/장수 배치), 손가락 가이드 상태머신, 적장 반격 출진(sallyEnemy), 로딩 오버레이, **CTA(엔드카드)**. 웹 빌드와 플레이어블 빌드가 **공유**.
- `build_playable.js` — 조립기. prototype에 다음을 적용해 단일 HTML 생성:
  1. `@font-face` → data URI (NotoSerifKR 재subset + 장식폰트 2종)
  2. `roster_200.js` 외부 스크립트 인라인
  3. **shim**(`<head>` 최상단): 이미지 `src`를 인라인 data URI로 가로채기, 매핑없는 자산은 투명픽셀, **WebSocket·fetch·XHR·Audio 차단**(네트워크 0)
  4. `inject.txt`를 `</body>` 앞 주입
  5. 최종 HTML의 모든 잔여 `assets/*` URL 일괄 치환(맵 있으면 data URI, 없으면 투명)
  - 승리배경은 **CSS 변수 `--advic`로 1벌만**(로딩+CTA 공유, 중복 인라인 방지)
- `assets_inline.json` — 인라인할 자산의 webp data URI 맵(compress.js 생성)
- `NotoSerifKR-ad.woff2` — 광고 글자만 남긴 재subset 폰트(1.79MB→314KB)

---

## 3. 재빌드 방법

```bash
cd mobile_game/playable/build
npm install                 # puppeteer-core (로컬 Chrome 필요)

# (A) 자산만 바꿨을 때 — webp 재압축
node compress.js            # → assets_inline.json 갱신 (Chrome로 webp 인코딩)

# (B) 폰트 글자셋이 바뀌었을 때 — 재subset (Python + fonttools 필요)
#   1) prototype.html+inject.txt의 모든 한글/한자를 glyphs_all.txt로 추출(수동/스크립트)
#   2) python -m fontTools.subset ../../assets/fonts/NotoSerifKR-subset.woff2 \
#        --text-file=glyphs_all.txt --output-file=NotoSerifKR-ad.woff2 \
#        --flavor=woff2 --layout-features='*' --no-hinting

# (C) 조립 (대부분 이것만 실행하면 됨)
node build_playable.js      # → ../playable_ad.html (3.76MB)

# (D) 검증 (네트워크 전면차단 하에 정상 구동 확인)
node verify_offline.js      # CTA 도달:true / JS 에러:0 / 차단 네트워크:0 여야 정상
```

환경변수 `CHROME_PATH`로 Chrome 경로 지정 가능. 기본값은 `C:\Program Files\Google\Chrome\Application\chrome.exe`.

---

## 4. 핵심 기술결정 · 함정 (꼭 읽을 것)

1. **장수 얼굴 = `war_v6` 아이콘** — 배지가 그리는 얼굴은 `generals/faces/`가 아니라
   `generals/face_icons/war_v6_halfbody_style_transparent/{id}_war_face_icon_v6_cute50.png` (200명 전부 V6).
   `battleFaceIconSrc()` 참고. compress.js는 주요 장수(faces/ 보유 id) 54명분 war_v6를 인라인.
   → **얼굴이 빈 원으로 나오면** 등장 장수 id의 war_v6가 맵에 없는 것. 그 id를 추가 인라인.
   (매핑없는 자산은 shim이 투명픽셀 반환 → 로드 성공하므로 엔진의 faces/ 폴백이 안 터짐에 주의)

2. **network-0 필수** — Google Ads 플레이어블 정책. shim이 이미지/WS/fetch/XHR/Audio를 전부 차단.
   `verify_offline.js`로 항상 확인(차단 네트워크 0이어야 함).

3. **`showTutoDrag`는 광고·본게임 튜토리얼 공용** — prototype.html의 이 함수 수정 시 광고에 딸려감.
   광고 전용 동작은 `if (window._adMode) return;`로 막을 것. `_adMode`는 inject.txt 상단에서 `AD||SHOW`로 설정.

4. **구형 안드로이드 웹뷰 호환** — `?.`·`??`·`ctx.roundRect` 직접호출 금지(성 안그려짐/멀티먹통). prototype.html에 roundRect 폴리필 + 문법 치환 적용돼 있음.

5. **CTA 문구** — 별점(★) 넣지 말 것(가짜 평점). 특징 칩: 방대한 시나리오 / 장수 수집·강화 / **실시간 멀티·친구대전**(금색 강조).

---

## 5. 배포

플레이어블은 원래 웹서버에 올려 **폰 미리보기**용으로도 서빙 중:
```
pscp playable_ad.html   game@192.168.254.137:/workspace/public/playable.html
pscp game-showcase.html game@192.168.254.137:/workspace/public/game-showcase.html
```
(서버는 cloudflared 터널 app.wooriban.org → localhost:8080)

**UI 변경은 웹에만 배포, APK 빌드 생략**(유저가 웹으로 확인) — 단 구형호환 등 치명버그 수정은 AAB 재빌드.

---

## 6. Google Ads 등록 (현황)

**등록처 = Google Ads 앱 캠페인**(AdMob 콘솔 아님). 여기 올린 플레이어블이 AdMob 네트워크에 전면광고로 노출됨.

사전준비 점검(2026-07 기준):
- ✅ **앱 Play 스토어 게시** — "손가락 삼국지 : 실시간 전략 대전" (`com.leesp.samgukgi`)
- ✅ **설치 전환추적** — 앱 연결 시 Google Play 설치가 자동 추적(Firebase 불필요). 설치수 캠페인 즉시 가능
- ⚠️ **인앱 이벤트 추적(Firebase/GA4)** — 미설정(`google-services.json` 없음). "설치 후 행동" 최적화 원할 때만 필요
- ❓ **Google Ads 계정** — 유저 확인 필요

절차: 새 캠페인 → 앱 프로모션 → Android/앱 연결 → 지역 한국·언어 한국어·예산 → 소재에 HTML5(플레이어블) 업로드 → 게시.
**주의**: HTML5(플레이어블) 소재는 계정에 지출 이력이 있거나 Google Ads 지원 요청으로 활성화해야 하는 경우가 많음. 신규 계정은 텍스트+이미지+동영상으로 먼저 돌린 뒤 HTML5 요청이 현실적.

---

## 7. TODO (다음 작업 후보)

- [ ] Google Ads 계정/앱 연결 후 HTML5 업로드 (필요 시 index.html로 rename + ZIP)
- [ ] 소재 텍스트(헤드라인·설명) 초안
- [ ] Exit API/mraid 호환 보강(구글 외 네트워크까지 클릭→스토어 보장)
- [ ] (선택) Firebase 연동 → 설치 후 행동 최적화
- [ ] 얼굴 누락 장수 발견 시 compress.js에 해당 id war_v6 추가

---

## 파일 맵 (`playable/build/`)

| 파일 | 역할 |
|---|---|
| `inject.txt` | 광고 주입 스크립트(핵심 소스) |
| `build_playable.js` | 조립기 → `../playable_ad.html` |
| `compress.js` | 자산 webp 재압축 → `assets_inline.json` |
| `verify_offline.js` | 오프라인 self-contained 검증 |
| `assets_inline.json` | 인라인 자산 data URI 맵(생성물) |
| `NotoSerifKR-ad.woff2` | 재subset 폰트(생성물) |
| `glyphs_all.txt` | 폰트 subset용 글자셋 |
| `gen_ids.json` | 광고 등장 장수 id(참고) |
| `package.json` | 의존성(puppeteer-core) |
