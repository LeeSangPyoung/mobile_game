# 빌드 & 배포 가이드 (다른 PC에서 clone 후 재현)

손가락삼국지(`com.leesp.samgukgi`) — GitHub clone 상태에서 **서명 AAB 빌드**와 **웹 배포**까지 재현하는 절차.

> ⚠️ clone만으로는 부족합니다. 아래 **[0] 별도 전달 파일**을 먼저 넣어야 서명 빌드가 됩니다.

---

## [0] repo에 없는 것 — 별도로 전달받아 넣기 (필수)

이 파일들은 보안상 git에서 제외돼 있어 **다른 경로로 안전하게 전달**받아야 합니다.

| 파일 | 놓을 위치 | 없으면 |
|---|---|---|
| `upload-keystore.jks` | `app/android/` | **서명 불가 → Play 거부** |
| `keystore.properties` | `app/android/` | 서명 설정 없음 → 릴리스 서명 안 됨 |
| `firebase-service-account.json` | `server/secrets/` | 서버 FCM 푸시만 불가(AAB엔 무관) |

- 키스토어 원본 백업: 개발 PC의 `samgukgi-keystore-backup/` (repo 밖). 이 폴더째 옮겨 위 2개를 `app/android/`에 복사.
- **서명 SHA256**: `A1:A0:69:73:CC:3F:8B:90:…:2B:18:4B:37` — 이 키로만 Play가 업데이트를 받습니다(불일치 시 거부).

---

## [1] 사전 요구사항 (각 PC 1회)

- **Node.js 22 이상** (서버 `node:sqlite` 내장 사용). 확인: `node -v`
- **JDK 23** (AGP 8.13 빌드 확인 버전). 확인: `java -version`
- **Android SDK** (환경변수 `ANDROID_HOME` 또는 `app/android/local.properties`에 `sdk.dir=` 지정)
- Gradle은 래퍼(`gradlew`) 사용 — 별도 설치 불필요

---

## [2] 서명 AAB 빌드

### 자동 (Windows PowerShell)
```powershell
# repo 루트(mobile_game)에서
./build_aab.ps1                # 버전 유지
./build_aab.ps1 -BumpVersion   # versionCode +1, versionName 패치 자동 상향
```
스크립트가 순서대로: 키스토어 확인 → `npm install` → `www` 재생성(prototype+assets) → `cap sync` → `bundleRelease` → AAB 경로 출력.

### 수동 (맥/리눅스/윈도우 공통)
```bash
# 1) 버전 상향 — app/android/app/build.gradle 의 versionCode(+1) / versionName
# 2) 의존성
cd app && npm install && cd ..
# 3) 웹 자산 → 앱 번들 소스 재생성 (app/www 는 git 제외라 매번 생성)
cp prototype.html app/www/index.html
rm -rf app/www/assets && cp -r assets app/www/assets
# 4) capacitor 동기화
cd app && npx --no-install cap sync android && cd ..
# 5) 서명 릴리스 번들
cd app/android && ./gradlew :app:bundleRelease --no-daemon
```
산출물: `app/android/app/build/outputs/bundle/release/app-release.aab`

검증:
```bash
keytool -printcert -jarfile app/android/app/build/outputs/bundle/release/app-release.aab | grep SHA256
# → 위 지문과 일치해야 함
```
업로드: Play Console → 앱 → 프로덕션/내부테스트 → 새 릴리스에 `app-release.aab` 첨부(유저 계정으로 직접).

---

## [3] 웹 배포 (games.wooriban.org / app.wooriban.org)

같은 도메인 두 개 모두 VM `192.168.254.137`의 `/workspace/public/`를 서빙(Cloudflare 캐시 없음 → 올리면 즉시 반영).

```bash
# prototype.html 수정 후, repo 루트에서:
HK="SHA256:vV2qMd4k46dJtDcuS5MFO8GuIIFMqD4VANX1Vk58Log"
pscp -batch -hostkey "$HK" -pw <VM비번> prototype.html game@192.168.254.137:/workspace/public/index.html
```
- ⚠️ **VM 접속 비번은 `docs/server_deploy_reference.md`에 평문으로 있습니다.** repo를 받는 사람은 모두 봅니다. 공개 repo면 반드시 비번 교체 + 문서에서 제거 권장.
- 서버 코드(`server/mp_server.js`) 변경 시엔 업로드 후 `/workspace/restart.sh` 재시작 필요. 상세: `docs/server_deploy_reference.md`.

---

## 요약 체크리스트 (새 PC)
- [ ] git clone
- [ ] 키스토어 2개 → `app/android/` (필수)
- [ ] (서버 푸시 쓸 때만) `firebase-service-account.json` → `server/secrets/`
- [ ] Node22 / JDK23 / Android SDK 설치
- [ ] `./build_aab.ps1 -BumpVersion` (또는 수동 절차)
- [ ] AAB 서명 지문 확인 → Play 업로드
