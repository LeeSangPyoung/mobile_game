# Phase 0 실행계획 — 순수 엔진 분리 (engine.js)

대상: `손가락삼국지` 멀티플레이 전제 작업 / 상위문서: `multiplayer_realtime_design.md`

> **완료 기준(Definition of Done)**
> 1. `engine.js`가 DOM/캔버스/window/zoom/DPR 의존 없이 시뮬을 돈다.
> 2. **싱글플레이가 engine.js 위에서 리그레션 없이 동일하게 플레이**된다.
> 3. **같은 seed + 같은 명령열 → 항상 같은 최종상태**(결정론 self-test 통과).

---

## 1. 지금 왜 그대로 못 뜯나 — 3대 결합

| 결합 | 실측 근거 | 처리 |
|---|---|---|
| **렌더/UI 직접호출** | update()가 `document.body.classList`, `updateFactionLegend()`, `msgShown`, `camX/Y/zoom`, `clampCamera()`, `updateCinematic()`, `showSpeech()` 호출 | 엔진 밖으로 분리(콜백/이벤트로 역전) |
| **좌표 뷰포트 종속** | 부대 `army.x/y`=픽셀, 성=`k.x*worldPxW()`(17770), aggro=`AGGRO_DIST()/zoom` | **월드단위 좌표계로 전환**(핵심) |
| **비결정 난수/시계** | `Math.random` 307곳, `performance.now()` 다수 | 시뮬분만 seed rng / 틱카운터 주입 |

---

## 2. 목표 인터페이스 (engine.js)

```js
// engine.js — 서버·호스트·싱글 공유. 순수(브라우저 API 0).
export class SimEngine {
  constructor(mapDef, seed, opts) {
    this.rng = mulberry32(seed);      // 시뮬 난수 단일 소스
    this.tick = 0;                    // performance.now 대체
    this.world = { w, h };            // 월드단위(픽셀/DPR 무관)
    this.castles = [];                // 순수 상태(직렬화 가능)
    this.armies  = [];                // army.x/y = 월드단위
    this.events  = [];                // 이번 스텝 발생 이벤트(전투/함락/대사) → 렌더가 소비
  }
  enqueue(playerId, cmd) { ... }      // {type:'SEND_ARMY', fromId,toId,unit,...} 검증 후 큐잉
  step(dt = 1/15) { ... }             // 기존 update(dt) 시뮬 부분 이식(고정 dt, this.rng)
  snapshot() { ... }                  // {tick,castles,armies} 순수 복사(네트워크 전송용)
  applySnapshot(s) { ... }            // 게스트: 호스트 상태 수신 반영(보간은 렌더가)
}
```

- **이벤트 큐 패턴**: 엔진은 `showSpeech`/파티클을 직접 부르지 않고 `events`에 `{type:'speech',...}`만 push. 렌더 레이어가 매 프레임 소비 → 연출은 클라에만.
- **명령은 id 기반**: `sendArmy(fromCastleObj,...)` → `enqueue({fromId,toId,...})`. 객체참조 대신 안정적 id 사용(직렬화·검증 위함).

---

## 3. 추출 인벤토리

**상태(엔진으로 이동)**: `castles`(17744), `armies`(17816), 성/부대 필드, 성별 생산·성벽 상태.
**시뮬 함수(이식)**:
- `update(dt)`(19896) — 오케스트레이션(UI가드 제거 후 순수화)
- `growth(dt)`(19306) — 생산
- `enemyAI(dt)`(19295) — AI(싱글/중립용; PvP에선 인간측 비활성)
- `resolveEngagements(dt)`(19519) — 부대-부대 전투
- `resolveSieges(dt)`(19654) — 공성
- `wallRegenAndFire(dt)`(19877) — 성벽
- `sendArmy(...)`(19143) → `enqueue`/내부 spawn
- `makeEnemyInstance`(13321) 등 인스턴스 생성 시뮬분

**엔진 밖 유지(렌더/UI)**: `render`(24768), `loop`(25513), 카메라(`camX/Y/zoom`,`clampCamera`17778), `worldPxW/H`(17770 — **렌더 전용 변환기로 격하**), `showSpeech`(18527), 미니맵/범례, 모달, FX.

---

## 4. 좌표계 전환 (가장 어려운 핵심)

**현재**: 성=정규화(0..1), 부대=픽셀(`정규화*worldPxW()`), 거리계산 픽셀, aggro가 zoom에 의존.

**전환 후**:
- 엔진 월드단위 정의: `WORLD.w/h`(스테이지 `stage.world` 기반, **DPR·캔버스·zoom 무관**). 성 좌표는 정규화 유지, 필요시 월드단위로 승격.
- **부대 `x/y`를 월드단위로 저장**. 모든 시뮬 거리/속도/aggro를 월드단위 상수로.
- `AGGRO_DIST()/zoom` → **월드단위 고정 반경**(zoom 제거). 이것만으로 "줌이 게임성 바꾸는" 버그도 동시 해결.
- **렌더 레이어가 월드→스크린 변환** 전담: `screen = world * pxPerWorld * zoom + camera`, DPR은 여기서만. `worldPxW/H`는 이 변환 헬퍼로 재정의.

**리스크**: 속도·반경·충돌 임계값이 곳곳에 픽셀 상수로 박혀 있으면 전수 환산 필요. → 4-1에서 먼저 상수 목록화.

---

## 5. 결정론화

- **고정 dt**: 엔진 `step(1/15)`. 렌더 프레임레이트와 분리(렌더는 스냅샷 보간).
- **RNG 주입**: 시뮬 경로의 `Math.random` → `this.rng()`. **연출용(파티클·대사 선택 `pickRandom` 등 시각효과)은 제외** — 시뮬 결과에 영향 주는 것만(전투 변동, 스폰, aggro 스태거 등).
  - 작업법: "시뮬 함수(§3) 내부의 Math.random"만 grep해 교체. 렌더/FX 함수의 것은 건드리지 않음.
- **시계**: 시뮬 로직의 `performance.now()` → `this.tick` 기반. FX 타이밍은 렌더에 남김.

---

## 6. 마이그레이션 순서 (증분 — 매 단계 싱글 동작 유지)

1. ✅ **상수 감사(4-1)**: 완료(`phase0_coupling_audit.md`).
2. ✅ **좌표 전환**: Step 1(기기독립)·Step 2(줌독립) 완료 — 단, **싱글 QA 대기**(오피스 사정으로 검증 일괄 예정).
3. ✅ **파일 골격**: `engine.js` 생성 — `mulberry32`/`hashSnapshot`/`SimEngine`(constructor·enqueue·step·snapshot·applySnapshot) 계약 정의 + 상태 컨테이너. prototype import는 5단계(브라우저 배선)로 보류.
4. ✅ **함수 이관(전장 완료)**: 전장 전 시스템을 `SimEngine` 메서드로 이관 —
   `_growth`·`_enemyAI/_aiTurn`·`_resolveEngagements`(크리티컬 `_rollCrit`)·`_resolveSieges`(성벽·반격·출진·분쟁·점령)·`_wallRegen`·`_moveArmies`(aggro·사격·합류·점령·도착·회피)·`_arrive`·`_moveArrows`·`_tryHuoyu`(회유 분열/전향)·`_checkWin`.
   UI/연출/오디오 제거, 의미있는 사건만 `events[]`(capture/wallBreach/armyDead/huoyu/win)로 방출.
   **메타 보정(장수·업그레이드)은 부대·성의 숫자 필드로 주입**(기본 1/0 = 중립·적) — 배선층이 owner=1에 계산해 실어줌.
5. ⏭ **명령 경유**: 엔진 계약 완료(`enqueue({type:'SEND_ARMY',fromId,toId,unit,muls})` → `_applyCommands`/`_spawnArmy`). **prototype↔engine 실배선은 브라우저 필요 → 일괄 QA 시**.
6. ✅ **RNG/시계 주입**: 엔진은 `this.rng`(mulberry32)/`this.simTime` 단일 소스. prototype in-place도 부분완료(coupling_audit Step 3).
7. ✅ **결정론 self-test**: `test/sim_determinism.mjs` **10/10 통과** — 같은 seed+명령열 4000틱 2회 → **최종해시·이벤트열 완전 동일**. 전투·공성·점령·승리 실제 발생 검증.
8. ⏭ **싱글 리그레션 QA**: 일괄 예정. **엔진은 prototype와 병렬 구현이라 체감 파리티는 배선+브라우저 QA에서 확정**(체크리스트: `phase0_coupling_audit.md` Step 1~3).

> **현재 상태 요약**: 순수 결정론 전장 엔진(`engine.js`)이 **headless로 완주·검증**됨. 남은 것은 (a) prototype.html이 자체 시뮬 대신 이 엔진에 위임하도록 배선, (b) 배선 후 브라우저 리그레션 QA. 둘 다 브라우저 필요 → "검증 일괄" 항목.
> **미이관(의도)**: 보강군 합류(`sendReinforcement`, 플레이어 편의), 보상/포로/별점(메타), 초기 맵 생성 난수 — 엔진엔 고정 mapDef 주입.

---

## 7. 리그레션·결정론 검증

- **정직한 한계**: 원본이 비결정(Math.random)이라 "원본과 비트 단위 동일"은 증명 불가. 목표는 (a) **플레이 체감/규칙 동일**(수동 QA) + (b) **엔진 자체 결정론**(같은 입력→같은 결과).
- **결정론 하네스**(headless): `new SimEngine(map, 42)` + 고정 명령 스크립트 → N틱 → `hash(snapshot)`. 두 번 돌려 동일해야 통과. Node에서 실행(서버 재사용의 첫 증거이기도).
- **QA 체크리스트**: 생산 속도, 부대 합류, 공성 함락 타이밍, AI 진출, 승패 판정이 이전과 어긋나지 않는지.

---

## 8. 산출물

- `engine.js`(순수 시뮬), 렌더 레이어가 얇게 이를 소비하도록 수정된 `prototype.html`.
- `test/sim_determinism.mjs`(Node 결정론 하네스).
- 싱글플레이 리그레션 QA 노트.

→ 완료 시 Phase 1(Firebase 골격)과 병행 가능. 엔진이 곧 호스트/서버 권위 시뮬의 재사용 단위.

---

## 9. 착수 전 확인

- 이 계획대로 **2단계(좌표 전환)를 가장 먼저 격리 진행**하는 데 동의?
- Phase 0은 큰 리팩터라 **작업 중 싱글 회귀 위험**이 있음 → 별도 브랜치/백업 권장(현재 git 아님 → 폴더 백업 or git init).
