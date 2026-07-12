# 배포 가이드 — VM(192.168.254.131) + Cloudflare Tunnel

손가락삼국지 실시간 1v1 중계서버(`server/mp_server.js`)를 VMWare VM에서 돌리고, Cloudflare
Tunnel로 기존 도메인에 붙여 외부 접속을 여는 절차. **의존성 0**(Node 내장만) — `npm install` 불필요.

> 구성: `[폰/브라우저] --wss--> [Cloudflare 도메인] --tunnel--> [VM 192.168.254.131:8080 mp_server.js]`
> Firebase 아님(코드에 Firebase 없음). 계정=게스트 닉네임, 전적/유저=VM 로컬 SQLite(`server/mp.db`).

---

## 0. 요구사항 (VM)
- **Node.js 22 이상** (필수 — `node:sqlite`, 내장 WebSocket 클라이언트 사용). 확인: `node -v`
- 열어둘 포트: 로컬 **8080**(Cloudflare Tunnel이 이 포트로 붙음. 외부 방화벽 개방 불필요 — 터널이 아웃바운드).

## 1. 서버 파일 복사
`server/` 폴더 **통째로** VM에 복사(예: `/opt/samguk/server`). 필요한 것은 이 폴더뿐:
```
server/
  mp_server.js
  public/            # mp_game.html, admin.html, mp_game_2view.html, assets/…
```
> `public/*`는 빌드 산출물. 클라이언트/엔진/메타를 고치면 개발 PC에서
> `node tools/build_mp_server_client.mjs` 재실행 후 `server/public/`를 다시 복사.

## 2. 서버 실행
```bash
cd /opt/samguk/server
ADMIN_KEY='원하는_관리자키' PORT=8080 node mp_server.js
# → [mp_server] listening on :8080  (public=…, admin=/admin key=****)
```
- `ADMIN_KEY`: 관리자 페이지 인증키(미지정 시 기본 `samguk-admin` — **운영에선 반드시 지정**).
- `PORT`: 기본 8080.
- `DB_PATH`: 전적 DB 경로(기본 `server/mp.db`). 백업하려면 이 파일만 복사.

LAN 확인(VM 콘솔): `curl -s localhost:8080/health` → `ok`.
같은 망 다른 기기: `http://192.168.254.131:8080/` (서버는 0.0.0.0 바인딩이라 바로 열림).

### 서비스로 상시 구동
**Linux(systemd)** — `/etc/systemd/system/samguk.service`:
```ini
[Unit]
Description=samguk mp_server
After=network.target
[Service]
WorkingDirectory=/opt/samguk/server
Environment=PORT=8080
Environment=ADMIN_KEY=원하는_관리자키
ExecStart=/usr/bin/node mp_server.js
Restart=always
[Install]
WantedBy=multi-user.target
```
```bash
sudo systemctl daemon-reload && sudo systemctl enable --now samguk
sudo journalctl -u samguk -f      # 로그
```
**Windows VM**: `nssm install samguk "C:\Program Files\nodejs\node.exe" mp_server.js` (작업디렉토리=server 폴더, 환경변수 PORT/ADMIN_KEY 지정) 또는 `pm2 start mp_server.js`.

## 3. Cloudflare Tunnel 연결(기존 도메인)
VM에 `cloudflared` 설치 후:
```bash
cloudflared tunnel login                          # 브라우저로 도메인 인증(1회)
cloudflared tunnel create samguk                  # 터널 생성 → 자격증명 json 발급
# ~/.cloudflared/config.yml
#   tunnel: samguk
#   credentials-file: /root/.cloudflared/<UUID>.json
#   ingress:
#     - hostname: game.내도메인.com
#       service: http://localhost:8080
#     - service: http_status:404
cloudflared tunnel route dns samguk game.내도메인.com   # DNS 레코드 자동 생성
cloudflared tunnel run samguk                     # 실행(서비스화: cloudflared service install)
```
- **WebSocket은 Cloudflare 터널에서 기본 지원** — 별도 설정 불필요. 클라이언트는 페이지가 https로
  열리면 자동으로 `wss://game.내도메인.com` 로 붙는다(`location.protocol==='https:'?'wss:':'ws:'`).
- 상시 구동: `cloudflared service install` (systemd 유닛 자동 등록).

## 4. 접속 주소
- 게임: **https://game.내도메인.com/** (= `/mp_game.html`)
- 관리자: **https://game.내도메인.com/admin** → 우측 상단에 `ADMIN_KEY` 입력(브라우저에 저장됨)
- 한 창 2뷰 테스트: `/mp_game_2view.html`

## 5. 관리자 페이지 기능
- **대기 큐**: 닉네임·전투력·대기시간. 체크 2명 → **강제 매칭**. 개별 **추방**.
- **진행중 대전**: 호스트/게스트·전투력·경과. 교착 시 **강제 종료**.
- **전투력 랭킹 / 최근 결과**. 1.5초마다 자동 갱신.
- 매칭 규칙: **전투력이 비슷한 순**으로 자동 매칭, 대기가 길어지면 허용 전투력차가 3초마다 +200씩 확대
  (오래 기다린 사람은 결국 매칭). 파라미터는 `mp_server.js` 상단 `TOL_*` 상수로 조정.

## 6. 앱(Capacitor)에서 온라인 대전 붙이기 (선택)
안드로이드 앱은 로컬 자산을 로드하므로, 온라인 대전 진입은 앱 내 WebView가
`https://game.내도메인.com/` 를 열게 하거나, 앱 자체를 이 서버에서 서빙받게 하면 된다.
현재 앱 빌드(`deploy.sh`)는 싱글(prototype.html)만 번들 — 온라인 대전 연결은 별도 진입 버튼 추가가 필요.

---
### 트러블슈팅
- `node:sqlite` 에러 → Node 22 미만. Node 업그레이드.
- 접속은 되는데 대전이 안 붙음 → 터널 WebSocket은 자동이지만, 앞단에 다른 프록시가 있으면
  `Upgrade`/`Connection` 헤더 통과 확인.
- 전적/유저 초기화 → `server/mp.db` 삭제 후 재시작(주의: 전적 전부 삭제).
