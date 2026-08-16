# 일기토 장수 규격 (초안)

장수 200명을 일기토에 넣으려면 "장수 한 명 = 폴더 하나"가 되어야 한다.
지금은 한 명에 30분씩 손이 가서 넘어가지 못하고 있다. 이 문서는 그 손을
없애기 위한 규격이다.

---

## 1. 지금 무엇이 막고 있나

장수 한 명을 추가할 때 실제로 드는 일:

| 항목 | 현재 | 상태 |
|---|---|---|
| 포즈 17컷 (webp) | 시트 2장 생성 → 도구 2번 | 자동 |
| `poses.json` (몸높이·창끝) | 도구가 기록 | 자동 |
| **리그 조각 5개 + 폴리곤 좌표** | **사람이 격자 보고 좌표 입력** | **수작업 · 최대 병목** |
| `CHAR_FEET` (발 중심·폭) | 픽셀 세어서 상수 입력 | 수작업 |
| `CHAR_SIZE` (체격 배율) | 눈대중 | 수작업 |
| 에셋 경로 17줄 + `POSE_SET` 등록 | 코드 편집 | 수작업 |
| 아우라 색 (무기 종류별) | 코드 편집 | 수작업 |

**리그가 병목의 뿌리다.** 리그는 걷기 그림이 없어서 만든 대체물이었다.
걷기를 그림으로 받으면 리그 자체가 사라지고, 그와 함께 폴리곤 수작업도 사라진다.

---

## 2. 목표 상태

```
assets/arcade_duel/generals/<장수id>/
    manifest.json      ← 체격·무기종류·발위치 등 (도구가 생성)
    poses.json         ← 몸높이·창끝 좌표     (도구가 생성)
    idle.webp  walk1.webp  walk2.webp  walk3.webp
    slash_windup.webp  slash_impact.webp  slash_recovery.webp
    thrust_windup.webp thrust_impact.webp thrust_recovery.webp
    heavy_windup.webp  heavy_impact.webp  heavy_recovery.webp
    guard_ready.webp   guard_just.webp
    hurt_light.webp    hurt_heavy.webp
    stunned.webp  ko_fall.webp  ko_down.webp
```

= **20컷.** 폴더를 떨구면 게임이 알아서 읽는다. **코드 편집 0줄.**

---

## 3. 발주 규격 (변경점)

기존 [POSE_ORDER.md](../asset_img/POSE_ORDER.md) · [ATTACK_ORDER.md](../asset_img/ATTACK_ORDER.md) 에
아래 세 가지를 추가한다.

### 3-1. 걷기 3컷을 반드시 포함 — 리그를 없애는 조건

```
walk1  앞발이 지면에 닿는 순간 (뒷발은 떠 있다)
walk2  두 발이 지나치는 중간 (몸이 가장 높다)
walk3  뒷발이 지면에 닿는 순간 (walk1 의 반대)
```

### 3-2. 대기 자세에서 무기를 지면에 닿게 하지 말 것

발 위치 자동 검출이 실패한 유일한 원인이다. 화웅의 도끼날이 바닥에 닿아 있어서
그것이 발로 잡혔고, 그림자가 발이 아닌 도끼 아래에 찍혔다.
**대기 자세만** 이 조건을 지키면 발 검출이 100% 자동화된다.

```
In the IDLE pose only: the weapon must NOT touch the ground.
Keep the blade/tip clearly above the floor line.
```

### 3-3. 체격을 문장으로 명시

`CHAR_SIZE` 를 눈대중으로 정하지 않기 위해, 발주서에 체급을 적는다.
도구가 이 값을 manifest 에 그대로 넣는다.

```
거구(여포·화웅·전위)      1.14
장신(관우·조운·마초)      1.05
표준(대다수)             1.00
단신·문관(제갈량·순욱)    0.92
```

---

## 4. 자동화해야 할 것 (구현 대기)

### 4-1. `tools/make_general.py` — 한 방에 처리

```
python3 tools/make_general.py --id zhao_yun --size 1.05 --weapon spear \
        asset_img/조운/*.png
```

내부 동작:
1. `split_pose_sheet.py` — 시트별 컷 분리·정렬·창끝 추출
2. `harmonize_poses.py` — 시트 간 크기 통일, 몸높이 기록
3. **발 위치 자동 측정** (3-2 규칙이 지켜지면 신뢰 가능)
4. `manifest.json` 출력 — id·체격·무기종류·발위치·포즈 목록

### 4-2. 게임 쪽: 하드코딩 → manifest 로더

지금 `ASSET_SRC` / `POSE_SET` / `POSE_KEY` / `CHAR_SIZE` / `CHAR_FEET` 에
장수 정보가 흩어져 있다. 이걸 하나로 모은다.

```js
const g = await loadGeneral('zhao_yun');   // manifest + 포즈 + 좌표를 한 번에
makeFighter({ general: g, stats: ROSTER[id] });
```

무기 종류(`spear`/`axe`/`sword`/`halberd`)로 아우라 색이 결정되므로
색 지정도 코드에서 사라진다.

### 4-3. 리그 제거

걷기 3컷이 들어오면:
- `duel/rig.js` · `clips.js` · `build_duel_rig.py` · `assets/duel_rig/` 삭제
- `rigClipFor()` / `drawRigPose()` 삭제

리그는 "그림이 없을 때의 임시방편"이었다. 그림이 생기면 없애는 게 맞다.
(단, 조운·화웅은 리그가 이미 돌아가므로 걷기 컷이 확보될 때까지 유지)

---

## 5. 검증 (장수마다 자동으로 돌릴 것)

`make_general.py` 가 아래를 확인하고 실패하면 경고한다.
지금까지 실제로 터진 문제들이라 전부 근거가 있다.

| 검사 | 왜 |
|---|---|
| 컷 개수 = 20 | 시트 분리 실패 감지 |
| 모든 컷의 몸통 최하단 = 지면(880) | 캐릭터가 공중에 뜨는 문제 |
| 몸통 크기 편차 ≤ 12% | 자세가 아니라 그림 배율이 흔들린 경우 |
| 캔버스 밖 픽셀 없음 | 창끝·망토 잘림 |
| 발 검출 성공 (무기 오검출 없음) | 그림자가 엉뚱한 곳에 찍히는 문제 |
| 배경 잔여 초록 없음 | 크로마키 실패 |

---

## 6. 남은 판단 — 200명을 정말 다 그릴 것인가

20컷 × 200명 = **4,000컷.** 생성 비용과 검수 시간이 현실적이지 않다.

대안:

**(A) 무기 타입별 공용 몸** — 창·검·도·극 4벌 × 20컷 = 80컷.
장수별로는 **머리만 교체**하고 색을 바꾼다. 200명 전원 커버.
기존 200장수 초상이 이미 있으므로 머리는 재활용 가능.

**(B) 일기토 등장 장수를 한정** — 챕터 보스 등 20~30명만 전용 세트.
나머지는 (A) 방식.

**추천: (B) 우선, (A) 로 확장.** 얼굴이 중요한 유명 장수만 전용으로 뽑고,
나머지는 공용 몸 + 머리 교체로 채운다.

이 판단이 서야 발주 규모가 정해진다. 그 전까지는 조운·화웅 2명으로
파이프라인을 완성해두는 것이 맞다.
