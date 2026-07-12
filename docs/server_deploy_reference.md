# games.wooriban.org 배포 레퍼런스 (접속 + 반영 방법)

## 1. 아키텍처 (어디서 호스팅되나)
```
[브라우저/폰] --https/wss--> games.wooriban.org
      └─ Cloudflare Tunnel(터널명: samguk) ──> VM 192.168.254.137 : localhost:8080
                                                   └─ Node 서버 mp_server.js (/workspace)
```
- **실제 서버는 VMware VM `192.168.254.137`** 하나뿐입니다.
- `remote.wooriban.org`(존재 안 함), `192.168.254.131`(초기 오기)은 **서버 아님** — 여기 접속 시도하면 실패합니다.
- Cloudflare는 **HTML을 캐시하지 않음**(`Cache-Control: no-store` → `Cf-Cache-Status: DYNAMIC`). 파일만 올리면 **즉시 라이브 반영**됩니다.

## 2. 접속 정보 (SSH)
| 항목 | 값 |
|---|---|
| 호스트 | `192.168.254.137` (포트 22) |
| 계정 | `game` |
| 비밀번호 | `tkdvud83` |
| 호스트키 | `ssh-ed25519 SHA256:vV2qMd4k46dJtDcuS5MFO8GuIIFMqD4VANX1Vk58Log` |
| sudo | 가능 (비번 `tkdvud83`) |

> ⚠️ 이 VM은 VMware **NAT** 망이라 **호스트 PC(192.168.254.1)에서만** SSH 접속됩니다. 다른 기기/외부에서 SSH는 안 됨(웹은 Cloudflare로 접속).

### 접속 명령
**Windows (PuTTY plink/pscp — 이 PC에 설치됨):**
```bash
HK="SHA256:vV2qMd4k46dJtDcuS5MFO8GuIIFMqD4VANX1Vk58Log"
# 명령 실행
plink -batch -hostkey "$HK" -pw tkdvud83 game@192.168.254.137 "명령어"
# 파일 업로드
pscp -batch -hostkey "$HK" -pw tkdvud83 로컬파일 game@192.168.254.137:/원격경로
```
**Linux/Mac (ssh/scp):**
```bash
ssh game@192.168.254.137          # 비번 tkdvud83
scp 로컬파일 game@192.168.254.137:/원격경로
```

## 3. 서버 파일 위치 (VM)
```
/workspace/
  mp_server.js          # Node 서버 (매칭·중계·전적·랭킹·관리자API)
  start.sh restart.sh stop.sh   # 서버 관리 스크립트
  mp.db                 # SQLite (유저/전적/랭킹)
  cloudflared cf-start.sh       # Cloudflare 터널
  public/               # ← 웹에 서빙되는 폴더 (games.wooriban.org/…)
    index.html          # 메인게임 (prototype.html)
    mp_game.html        # 온라인 대전 클라
    admin.html          # 관리자 콘솔 (/admin)
    assets/…            # 게임 에셋
/home/game/node/bin/node        # Node 22 (사용자 설치)
```

## 4. 반영 방법

### A. 정적 파일 반영 (HTML/JS/에셋) — **업로드만, 재시작 불필요**
`/workspace/public/` 아래 파일을 덮어쓰면 **즉시 라이브**(서버가 no-store로 매번 새로 읽음, CF 캐시 없음).

예) 메인게임(index.html) 반영 — **이 저장소 루트에서:**
```bash
HK="SHA256:vV2qMd4k46dJtDcuS5MFO8GuIIFMqD4VANX1Vk58Log"
# prototype.html 수정 후:
pscp -batch -hostkey "$HK" -pw tkdvud83 prototype.html game@192.168.254.137:/workspace/public/index.html
```
온라인 클라(mp_game.html) 반영:
```bash
# tools/build_mp_server_client.mjs 수정 후 재빌드:
node tools/build_mp_server_client.mjs
pscp -batch -hostkey "$HK" -pw tkdvud83 server/public/mp_game.html game@192.168.254.137:/workspace/public/mp_game.html
```
관리자 페이지:
```bash
pscp -batch -hostkey "$HK" -pw tkdvud83 server/public/admin.html game@192.168.254.137:/workspace/public/admin.html
```
> 반영 즉시 확인: `curl -s "https://games.wooriban.org/index.html" | grep -c battleSelect` (0보다 크면 새 파일)

### B. 서버 코드 반영 (mp_server.js) — **업로드 + 재시작 필요**
```bash
HK="SHA256:vV2qMd4k46dJtDcuS5MFO8GuIIFMqD4VANX1Vk58Log"
pscp -batch -hostkey "$HK" -pw tkdvud83 server/mp_server.js game@192.168.254.137:/workspace/mp_server.js
MSYS_NO_PATHCONV=1 plink -batch -hostkey "$HK" -pw tkdvud83 game@192.168.254.137 "bash /workspace/restart.sh"
```

## 5. 서버 관리
| 작업 | 명령 (game으로 SSH 접속 후) |
|---|---|
| 재시작 | `/workspace/restart.sh` |
| 중지 | `/workspace/stop.sh` |
| 상태/로그 | `tail -f /workspace/mp.log` , `tail -f /workspace/cf.log` |
| health | `curl -s localhost:8080/health` → `ok` |
| 자동시작 | `crontab -l` (재부팅 시 mp_server + cloudflared 자동 기동 등록됨) |

## 6. 자주 하는 오해
- **"원격이 옛날 파일"** → 대개 (1) 다른 서버(.131/remote) 확인, 또는 (2) **로컬 브라우저 캐시**. 강력 새로고침(Ctrl+Shift+R)으로 해결. 오리진은 no-store라 항상 최신.
- **APK/AAB는 서버와 무관** → 앱은 `app/www`를 번들. 서버(games.wooriban.org)는 웹/온라인대전 중계용. 앱의 온라인 대전만 이 서버(`wss://games.wooriban.org`)로 접속.
