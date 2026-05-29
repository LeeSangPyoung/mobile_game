# BGM Inventory

2026-05-29 기준으로 실제 게임에서 쓰는 BGM은 총 3곡이다. 원본 기준 위치는 `assets/audio/`이고, 같은 파일을 `app/www/assets/audio/`와 `app/android/app/src/main/assets/public/assets/audio/`에 동기화했다.

## 현재 구성

- 전체 BGM: 3곡
- 평상시 BGM: 2곡
- 전투 BGM: 1곡
- 방향: 생성형/8비트/저샘플레이트 WAV 제거, 검증된 공개 음원 사용
- 라이선스: 3곡 모두 OpenGameArt의 CC0/Public Domain 계열

## 재생 로직

- 코드 위치: `prototype.html`, `app/www/index.html`, `app/android/app/src/main/assets/public/index.html`의 `BGM` 모듈
- 평상시 BGM 풀: `PREP_FILES`
- 전투 BGM 풀: `BATTLE_FILES`
- 화면 매핑: `splash`는 BGM 없음, `game`은 전투 BGM, 그 외 화면은 평상시 BGM
- 기본 볼륨: 평상시 45%, 전투 45%
- 음소거/볼륨 저장 위치: `SAVE.audioSettings`
- 페이드: 시작 700ms, 종료 500ms
- 회전 주기: 평상시 180초, 전투 240초
- 곡이 1개뿐인 풀은 회전 타이머를 만들지 않는다. 전투 BGM 1곡 구성에서 같은 곡이 중간에 재시작되는 것을 막기 위함이다.
- 선택 방식: 풀에 여러 곡이 있으면 랜덤 순서로 섞은 뒤 한 곡씩 재생한다. 모든 곡이 한 번씩 나온 뒤 다시 섞으며, 새 묶음의 첫 곡도 직전 곡과 겹치지 않게 한다.
- 재생 방식: 파일 기반 `Audio` 엘리먼트, `loop = true`

## 현재 트랙 목록

| 구분 | 파일 | 길이 | 포맷 | 크기 | 출처/라이선스 | 방향 |
| --- | --- | ---: | --- | ---: | --- | --- |
| 평상시 | `assets/audio/main_prepare_your_swords.ogg` | 88.3s | OGG Vorbis, stereo 44.1kHz | 1.2MB | OpenGameArt, `Prepare your swords`, CC0 | 출정/준비 화면용 판타지 앰비언트 |
| 평상시 | `assets/audio/main_up_in_the_sky.ogg` | 197.6s | OGG Vorbis, stereo 48kHz | 3.3MB | OpenGameArt, `Up in the Sky`, CC0 선택 가능 | 긴 루프형 메인/대기 화면 BGM |
| 전투 | `assets/audio/battle_qazijamjam.mp3` | 239.7s | MP3, stereo 44.1kHz, 192kbps | 5.5MB | OpenGameArt, `QaziJamJam`, CC0/Public Domain | 4분짜리 오케스트라 전투 BGM |

## 출처

- `QaziJamJam (orchestral battle theme)` by Emma_MA: https://opengameart.org/content/qazijamjam-orchestral-battle-theme
- `Prepare your swords` by bojidar-bg: https://opengameart.org/content/prepare-your-swords
- `Up in the Sky` by Memoraphile / You're Perfect Studio: https://opengameart.org/content/up-in-the-sky

## 제거된 런타임 트랙

아래 파일들은 런타임 BGM 풀에서 제거했고, 현재 오디오 폴더에서도 제외했다.

- `assets/audio/battle.ogg`
- `assets/audio/battle_iron_charge.wav`
- `assets/audio/battle_siege_breaker.wav`
- `assets/audio/prep_han_court.wav`
- `assets/audio/prep_war_council.wav`
- `assets/audio/prep_moonlit_camp.wav`
- `calm1.ogg`
- `calm2.ogg`
- `calm3.ogg`
- `calm4.wav`
- `calm5.wav`
- `battle1.wav`
- `battle2.wav`
- `battle3.wav`
- `battle4.wav`
- `battle5.wav`

## 주의

- `tools/generate_samguk_bgm.py`, `tools/generate_more_bgm.py`, `tools/remix_battle_from_ogg.py`는 과거 생성/실험용 스크립트다.
- 새 BGM 정책에서는 직접 합성한 8비트/저샘플레이트 음악을 런타임 풀에 넣지 않는다.
