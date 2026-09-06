// mp_server.js — 손가락삼국지 실시간 1v1 중계서버 (의존성 0: Node 내장만 사용)
//   기능: 정적파일 서빙 + WebSocket 중계 + 전투력기반 매칭 + 닉네임(중복체크) + 전적(승/패)
//         + 관리자 대시보드(/admin): 대기큐·진행중 대전 실시간 현황 + 강제매칭/추방
//   실행: node mp_server.js   (환경변수 PORT=8080, ADMIN_KEY, DB_PATH)
//   요구: Node 22+ (node:sqlite 내장). 배포: 이 폴더 통째로 복사 후 실행. npm install 불필요.
'use strict';
const http = require('http');
const crypto = require('crypto');
const fs = require('fs');
const path = require('path');
const { DatabaseSync } = require('node:sqlite');
const fcm = require('./fcm_push');   // FCM v1 발송(깜짝 이벤트 알림). 서비스계정 없으면 자동 비활성.

const PORT = Number(process.env.PORT || 8080);
const ADMIN_KEY = process.env.ADMIN_KEY || 'samguk-admin';
const PUB = path.join(__dirname, 'public');
const db = new DatabaseSync(process.env.DB_PATH || path.join(__dirname, 'mp.db'));
db.exec("CREATE TABLE IF NOT EXISTS users(uid TEXT PRIMARY KEY, nick TEXT UNIQUE, wins INTEGER DEFAULT 0, losses INTEGER DEFAULT 0, created INTEGER)");
db.exec("CREATE TABLE IF NOT EXISTS matches(id INTEGER PRIMARY KEY AUTOINCREMENT, host_uid TEXT, guest_uid TEXT, winner_side INTEGER, ended INTEGER)");
// 설치/실행 집계 — 앱·게임 실행 시 기기 고유 id(cid) 비콘. platform=app|web.
db.exec("CREATE TABLE IF NOT EXISTS installs(cid TEXT PRIMARY KEY, platform TEXT, first_seen INTEGER, last_seen INTEGER, launches INTEGER DEFAULT 0)");
// 푸시 토큰(FCM) — 앱에서 등록. 깜짝 이벤트 방송 대상.
db.exec("CREATE TABLE IF NOT EXISTS push_tokens(token TEXT PRIMARY KEY, cid TEXT, platform TEXT, created INTEGER, last_seen INTEGER)");
// 깜짝 이벤트(LiveOps) — 관리자가 등록, 30분 한정. active=1은 동시에 하나만.
db.exec("CREATE TABLE IF NOT EXISTS live_events(id INTEGER PRIMARY KEY AUTOINCREMENT, type TEXT, general_id TEXT, general_name TEXT, stars INTEGER, stage_id TEXT, stage_label TEXT, recruit_pct INTEGER, reward_stars INTEGER, reward_gold INTEGER, title TEXT, body TEXT, start_ts INTEGER, duration_min INTEGER, active INTEGER DEFAULT 1)");
for (const sql of [
  "ALTER TABLE live_events ADD COLUMN generals_json TEXT",   // 후보 장수 풀 [{id,name}] — 폰마다 랜덤 1명
  "ALTER TABLE live_events ADD COLUMN stage_local INTEGER",  // 장(1~20). NULL이면 유저 현재 챕터 랜덤 장
  "ALTER TABLE live_events ADD COLUMN free_recruit INTEGER DEFAULT 1", // 이벤트 등용 별차감 무마(1=무료, 0=별소모)
  "ALTER TABLE live_events ADD COLUMN test_cid TEXT",                   // 테스트 모드: 지정 기기(cid)에만 푸시·표시. NULL=전체 공개
]) { try { db.exec(sql); } catch (_) {} }
// 이벤트 달성자(클리어) 기록 — 유저별 1회. 콘솔에서 이벤트별 달성자 조회.
db.exec("CREATE TABLE IF NOT EXISTS event_completions(id INTEGER PRIMARY KEY AUTOINCREMENT, event_id INTEGER, cid TEXT, nick TEXT, general_id TEXT, general_name TEXT, recruited INTEGER, ts INTEGER)");
try { db.exec("CREATE UNIQUE INDEX IF NOT EXISTS idx_evcomp ON event_completions(event_id, cid)"); } catch (_) {}
// 전투력/기록 확장 컬럼 (기존 DB에도 안전하게 추가)
for (const sql of [
  "ALTER TABLE users ADD COLUMN power INTEGER DEFAULT 1000",
  "ALTER TABLE users ADD COLUMN banned INTEGER DEFAULT 0",
  "ALTER TABLE users ADD COLUMN draws INTEGER DEFAULT 0",
  "ALTER TABLE users ADD COLUMN is_bot INTEGER DEFAULT 0",
  "ALTER TABLE matches ADD COLUMN host_power INTEGER DEFAULT 0",
  "ALTER TABLE matches ADD COLUMN guest_power INTEGER DEFAULT 0",
  "ALTER TABLE matches ADD COLUMN dur INTEGER DEFAULT 0",
  "ALTER TABLE installs ADD COLUMN ua TEXT",       // 기기 User-Agent 원문
  "ALTER TABLE installs ADD COLUMN model TEXT",     // UA에서 파싱한 기기모델(예: SM-F926N)
  "ALTER TABLE installs ADD COLUMN andver TEXT",    // UA에서 파싱한 안드로이드 버전
]) { try { db.exec(sql); } catch (_) {} }

// ── 계정 + 세이브 보관 ───────────────────────────────────────────────────
// 세이브가 폰 안에만 있어서, 기기를 바꾸거나 앱을 지우면 처음부터였다.
// uid 는 users 와 같은 값을 쓴다 — 멀티 계정과 세이브 계정이 따로 놀면 어긋난다.
db.exec("CREATE TABLE IF NOT EXISTS accounts(uid TEXT PRIMARY KEY, token_hash TEXT NOT NULL, pgs_id TEXT UNIQUE, google_sub TEXT UNIQUE, created INTEGER, last_seen INTEGER)");
// mp_strict=1 이면 멀티 hello 에도 토큰을 요구한다. 토큰을 이해하는
// 클라이언트가 한 번 증명하면 켜진다 — 옛 클라이언트는 그때까지 통과.
for (const sql of ["ALTER TABLE accounts ADD COLUMN mp_strict INTEGER DEFAULT 0"]) { try { db.exec(sql); } catch (_) {} }
// data 는 클라의 localStorage['save'] 원문 그대로. 항목을 골라 담지 않는다 —
// 골라 담으면 나중에 SAVE 에 항목이 늘 때 조용히 빠진다.
db.exec("CREATE TABLE IF NOT EXISTS saves(uid TEXT PRIMARY KEY, rev INTEGER NOT NULL, data TEXT NOT NULL, size INTEGER, updated INTEGER, cid TEXT, device TEXT, summary TEXT)");
// 잘못 덮었을 때 되돌리기용. uid 당 최근 5개만 남긴다.
db.exec("CREATE TABLE IF NOT EXISTS save_history(id INTEGER PRIMARY KEY AUTOINCREMENT, uid TEXT, rev INTEGER, data TEXT, updated INTEGER)");
try { db.exec("CREATE INDEX IF NOT EXISTS idx_savehist ON save_history(uid, rev)"); } catch (_) {}

const SAVE_MAX = 256 * 1024;        // 실측 3KB, 만렙도 30KB. 256KB면 넉넉하다
const SAVE_HISTORY_KEEP = 5;

const newToken = () => crypto.randomBytes(32).toString('hex');
const hashToken = (t) => crypto.createHash('sha256').update(String(t || '')).digest('hex');

// 계정을 만든다. uid 는 멀티와 같은 규칙(u + 16hex).
function createAccount(existingUid) {
  const uid = existingUid || ('u' + crypto.randomBytes(8).toString('hex'));
  const token = newToken();
  const now = Date.now();
  db.prepare('INSERT INTO accounts(uid,token_hash,created,last_seen) VALUES(?,?,?,?) ON CONFLICT(uid) DO UPDATE SET token_hash=excluded.token_hash, last_seen=excluded.last_seen')
    .run(uid, hashToken(token), now, now);
  // 멀티 쪽 users 행도 없으면 만들어 둔다(닉네임은 나중에 로비에서 정한다)
  try {
    if (!db.prepare('SELECT uid FROM users WHERE uid=?').get(uid)) {
      db.prepare('INSERT INTO users(uid,nick,wins,losses,created,power) VALUES(?,?,0,0,?,?)')
        .run(uid, null, now, DEFAULT_POWER);
    }
  } catch (_) {}
  return { uid, token };
}

// 토큰이 맞아야 그 계정이다. 맞지 않으면 null.
function authAccount(uid, token) {
  if (!uid || !token) return null;
  const a = db.prepare('SELECT * FROM accounts WHERE uid=?').get(String(uid));
  if (!a) return null;
  const given = hashToken(token), want = String(a.token_hash || '');
  if (given.length !== want.length) return null;
  if (!crypto.timingSafeEqual(Buffer.from(given), Buffer.from(want))) return null;
  try { db.prepare('UPDATE accounts SET last_seen=? WHERE uid=?').run(Date.now(), a.uid); } catch (_) {}
  return a;
}

// uid 당 분당 6회. 정상 플레이로는 절대 안 걸리고, 폭주만 걸린다.
const putHits = new Map();
function putAllowed(uid) {
  const now = Date.now(), win = 60000;
  const arr = (putHits.get(uid) || []).filter((t) => now - t < win);
  if (arr.length >= 6) { putHits.set(uid, arr); return false; }
  arr.push(now); putHits.set(uid, arr);
  if (putHits.size > 5000) putHits.clear();   // 메모리 상한
  return true;
}

// ── 전투력 기반 매칭 파라미터 ────────────────────────────────────────────
const DEFAULT_POWER = 1000;      // 전투력 미보고 시 기본값
const TOL_BASE = 200;            // 최초 허용 전투력차
const TOL_STEP = 500;            // TOL_EVERY_MS마다 넓어지는 폭(빠른 확대)
const TOL_EVERY_MS = 1500;       // 1.5초마다 매칭폭 확대(빠르게)
const TOL_MAX = 1_000_000;       // 충분히 기다리면 사실상 아무나
const BOT_WAIT_MS = 3000;        // 큐에서 이만큼(3초) 상대 못 찾으면 봇 투입 (대기 이탈 방지 위해 10초→3초 단축)

// ── 봇(더미 상대) — 큐 0명일 때 대전 성사용. 이름은 실제 유저처럼 보이게 100개, 예약(유저 사용 금지). ──
const BOT_NAMES = [
  '관우형님','조조패왕','여포무쌍','제갈량빠','유비님좋아','장비돌격','조자룡7','마초킹덤','황충노장군','사마의책사',
  '손권강동','주유도독','육손불꽃','감녕수적','태사자','하후돈독안','장료위세','서황상승','방덕충절','강유북벌',
  '웃는호랑이','불꽃남자22','서울촌놈','부산갈매기88','대구사나이','밤샘전사','라면왕19','치킨각77','커피한잔해','새벽감성러',
  '도발은금지','무한도전각','국밥한그릇','노래하는곰','졸린고양이','달빛기사','철벽수비수','기병대장77','성벽지기13','통일제국2026',
  '전략의신88','삼국지매니아','붉은절벽','황금기병','청룡의화신','백호장군','현무방패','주작날개','오호대장군','천하제일검',
  'TripleK1ll','GGwp님','NoMercy77','WarHammer','DragonFist','IronWall88','RushKing','ShadowLord','KingSlayer','CavalryX',
  'SpearMaster','ArrowRain99','BladeDance','StormRider','NightOwl22','RedCliff208','ThunderGod','SilentBlade','FrostArrow','EmberKnight',
  'cavalry킹','spear장인','삼국Warrior','궁수Master','KOREA호랑이','Seoul촌놈77','busan파도','제갈Kong','LuBu여포','CaoCao조조',
  '별밤지기','겨울나그네','바람의검객','산적두목','평야의사자','설원의늑대','강철심장','불굴의창','연승가도','한판붙자',
  '초보아님요','고인물주의','즐겜유저','빡겜모드','리쌍의후예','전설의재림','막눈피셜','핵인싸군주','소환사협곡','정벌자김씨',
  '이순신함대','권율장군님','최영대감','을지문덕','계백결사대','김유신화랑','연개소문','대조영발해','광개토대왕','근초고왕',
];
// 봇 유저를 DB에 시드(is_bot=1) — 관리자에서 '봇'으로 구분 표시, '가입 유저' 카운트에선 제외.
(function seedBots() {
  const now = Date.now();
  const ins = db.prepare("INSERT OR IGNORE INTO users(uid,nick,wins,losses,created,power,is_bot) VALUES(?,?,0,0,?,1000,1)");
  for (let i = 0; i < BOT_NAMES.length; i++) { try { ins.run('bot_' + (i + 1), BOT_NAMES[i], now); } catch (_) {} }
})();

// ── 정적 파일 ────────────────────────────────────────────────────────────
const MIME = { '.html':'text/html; charset=utf-8', '.js':'text/javascript; charset=utf-8', '.css':'text/css; charset=utf-8',
  '.png':'image/png', '.jpg':'image/jpeg', '.jpeg':'image/jpeg', '.webp':'image/webp', '.svg':'image/svg+xml',
  '.json':'application/json; charset=utf-8', '.ogg':'audio/ogg', '.woff2':'font/woff2' };
const server = http.createServer((req, res) => {
  const u = new URL(req.url || '/', 'http://localhost');
  let p = decodeURIComponent(u.pathname);
  // CORS — 앱(WebView origin=https://localhost)에서 /push/register·/live_event를 크로스오리진 fetch하므로 허용.
  res.setHeader('Access-Control-Allow-Origin', '*');
  res.setHeader('Access-Control-Allow-Headers', 'Content-Type');
  res.setHeader('Access-Control-Allow-Methods', 'GET, POST, OPTIONS');
  if (req.method === 'OPTIONS') { res.writeHead(204); res.end(); return; }
  if (p === '/' || p === '') p = '/index.html';   // 메인게임(prototype). 온라인 대전은 /mp_game.html
  if (p === '/health') { res.writeHead(200); res.end('ok'); return; }
  // 설치/실행 비콘 — 게임 로드 시 기기 id(cid) 1회. 인증 불필요, 1x1 gif 응답(가벼움).
  if (p === '/beacon') {
    const cid = String(u.searchParams.get('cid') || '').replace(/[^a-zA-Z0-9_-]/g, '').slice(0, 40);
    const plat = u.searchParams.get('p') === 'app' ? 'app' : 'web';
    // 기기모델/안드버전은 클라 beacon이 아니라 User-Agent 헤더에서 파싱한다.
    //   예: "Mozilla/5.0 (Linux; Android 15; SM-F926N Build/…)" → andver=15, model=SM-F926N
    const ua = String(req.headers['user-agent'] || '').slice(0, 300);
    let andver = '', model = '';
    const _av = ua.match(/Android\s+([\d.]+)/i); if (_av) andver = _av[1];
    const _md = ua.match(/Android\s+[\d.]+;\s*([^;)]+?)\s*(?:Build\/|\))/i); if (_md) model = _md[1].trim();
    if (cid) { try {
      const now = Date.now();
      const ex = db.prepare('SELECT cid FROM installs WHERE cid=?').get(cid);
      // model/andver는 파싱됐을 때만 갱신(웹/UA누락 시 기존값 보존).
      if (ex) db.prepare("UPDATE installs SET last_seen=?, launches=launches+1, platform=?, ua=?, model=CASE WHEN ?<>'' THEN ? ELSE model END, andver=CASE WHEN ?<>'' THEN ? ELSE andver END WHERE cid=?").run(now, plat, ua, model, model, andver, andver, cid);
      else db.prepare('INSERT INTO installs(cid,platform,first_seen,last_seen,launches,ua,model,andver) VALUES(?,?,?,?,1,?,?,?)').run(cid, plat, now, now, ua, model, andver);
    } catch (_) {} }
    res.writeHead(200, { 'Content-Type': 'image/gif', 'Cache-Control': 'no-store', 'Access-Control-Allow-Origin': '*' });
    res.end(Buffer.from('R0lGODlhAQABAAAAACH5BAEKAAEALAAAAAABAAEAAAICTAEAOw==', 'base64'));
    return;
  }

  // ── 관리자 인증(토큰) + API ──
  const readBody = (cb) => { let b = ''; req.on('data', (c) => { b += c; if (b.length > 1e4) req.destroy(); }); req.on('end', () => { let j; try { j = JSON.parse(b || '{}'); } catch (_) { j = {}; } cb(j); }); };
  const sendJson = (code, obj) => { res.writeHead(code, { 'Content-Type': 'application/json; charset=utf-8', 'Cache-Control': 'no-store' }); res.end(JSON.stringify(obj)); };
  if (p === '/admin') p = '/admin.html';
  if (p === '/admin/login' && req.method === 'POST') {
    readBody((j) => {
      if (String(j.password || '') !== ADMIN_KEY) return sendJson(401, { ok: false, err: '비밀번호가 올바르지 않습니다' });
      sendJson(200, { ok: true, token: adminLogin() });
    });
    return;
  }
  if (p === '/admin/logout' && req.method === 'POST') { readBody((j) => { adminSessions.delete(String(j.token || '')); sendJson(200, { ok: true }); }); return; }
  if (p === '/admin/api') {
    if (!adminAuthed(u, req)) return sendJson(403, { ok: false, err: 'auth' });
    return sendJson(200, adminData());
  }
  if (p === '/admin/action' && req.method === 'POST') {
    if (!adminAuthed(u, req)) return sendJson(403, { ok: false, err: 'auth' });
    readBody((j) => sendJson(200, adminAction(j)));
    return;
  }
  if (p === '/admin/users') {
    if (!adminAuthed(u, req)) return sendJson(403, { ok: false, err: 'auth' });
    return sendJson(200, adminUsers(u.searchParams.get('q') || '', u.searchParams.get('sort') || 'power', parseInt(u.searchParams.get('page') || '1', 10)));
  }
  if (p === '/admin/user') {
    if (!adminAuthed(u, req)) return sendJson(403, { ok: false, err: 'auth' });
    return sendJson(200, adminUserDetail(u.searchParams.get('uid') || ''));
  }
  if (p === '/admin/matches') {
    if (!adminAuthed(u, req)) return sendJson(403, { ok: false, err: 'auth' });
    return sendJson(200, adminMatches(parseInt(u.searchParams.get('page') || '1', 10), u.searchParams.get('q') || ''));
  }
  // ── 푸시 토큰 등록(앱) ──
  if (p === '/push/register' && req.method === 'POST') {
    readBody((j) => {
      const tok = String(j.token || '').trim();
      if (!tok) return sendJson(400, { ok: false });
      const now = Date.now();
      try {
        db.prepare("INSERT INTO push_tokens(token,cid,platform,created,last_seen) VALUES(?,?,?,?,?) ON CONFLICT(token) DO UPDATE SET cid=excluded.cid, platform=excluded.platform, last_seen=excluded.last_seen")
          .run(tok, String(j.cid || ''), String(j.platform || 'app'), now, now);
      } catch (_) {}
      sendJson(200, { ok: true });
    });
    return;
  }
  // ── 계정 발급(익명) ──
  //   앱이 처음 켜질 때 말없이 한 번. 유저는 이런 게 있는 줄도 모른다.
  if (p === '/auth/anon' && req.method === 'POST') {
    readBody((j) => {
      try {
        const acc = createAccount(null);
        const cid = String(j.cid || '').replace(/[^a-zA-Z0-9_-]/g, '').slice(0, 40);
        if (cid) { try { db.prepare('UPDATE saves SET cid=? WHERE uid=?').run(cid, acc.uid); } catch (_) {} }
        sendJson(200, { ok: true, uid: acc.uid, token: acc.token });
      } catch (e) { sendJson(500, { ok: false, err: 'create' }); }
    });
    return;
  }
  // ── 세이브 올리기 ──
  //   몸통이 기본 readBody 상한(10KB)보다 클 수 있어 따로 읽는다.
  if (p === '/save/put' && req.method === 'POST') {
    let body = '';
    req.on('data', (c) => { body += c; if (body.length > SAVE_MAX + 4096) req.destroy(); });
    req.on('end', () => {
      let j; try { j = JSON.parse(body || '{}'); } catch (_) { j = {}; }
      const acc = authAccount(j.uid, j.token);
      if (!acc) return sendJson(401, { ok: false, err: 'auth' });
      if (!putAllowed(acc.uid)) return sendJson(429, { ok: false, err: 'rate' });
      const data = String(j.data || '');
      if (!data || data.length > SAVE_MAX) return sendJson(400, { ok: false, err: 'size' });
      try { JSON.parse(data); } catch (_) { return sendJson(400, { ok: false, err: 'json' }); }
      const cur = db.prepare('SELECT rev, data, updated FROM saves WHERE uid=?').get(acc.uid);
      const curRev = cur ? (cur.rev | 0) : 0;
      // 내가 읽어 간 판(baseRev)이 지금 서버 판과 다르면 그 사이에 다른 기기가 올렸다.
      // 말없이 덮지 않는다 — 어느 쪽을 살릴지는 사람이 고른다.
      const baseRev = (j.rev == null) ? curRev : (j.rev | 0);
      if (cur && baseRev !== curRev) {
        return sendJson(409, { ok: false, err: 'conflict', rev: curRev,
                               data: cur.data, updated: cur.updated });
      }
      const now = Date.now(), rev = curRev + 1;
      if (cur) {   // 덮기 전에 한 벌 남긴다
        try {
          db.prepare('INSERT INTO save_history(uid,rev,data,updated) VALUES(?,?,?,?)').run(acc.uid, cur.rev, cur.data, cur.updated);
          db.prepare('DELETE FROM save_history WHERE uid=? AND id NOT IN (SELECT id FROM save_history WHERE uid=? ORDER BY id DESC LIMIT ?)').run(acc.uid, acc.uid, SAVE_HISTORY_KEEP);
        } catch (_) {}
      }
      const summary = (j.summary && typeof j.summary === 'object') ? JSON.stringify(j.summary).slice(0, 500) : null;
      db.prepare('INSERT INTO saves(uid,rev,data,size,updated,cid,device,summary) VALUES(?,?,?,?,?,?,?,?) ON CONFLICT(uid) DO UPDATE SET rev=excluded.rev, data=excluded.data, size=excluded.size, updated=excluded.updated, cid=excluded.cid, device=excluded.device, summary=excluded.summary')
        .run(acc.uid, rev, data, data.length, now,
             String(j.cid || '').slice(0, 40), String(j.device || '').slice(0, 60), summary);
      sendJson(200, { ok: true, rev });
    });
    return;
  }
  // ── 세이브 내려받기 ──
  if (p === '/save/get') {
    const acc = authAccount(u.searchParams.get('uid'), u.searchParams.get('token'));
    if (!acc) return sendJson(401, { ok: false, err: 'auth' });
    const row = db.prepare('SELECT rev, data, updated, device, summary FROM saves WHERE uid=?').get(acc.uid);
    if (!row) return sendJson(200, { ok: true, rev: 0, data: null });
    return sendJson(200, { ok: true, rev: row.rev, data: row.data, updated: row.updated, device: row.device, summary: row.summary });
  }
  // ── 활성 깜짝 이벤트 조회(게임 폴링). 테스트 이벤트는 지정 cid에만 보임. ──
  if (p === '/live_event') {
    const _cid = u.searchParams.get('cid') || '';
    const _ev = activeEvent();
    if (_ev && _ev.testCid && _ev.testCid !== _cid) return sendJson(200, { ok: true, event: null });
    return sendJson(200, { ok: true, event: _ev });
  }
  // ── 이벤트 달성 보고(게임) ──
  if (p === '/event/complete' && req.method === 'POST') {
    readBody((j) => {
      const eid = parseInt(j.eventId, 10);
      const cid = String(j.cid || '').slice(0, 64);
      if (!eid || !cid) return sendJson(400, { ok: false });
      try {
        db.prepare("INSERT OR IGNORE INTO event_completions(event_id,cid,nick,general_id,general_name,recruited,ts) VALUES(?,?,?,?,?,?,?)")
          .run(eid, cid, String(j.nick || '').slice(0, 40), String(j.generalId || ''), String(j.generalName || ''), j.recruited ? 1 : 0, Date.now());
      } catch (_) {}
      sendJson(200, { ok: true });
    });
    return;
  }
  // ── 관리자: 이벤트 달성자 목록 ──
  if (p === '/admin/event/completions') {
    if (!adminAuthed(u, req)) return sendJson(403, { ok: false, err: 'auth' });
    const eid = parseInt(u.searchParams.get('id') || '0', 10) || 0;
    let rows = [];
    try { rows = db.prepare("SELECT cid, nick, general_id, general_name, recruited, ts FROM event_completions WHERE event_id=? ORDER BY ts DESC LIMIT 1000").all(eid); } catch (_) {}
    let ev = null;
    try {
      const r = db.prepare("SELECT * FROM live_events WHERE id=?").get(eid);
      if (r) {
        let generals = []; try { generals = r.generals_json ? JSON.parse(r.generals_json) : []; } catch (_) {}
        ev = { id: r.id, type: r.type, generals, generalName: r.general_name, stars: r.stars, stageLabel: r.stage_label, stageLocal: r.stage_local, recruitPct: r.recruit_pct, rewardStars: r.reward_stars, rewardGold: r.reward_gold, freeRecruit: (r.free_recruit == null ? true : !!r.free_recruit), title: r.title, durationMin: r.duration_min, startTs: r.start_ts, active: r.active };
      }
    } catch (_) {}
    return sendJson(200, { ok: true, id: eid, count: rows.length, rows, event: ev });
  }
  // ── 관리자: 이벤트 생성+푸시 방송 ──
  if (p === '/admin/event' && req.method === 'POST') {
    if (!adminAuthed(u, req)) return sendJson(403, { ok: false, err: 'auth' });
    readBody((j) => sendJson(200, createLiveEvent(j)));
    return;
  }
  // ── 관리자: 활성 이벤트 종료 ──
  if (p === '/admin/event/clear' && req.method === 'POST') {
    if (!adminAuthed(u, req)) return sendJson(403, { ok: false, err: 'auth' });
    try { db.exec("UPDATE live_events SET active=0 WHERE active=1"); } catch (_) {}
    return sendJson(200, { ok: true });
  }
  // ── 관리자: 푸시 대상 수 + 최근 이벤트(콘솔 표시용) ──
  if (p === '/admin/event/status') {
    if (!adminAuthed(u, req)) return sendJson(403, { ok: false, err: 'auth' });
    let tokens = 0, recent = [], devices = [];
    try { tokens = db.prepare("SELECT COUNT(*) c FROM push_tokens").get().c; } catch (_) {}
    try { recent = db.prepare("SELECT le.id, le.type, le.general_name, le.stage_label, le.start_ts, le.duration_min, le.active, (SELECT COUNT(*) FROM event_completions ec WHERE ec.event_id=le.id) AS done FROM live_events le ORDER BY le.id DESC LIMIT 10").all(); } catch (_) {}
    // 테스트 대상 선택용 — 푸시 토큰 보유 기기, 최근 접속순.
    try { devices = db.prepare("SELECT pt.cid AS cid, pt.last_seen AS last_seen, i.model AS model, i.andver AS andver FROM push_tokens pt LEFT JOIN installs i ON i.cid=pt.cid ORDER BY pt.last_seen DESC LIMIT 30").all(); } catch (_) {}
    return sendJson(200, { ok: true, tokens, fcm: fcm.fcmEnabled(), active: activeEvent(), recent, devices });
  }

  const file = path.normalize(path.join(PUB, p));
  if (!file.startsWith(PUB)) { res.writeHead(403); res.end('forbidden'); return; }
  fs.readFile(file, (e, data) => {
    if (e) { res.writeHead(404); res.end('not found'); return; }
    res.writeHead(200, { 'Content-Type': MIME[path.extname(file).toLowerCase()] || 'application/octet-stream', 'Cache-Control': 'no-store' });
    res.end(data);
  });
});

// ── WebSocket (직접 구현, 의존성 없음) ───────────────────────────────────
server.on('upgrade', (req, socket) => {
  const key = req.headers['sec-websocket-key'];
  if (!key) { socket.destroy(); return; }
  const accept = crypto.createHash('sha1').update(key + '258EAFA5-E914-47DA-95CA-C5AB0DC85B11').digest('base64');
  socket.write('HTTP/1.1 101 Switching Protocols\r\nUpgrade: websocket\r\nConnection: Upgrade\r\nSec-WebSocket-Accept: ' + accept + '\r\n\r\n');
  attach(socket);
});
function wsSend(socket, payload, opcode = 0x1) {
  const len = payload.length; let header;
  if (len < 126) header = Buffer.from([0x80 | opcode, len]);
  else if (len < 65536) { header = Buffer.allocUnsafe(4); header[0] = 0x80 | opcode; header[1] = 126; header.writeUInt16BE(len, 2); }
  else { header = Buffer.allocUnsafe(10); header[0] = 0x80 | opcode; header[1] = 127; header.writeBigUInt64BE(BigInt(len), 2); }
  try { socket.write(Buffer.concat([header, payload])); } catch (_) {}
}
const online = new Set();
function attach(socket) {
  const ws = { socket, uid: null, nick: null, room: null, power: DEFAULT_POWER, qtime: 0,
    sendJson(o) { wsSend(socket, Buffer.from(JSON.stringify(o))); }, close() { try { socket.end(); } catch (_) {} } };
  ws._alive = true;
  online.add(ws);
  let buf = Buffer.alloc(0);
  socket.on('data', (d) => {
    buf = Buffer.concat([buf, d]);
    for (;;) {
      const f = decodeFrame(buf); if (!f) break; buf = f.rest;
      ws._alive = true;                                                     // 어떤 프레임이든 = 살아있음
      if (f.opcode === 0x8) { onClose(ws); ws.close(); return; }
      if (f.opcode === 0x9) { wsSend(socket, f.payload, 0xA); continue; }   // ping→pong
      if (f.opcode === 0xA) { continue; }                                   // pong 수신(생존 확인)
      if (f.opcode === 0x1) { let m; try { m = JSON.parse(f.payload.toString('utf8')); } catch (_) { continue; } onMessage(ws, m); }
    }
  });
  socket.on('close', () => onClose(ws));
  socket.on('error', () => { try { socket.destroy(); } catch (_) {} onClose(ws); });
}
function decodeFrame(buf) {
  if (buf.length < 2) return null;
  const b1 = buf[1], opcode = buf[0] & 0x0f, masked = (b1 & 0x80) !== 0;
  let len = b1 & 0x7f, off = 2;
  if (len === 126) { if (buf.length < 4) return null; len = buf.readUInt16BE(2); off = 4; }
  else if (len === 127) { if (buf.length < 10) return null; len = Number(buf.readBigUInt64BE(2)); off = 10; }
  let mask = null;
  if (masked) { if (buf.length < off + 4) return null; mask = buf.slice(off, off + 4); off += 4; }
  if (buf.length < off + len) return null;
  let payload = buf.slice(off, off + len);
  if (masked) { const out = Buffer.allocUnsafe(len); for (let i = 0; i < len; i++) out[i] = payload[i] ^ mask[i & 3]; payload = out; }
  return { opcode, payload, rest: buf.slice(off + len) };
}

// ── 매칭/중계/전적 ───────────────────────────────────────────────────────
let queue = [];                     // 대기중 ws 목록
let matchSeq = 0;
const activeRooms = new Map();       // id → room(진행중 대전)

function dequeue(ws) { queue = queue.filter((x) => x !== ws); }
function tolerance(waitedMs) { return Math.min(TOL_MAX, TOL_BASE + Math.floor(Math.max(0, waitedMs) / TOL_EVERY_MS) * TOL_STEP); }

function enqueue(ws, power, mode) {
  dequeue(ws);
  leaveRoomIfAny(ws);   // 로비에서 큐 진입 = 전투 중 아님 → 남은 방 정리(고착 시 tryMatch가 스킵해 무한 대기 방지)
  if (ws.uid) clearInvite(ws.uid, true, 'friendCanceled');   // 랜덤/전투력 매칭 전환 → 내 친구초대 취소
  // 같은 계정(uid)의 다른 대기 연결은 큐에서 제거 — 자기 자신과 매칭 방지(계정당 1슬롯)
  if (ws.uid) for (const w of queue.slice()) if (w !== ws && w.uid === ws.uid) { dequeue(w); try { w.sendJson({ t: 'canceled', reason: 'dup' }); } catch (_) {} }
  ws.mode = (mode === 'random') ? 'random' : 'ranked';   // random=전투력 무시 즉시매칭, ranked=전투력 근접
  ws.power = Number.isFinite(power) ? (power | 0) : (ws.power || DEFAULT_POWER);
  ws.qtime = Date.now();
  queue.push(ws);
  if (ws.uid) { try { db.prepare('UPDATE users SET power=? WHERE uid=?').run(ws.power, ws.uid); } catch (_) {} }
  tryMatch();
  // 즉시 매칭됐으면 matched만 보냄(기존 동작). 아직 대기중일 때만 queued 통지.
  if (!ws.room) ws.sendJson({ t: 'queued', power: ws.power, waiting: queue.length });
}

// ── 친구 초대(초대→수락) ────────────────────────────────────────────────
const friendInvites = new Map();   // fromUid → { fromUid, toUid, fromNick, toNick, at, timer }
const FRIEND_TTL = 30000;          // 초대 만료(ms)
function onlineWsByUid(uid) { if (!uid) return null; for (const w of online) if (w.uid === uid) return w; return null; }
function onlineWsByNick(nick) { if (!nick) return null; const low = String(nick).toLowerCase(); for (const w of online) if (w.uid && w.nick && w.nick.toLowerCase() === low) return w; return null; }
// 초대 취소/정리 — notifyTarget=true면 초대 대상에게 msgType 통보
function clearInvite(fromUid, notifyTarget, msgType, fromNickOverride) {
  const inv = friendInvites.get(fromUid); if (!inv) return null;
  friendInvites.delete(fromUid);
  if (inv.timer) { try { clearTimeout(inv.timer); } catch (_) {} }
  if (notifyTarget) { const tw = onlineWsByUid(inv.toUid); if (tw) try { tw.sendJson({ t: msgType || 'friendCanceled', from: inv.fromNick }); } catch (_) {} }
  return inv;
}
// 특정 ws가 관여한 모든 초대 정리 — 매칭 진입/접속종료 시 호출(양방향 통보)
function clearInvitesInvolving(ws, reasonToInviter) {
  if (!ws || !ws.uid) return;
  clearInvite(ws.uid, true, 'friendCanceled');                       // 내가 보낸 초대 → 대상에 취소통보
  for (const [fu, inv] of [...friendInvites]) if (inv.toUid === ws.uid) {   // 나를 향한 초대 → 초대자에 통보
    friendInvites.delete(fu); if (inv.timer) { try { clearTimeout(inv.timer); } catch (_) {} }
    const aw = onlineWsByUid(inv.fromUid); if (aw) try { aw.sendJson({ t: 'friendError', msg: reasonToInviter || '상대가 준비를 종료했습니다' }); } catch (_) {}
  }
}

function makeRoom(a, b, friendly) {
  // 호스트(권위) = 더 오래 기다린 쪽(qtime 작은 쪽). 동률이면 a.
  const host = (a.qtime <= b.qtime) ? a : b;
  const guest = (host === a) ? b : a;
  dequeue(host); dequeue(guest);
  const id = ++matchSeq;
  const room = { id, a: host, b: guest, recorded: false, started: Date.now(), friendly: !!friendly };
  host.room = room; guest.room = room;
  activeRooms.set(id, room);
  // 매칭 확정 → 두 사람이 관여한 잔여 친구초대 정리(상대편에 통보)
  clearInvitesInvolving(host, '상대가 다른 대전을 시작했습니다');
  clearInvitesInvolving(guest, '상대가 다른 대전을 시작했습니다');
  host.sendJson({ t: 'matched', role: 'host', opp: guest.nick, oppPower: guest.power });
  guest.sendJson({ t: 'matched', role: 'guest', opp: host.nick, oppPower: host.power });
}

// 전투력이 가까운 순으로 정렬 후, 대기시간에 따라 넓어지는 허용폭 안에서 인접쌍을 그리디 매칭
function tryMatch() {
  if (queue.length < 2) return;
  const now = Date.now();
  // 1) 랜덤 큐: 전투력 무시, 서로 다른 계정 아무나 즉시 매칭(먼저 온 순)
  const rnd = queue.filter((w) => w.mode === 'random' && !w.room).sort((x, y) => x.qtime - y.qtime);
  for (let i = 0; i < rnd.length; i++) {
    if (rnd[i].room) continue;
    for (let j = i + 1; j < rnd.length; j++) {
      if (rnd[j].room || (rnd[i].uid && rnd[i].uid === rnd[j].uid)) continue;
      makeRoom(rnd[i], rnd[j]); break;
    }
  }
  // 2) 전투력 큐: 근접 매칭(대기 길수록 허용폭 확대)
  const ranked = queue.filter((w) => w.mode !== 'random' && !w.room).sort((x, y) => (x.power - y.power) || (x.qtime - y.qtime));
  for (let i = 0; i + 1 < ranked.length; i++) {
    const a = ranked[i], b = ranked[i + 1];
    if (a.room || b.room) continue;
    if (a.uid && a.uid === b.uid) continue;    // 같은 계정끼리 매칭 금지
    const gap = Math.abs(a.power - b.power);
    const tol = Math.max(tolerance(now - a.qtime), tolerance(now - b.qtime));
    if (gap <= tol) makeRoom(a, b);
  }
}
setInterval(tryMatch, 1000);   // 대기시간 경과에 따른 허용폭 확대 반영

// ── 봇 투입: 큐에서 BOT_WAIT_MS(3초) 넘게 상대 못 찾은 대기자에게 봇 상대 배정 ──
//   봇 전투는 '클라'에서 로컬 AI로 진행(서버는 상대 없음). 서버는 이름·시드·난이도만 내려줌.
function spawnBotFor(ws) {
  if (!ws || ws.room) return;
  const botNick = BOT_NAMES[Math.floor(Math.random() * BOT_NAMES.length)];
  const seed = (Math.floor(Math.random() * 0x100000000)) >>> 0;
  const difficulty = Math.random();                                   // 0~1 (클라가 AI레벨·팀강도로 환산)
  const botPower = Math.max(500, (ws.power | 0) + Math.round((Math.random() * 2 - 1) * 400));  // 내 전투력 ±400 근처
  dequeue(ws);
  ws._botMatch = true; ws._botNick = botNick;                         // 봇전 진행중 + 상대 봇 이름(결과 기록용)
  try { ws.sendJson({ t: 'botMatch', botNick, seed, difficulty, botPower }); } catch (_) {}
}
setInterval(() => {
  const now = Date.now();
  for (const w of queue.slice()) {
    if (w.room) continue;
    if (now - (w.qtime || now) >= BOT_WAIT_MS) spawnBotFor(w);
  }
}, 1000);

// 하트비트: 10초마다 ping. 직전 주기에 아무 응답도 없던(pong/메시지) 소켓은 좀비로 보고 축출.
//   → 비정상 끊김(앱 강제종료·절전·네트워크 끊김) 시에도 ~10~20초 내 정리 + 상대에 기권승. (30초→10초로 단축)
setInterval(() => {
  for (const ws of [...online]) {
    if (ws._alive === false) {
      ws._miss = (ws._miss || 0) + 1;
      // 모바일 백그라운드(JS 정지)는 흔하므로 1주기로 축출하지 않음 — 연속 4주기(~40초) 무응답이어야 좀비로 정리.
      if (ws._miss > 4) { try { ws.socket.destroy(); } catch (_) {} onClose(ws); continue; }
    } else { ws._miss = 0; }
    ws._alive = false;
    try { wsSend(ws.socket, Buffer.alloc(0), 0x9); } catch (_) {}   // ping
  }
}, 10000);

function sendStats(ws) {
  if (!ws || !ws.uid) return;
  const u = db.prepare('SELECT wins,losses,power,draws FROM users WHERE uid=?').get(ws.uid);
  if (u) ws.sendJson({ t: 'stats', wins: u.wins, losses: u.losses, power: u.power, draws: u.draws });
}
function recordRoomResult(room, winnerSide) {
  if (!room || room.recorded) return;
  room.recorded = true;
  activeRooms.delete(room.id);
  // 방 종료 → 양쪽 .room 참조 해제(안 하면 tryMatch의 !w.room 필터에 걸려 재매칭 영구 불가)
  if (room.a && room.a.room === room) room.a.room = null;
  if (room.b && room.b.room === room) room.b.room = null;
  if (room.friendly) { sendStats(room.a); sendStats(room.b); return; }   // 친구전=캐주얼: 승패·랭킹 미기록
  const hostU = room.a.uid, guestU = room.b.uid;
  const winU = winnerSide === 1 ? hostU : guestU, loseU = winnerSide === 1 ? guestU : hostU;
  try {
    if (winU) db.prepare('UPDATE users SET wins=wins+1 WHERE uid=?').run(winU);
    if (loseU) db.prepare('UPDATE users SET losses=losses+1 WHERE uid=?').run(loseU);
    db.prepare('INSERT INTO matches(host_uid,guest_uid,winner_side,ended,host_power,guest_power,dur) VALUES(?,?,?,?,?,?,?)')
      .run(hostU, guestU, winnerSide, Date.now(), room.a.power | 0, room.b.power | 0, Date.now() - room.started);
  } catch (_) {}
  sendStats(room.a); sendStats(room.b);
}
function recordResult(ws, winnerSide) {
  const room = ws.room; if (!room || room.recorded) return;
  if (ws !== room.a) return;                       // 호스트(권위)만 결과 기록
  recordRoomResult(room, winnerSide);
}
// 기권/이탈 — 나간 쪽(ws)의 반대편이 승. 상대에 oppLeft(forfeit) 통보 + 기록.
function forfeitRoom(ws, reason) {
  const room = ws.room; if (!room) return;
  const other = room.a === ws ? room.b : room.a;
  if (!room.recorded) recordRoomResult(room, ws === room.a ? 2 : 1);   // ws=host면 guest(2) 승. (주의: 내부에서 양쪽 .room=null 처리)
  // recordRoomResult가 이미 other.room을 null로 만들므로 조건 없이 통보(예전엔 other.room===room 검사에 걸려 oppLeft 미전송 버그)
  if (other) { other.room = null; try { other.sendJson({ t: 'oppLeft', reason: reason || 'forfeit' }); } catch (_) {} }
  activeRooms.delete(room.id);
  ws.room = null;
}
// 로비에서 매칭/초대 시도 = 이 클라는 전투 중이 아님. 남은 방이 있으면(호스트 result 누락 등으로 고착) 정리.
// 방이 아직 살아있으면(미기록) 포기 처리(상대 기권승) 후 참조 해제 → '이미 대전 중' 고착 방지.
function leaveRoomIfAny(ws) {
  const r = ws && ws.room;
  if (!r) return;
  if (!r.recorded && activeRooms.has(r.id)) { try { forfeitRoom(ws, 'forfeit'); } catch (_) {} }
  ws.room = null;
}
// ── 재접속 유예(순간 끊김/화면잠금 보호) ─────────────────────────────────────
// 전투 중 끊기면 즉시 기권이 아니라 GRACE_MS 동안 재접속을 기다리고, 그 사이 돌아오면 대전을 이어감.
const GRACE_MS = 30000;   // 재접속 유예 30초 — 모바일에서 잠깐 앱 벗어났다 와도 대전 유지(예전 9초는 너무 짧았음)
// 유예 만료 등에서 '진 쪽'을 side로 지정해 기권 처리(끊긴 소켓은 이미 죽었으므로 ws가 아니라 side 사용).
function forfeitBySide(room, side, reason) {
  if (!room) return;
  if (room._graceTimer) { clearTimeout(room._graceTimer); room._graceTimer = null; }
  if (room.recorded) { activeRooms.delete(room.id); return; }
  const loserIsHost = (side === 'a');
  const other = loserIsHost ? room.b : room.a;
  recordRoomResult(room, loserIsHost ? 2 : 1);   // 진 쪽이 host면 guest(2) 승
  if (other) { other.room = null; try { other.sendJson({ t: 'oppLeft', reason: reason || 'forfeit' }); } catch (_) {} }
  activeRooms.delete(room.id);
}
// hello(재접속) 시 호출 — 유예중인 방이 있으면 새 소켓을 재부착하고 양쪽에 재개 통보.
function tryResumeRoom(ws) {
  if (!ws || !ws.uid) return false;
  for (const room of activeRooms.values()) {
    if (room.recorded || !room._graceUid || !room._graceSide) continue;
    const oldWs = (room._graceSide === 'a') ? room.a : room.b;
    if (!oldWs || oldWs.uid !== ws.uid) continue;
    // 재부착 — 옛(좀비) 소켓의 방 참조를 끊고(그대로 두면 그 소켓 정리 시 이 방에 또 유예가 걸림), 새 소켓으로 교체
    if (oldWs !== ws) { try { oldWs.room = null; oldWs._miss = 0; } catch (_) {} }
    if (room._graceTimer) { clearTimeout(room._graceTimer); room._graceTimer = null; }
    if (room._graceSide === 'a') room.a = ws; else room.b = ws;
    ws.room = room; ws._lastMsgAt = Date.now();
    room._graceUid = null; room._graceSide = null;
    try { ws.sendJson({ t: 'resumeMatch', role: (room.a === ws ? 'host' : 'guest') }); } catch (_) {}
    const opp = (room.a === ws) ? room.b : room.a;
    if (opp) { try { opp.sendJson({ t: 'oppResumed' }); } catch (_) {} }
    return true;
  }
  return false;
}
// 같은 계정(uid)의 옛(좀비) 세션 정리 — 새 hello 소켓만 남겨 이중 세션/재접속 실패 방지.
//   단, 옛 소켓이 아직 '살아있는 방'을 잡고 있으면 건드리지 않고 정상 유예/onClose에 맡김(안전).
function evictStaleSessions(ws) {
  if (!ws || !ws.uid) return;
  for (const w of [...online]) {
    if (w === ws || w.uid !== ws.uid) continue;
    if (w.room && !w.room.recorded) continue;   // 살아있는 방 보유 → 건드리지 않음
    online.delete(w);
    dequeue(w);
    try { w.socket.destroy(); } catch (_) {}
  }
}
// 닉네임 길이(칸): 한글 음절/자모=2칸, 그 외(영문·숫자·밑줄)=1칸
function nickWeight(s) {
  let n = 0;
  for (let i = 0; i < s.length; i++) {
    const c = s.charCodeAt(i);
    n += ((c >= 0xAC00 && c <= 0xD7A3) || (c >= 0x3131 && c <= 0x318E)) ? 2 : 1;
  }
  return n;
}
// 닉네임 유효성: 4~16칸(한글=2칸 → 한글 2~8자·영문/숫자 4~16자), 한글·영문·숫자·밑줄만. { nick } 또는 { err }
const BOT_NAME_SET = new Set(BOT_NAMES.map((s) => s.toLowerCase()));
function isReservedNick(nick) { return BOT_NAME_SET.has(String(nick || '').toLowerCase()); }
function validateNick(raw) {
  const nick = String(raw == null ? '' : raw).trim();
  if (!nick) return { err: '닉네임을 입력하세요' };
  if (!/^[0-9A-Za-z가-힣ㄱ-ㅎㅏ-ㅣ_]+$/.test(nick)) return { err: '한글·영문·숫자·밑줄만 쓸 수 있습니다' };
  const w = nickWeight(nick);
  if (w < 4) return { err: '너무 짧습니다 · 한글 2자 또는 영문·숫자 4자 이상' };
  if (w > 16) return { err: '너무 깁니다 · 한글 8자 또는 영문 16자 이하' };
  if (isReservedNick(nick)) return { err: '사용할 수 없는 닉네임입니다' };   // 봇 예약 이름 — 유저 사용 금지
  return { nick: nick };
}
function onMessage(ws, m) {
  if (!m || typeof m.t !== 'string') return;
  ws._lastMsgAt = Date.now();   // 상대 이탈 판정용 — 실제 메시지(턴 릴레이 포함) 수신 시각
  if (m.t === 'hello') {
    if (m.uid) {
      const u = db.prepare('SELECT * FROM users WHERE uid=?').get(m.uid);
      if (u) {
        if (u.banned) { ws.sendJson({ t: 'error', code: 'banned', msg: '차단된 계정입니다' }); return; }
        // 신원 확인 — uid 만으로는 안 된다. 토큰이 있어야 그 사람이다.
        //   예전엔 uid 만 맞으면 통과했다. 세이브가 서버에 있는 지금은
        //   그게 곧 '남의 진행도를 덮어쓸 수 있다' 가 된다.
        let issued = null;
        const acc = db.prepare('SELECT * FROM accounts WHERE uid=?').get(u.uid);
        if (!acc) {
          // 처음 보는 계정 — 토큰을 만들어 welcome 에 실어 보낸다.
          // 옛 클라이언트는 이 값을 무시한다. 그래도 끊기지 않는다(아래 참고).
          issued = createAccount(u.uid).token;
        } else if (m.token) {
          // 토큰을 보냈다 = 새 클라이언트. 맞아야 통과하고, 이후로는 엄격해진다.
          if (!authAccount(u.uid, m.token)) { ws.sendJson({ t: 'error', code: 'noauth', msg: '인증에 실패했습니다' }); return; }
          if (!acc.mp_strict) { try { db.prepare('UPDATE accounts SET mp_strict=1 WHERE uid=?').run(u.uid); } catch (_) {} }
        } else if (acc.mp_strict) {
          // 한 번 토큰을 쓰던 계정이 갑자기 안 보낸다 — 남이 uid 만 들고 온 것이다.
          ws.sendJson({ t: 'error', code: 'noauth', msg: '인증에 실패했습니다' }); return;
        } else {
          // 아직 업데이트 안 한 유저. 지금까지처럼 통과시키고 토큰만 다시 쥐여 준다.
          issued = createAccount(u.uid).token;
        }
        ws.uid = u.uid; ws.nick = u.nick; ws.power = u.power || DEFAULT_POWER;
        const w = { t: 'welcome', uid: u.uid, nick: u.nick, wins: u.wins, losses: u.losses, power: u.power, draws: u.draws };
        if (issued) w.token = issued;
        ws.sendJson(w);
        try { tryResumeRoom(ws); } catch (_) {}
        try { evictStaleSessions(ws); } catch (_) {}
        return;
      }
    }
    if (m.nick != null) {
      const v = validateNick(m.nick);
      if (v.err) { ws.sendJson({ t: 'error', code: 'nick', msg: v.err }); return; }
      const nick = v.nick;
      if (db.prepare('SELECT uid FROM users WHERE nick=?').get(nick)) { ws.sendJson({ t: 'error', code: 'dup', msg: '이미 사용중인 닉네임입니다' }); return; }
      const uid = 'u' + crypto.randomBytes(8).toString('hex');
      try { db.prepare('INSERT INTO users(uid,nick,wins,losses,created,power) VALUES(?,?,0,0,?,?)').run(uid, nick, Date.now(), DEFAULT_POWER); }
      catch (_) { ws.sendJson({ t: 'error', code: 'dup', msg: '이미 사용중인 닉네임입니다' }); return; }
      // 새 계정에는 처음부터 토큰을 쥐여 주고, 곧바로 엄격 모드로 둔다.
      const _tok = createAccount(uid).token;
      try { db.prepare('UPDATE accounts SET mp_strict=1 WHERE uid=?').run(uid); } catch (_) {}
      ws.uid = uid; ws.nick = nick; ws.power = DEFAULT_POWER;
      ws.sendJson({ t: 'welcome', uid, nick, wins: 0, losses: 0, power: DEFAULT_POWER, draws: 0, token: _tok });
      return;
    }
    ws.sendJson({ t: 'error', code: 'login', msg: '로그인 실패' });
  }
  else if (m.t === 'renameNick') {   // 닉네임 변경
    if (!ws.uid) { ws.sendJson({ t: 'error', code: 'noauth', msg: '닉네임 등록 필요' }); return; }
    const v = validateNick(m.nick);
    if (v.err) { ws.sendJson({ t: 'error', code: 'renameErr', msg: v.err }); return; }
    const nick = v.nick;
    if (nick === ws.nick) { ws.sendJson({ t: 'renamed', nick: nick }); return; }
    const ex = db.prepare('SELECT uid FROM users WHERE nick=?').get(nick);
    if (ex && ex.uid !== ws.uid) { ws.sendJson({ t: 'error', code: 'renameErr', msg: '이미 사용중인 닉네임입니다' }); return; }
    try { db.prepare('UPDATE users SET nick=? WHERE uid=?').run(nick, ws.uid); }
    catch (_) { ws.sendJson({ t: 'error', code: 'renameErr', msg: '변경에 실패했습니다(중복)' }); return; }
    ws.nick = nick;
    ws.sendJson({ t: 'renamed', nick: nick });
  }
  else if (m.t === 'queue') { if (!ws.uid) { ws.sendJson({ t: 'error', code: 'noauth', msg: '닉네임 등록 필요' }); return; } enqueue(ws, m.power, m.mode); }
  else if (m.t === 'cancel') { dequeue(ws); ws.sendJson({ t: 'canceled' }); }
  else if (m.t === 'relay') { const r = ws.room; if (r) { const other = r.a === ws ? r.b : r.a; if (other) other.sendJson({ t: 'relay', m: m.m }); } }
  else if (m.t === 'result') { recordResult(ws, m.winner | 0); }
  else if (m.t === 'forfeit') { forfeitRoom(ws, 'forfeit'); }
  else if (m.t === 'botResult') {
    // 봇전 결과 — 실제 유저의 승/패만 기록(랭킹 A안). _botMatch 플래그로 봇 1회당 1결과만(파밍 가드).
    if (!ws.uid || !ws._botMatch) return;
    ws._botMatch = false;
    const won = !!m.won;
    let botUid = null;
    try { const b = db.prepare('SELECT uid FROM users WHERE nick=? AND is_bot=1').get(ws._botNick || ''); if (b) botUid = b.uid; } catch (_) {}
    try {
      db.prepare('UPDATE users SET ' + (won ? 'wins=wins+1' : 'losses=losses+1') + ' WHERE uid=?').run(ws.uid);
      db.prepare('INSERT INTO matches(host_uid,guest_uid,winner_side,ended,host_power,guest_power,dur) VALUES(?,?,?,?,?,?,?)')
        .run(ws.uid, botUid, won ? 1 : 2, Date.now(), ws.power | 0, 1000, 0);   // guest=봇(이름 표시). botUid null이면 여전히 빈칸
    } catch (_) {}
    sendStats(ws);
  }
  else if (m.t === 'oppGone') {
    // 남은 클라가 '상대 턴 끊김'을 보고. 상대가 유예시간(GRACE_MS)+ 무메시지일 때만 인정 → 상대 이탈 = ws 기권승.
    //   (예전 8초는 모바일 백그라운드 유예보다 짧아, 잠깐 벗어난 상대를 조기 기권시켰음)
    const r = ws.room;
    if (r && !r.recorded) {
      const other = r.a === ws ? r.b : r.a;
      if (other && (Date.now() - (other._lastMsgAt || 0)) > GRACE_MS) forfeitRoom(other, 'timeout');
    }
  }
  else if (m.t === 'stats') { sendStats(ws); }
  else if (m.t === 'rank') { sendRank(ws); }
  // ── 친구 초대 ──
  else if (m.t === 'friendInvite') {
    if (!ws.uid) { ws.sendJson({ t: 'error', code: 'noauth', msg: '닉네임 등록 필요' }); return; }
    leaveRoomIfAny(ws);   // 로비 복귀 후 남은 방 정리(고착 방지) — 이후 정상적으로 대상 검증
    const target = String(m.target || '').trim().slice(0, 16);
    if (!target) { ws.sendJson({ t: 'friendError', msg: '상대 닉네임을 입력하세요' }); return; }
    if (target.toLowerCase() === String(ws.nick || '').toLowerCase()) { ws.sendJson({ t: 'friendError', msg: '자기 자신은 초대할 수 없습니다' }); return; }
    if (isReservedNick(target)) { ws.sendJson({ t: 'friendError', msg: '초대할 수 없는 상태입니다' }); return; }   // 봇 이름 — 초대 방어
    const tw = onlineWsByNick(target);
    if (!tw || !tw.uid) { ws.sendJson({ t: 'friendError', msg: '상대가 접속 중이 아닙니다' }); return; }
    if (tw.uid === ws.uid) { ws.sendJson({ t: 'friendError', msg: '자기 자신은 초대할 수 없습니다' }); return; }
    if (tw.room) { ws.sendJson({ t: 'friendError', msg: '상대가 대전 중입니다' }); return; }
    clearInvite(ws.uid, true, 'friendCanceled');   // 내 이전 초대 취소(대상 통보)
    dequeue(ws);                                    // 친구대전 준비 → 랜덤 큐에서 빠짐
    const inv = { fromUid: ws.uid, toUid: tw.uid, fromNick: ws.nick, toNick: tw.nick, at: Date.now() };
    inv.timer = setTimeout(() => {
      if (friendInvites.get(inv.fromUid) === inv) {
        friendInvites.delete(inv.fromUid);
        const iw = onlineWsByUid(inv.fromUid); if (iw) try { iw.sendJson({ t: 'friendError', msg: '상대가 응답하지 않습니다' }); } catch (_) {}
        const ow = onlineWsByUid(inv.toUid); if (ow) try { ow.sendJson({ t: 'friendCanceled', from: inv.fromNick }); } catch (_) {}
      }
    }, FRIEND_TTL);
    friendInvites.set(ws.uid, inv);
    ws.sendJson({ t: 'friendInviteSent', to: tw.nick });
    tw.sendJson({ t: 'friendInvited', from: ws.nick, fromUid: ws.uid });
  }
  else if (m.t === 'friendAccept') {
    const fromUid = String(m.fromUid || '');
    const inv = friendInvites.get(fromUid);
    if (!inv || inv.toUid !== ws.uid) { ws.sendJson({ t: 'friendError', msg: '초대가 만료되었습니다' }); return; }
    if (ws.room) { ws.sendJson({ t: 'friendError', msg: '이미 대전 중입니다' }); return; }
    const aw = onlineWsByUid(inv.fromUid);
    if (!aw) { friendInvites.delete(fromUid); if (inv.timer) try { clearTimeout(inv.timer); } catch (_) {} ws.sendJson({ t: 'friendError', msg: '상대가 접속을 종료했습니다' }); return; }
    if (aw.room) { friendInvites.delete(fromUid); if (inv.timer) try { clearTimeout(inv.timer); } catch (_) {} ws.sendJson({ t: 'friendError', msg: '상대가 다른 대전을 시작했습니다' }); return; }
    friendInvites.delete(fromUid); if (inv.timer) try { clearTimeout(inv.timer); } catch (_) {}
    aw.qtime = Date.now() - 1000; ws.qtime = Date.now();   // 초대자를 호스트로
    makeRoom(aw, ws, true);   // 친구전 = 캐주얼(승패·랭킹 미기록)
  }
  else if (m.t === 'friendDecline') {
    const fromUid = String(m.fromUid || '');
    const inv = friendInvites.get(fromUid);
    if (inv && inv.toUid === ws.uid) {
      friendInvites.delete(fromUid); if (inv.timer) try { clearTimeout(inv.timer); } catch (_) {}
      const aw = onlineWsByUid(inv.fromUid); if (aw) try { aw.sendJson({ t: 'friendDeclined', by: ws.nick }); } catch (_) {}
    }
  }
  else if (m.t === 'friendBusy') {   // 상대가 게임 중 등으로 수락 불가 → 초대자에게 사유 통보
    const fromUid = String(m.fromUid || '');
    const inv = friendInvites.get(fromUid);
    if (inv && inv.toUid === ws.uid) {
      friendInvites.delete(fromUid); if (inv.timer) try { clearTimeout(inv.timer); } catch (_) {}
      const aw = onlineWsByUid(inv.fromUid); if (aw) try { aw.sendJson({ t: 'friendBusy', reason: String(m.reason || '').slice(0, 20) }); } catch (_) {}
    }
  }
  else if (m.t === 'friendCancel') { clearInvite(ws.uid, true, 'friendCanceled'); }
}
// 랭킹: 승/무/패 포인트(승×3 + 무×1). 상위 100 + 내 순위(동점=동순위, 100위 밖이어도 조회).
function sendRank(ws) {
  const myUid = ws.uid || '';
  // 동점(같은 점수)이면 '나'를 그 그룹 맨 위로 정렬. (uid=?) DESC 가 pts 다음이라 점수 그룹 내에서만 적용.
  const top = db.prepare("SELECT nick,wins,draws,losses,(wins*3+draws) pts, (uid=?) mine FROM users WHERE is_bot=0 ORDER BY pts DESC, (uid=?) DESC, wins DESC, losses ASC, created ASC LIMIT 100").all(myUid, myUid);
  // 표준 경쟁 순위: 동점이면 같은 순위(1,2,2,2,5,6…). 점수 바뀌는 지점에서 순위=현재 인덱스+1.
  let rank = 0, prevPts = null;
  top.forEach((u, i) => { if (u.pts !== prevPts) { rank = i + 1; prevPts = u.pts; } u.rank = rank; });
  let me = null;
  if (ws.uid) {
    const u = db.prepare("SELECT nick,wins,draws,losses,(wins*3+draws) pts FROM users WHERE uid=?").get(ws.uid);
    if (u) {
      // 내 순위 = 나보다 점수 높은 사람 수 + 1 (동점자와 같은 순위). 표의 내 행 순위와 일치.
      const rankMe = db.prepare("SELECT COUNT(*)+1 r FROM users WHERE is_bot=0 AND (wins*3+draws) > ?").get(u.pts).r;
      const total = db.prepare("SELECT COUNT(*) n FROM users WHERE is_bot=0").get().n;
      me = { rank: rankMe, total, nick: u.nick, wins: u.wins, draws: u.draws, losses: u.losses, pts: u.pts };
    }
  }
  ws.sendJson({ t: 'rank', top, me });
}
function onClose(ws) {
  online.delete(ws);
  dequeue(ws);
  clearInvitesInvolving(ws, '상대가 접속을 종료했습니다');   // 관여한 친구초대 정리(양방향 통보)
  const r = ws.room;
  if (r) {
    if (!r.recorded) {
      // 진행중 대전 끊김 — 즉시 기권 대신 유예(재접속 대기). 유예 안에 돌아오면 이어감(tryResumeRoom), 만료 시 기권.
      if (r._graceUid) return;   // 이미 유예중(양쪽 다 끊김 등) — 타이머가 처리
      const side = (r.a === ws) ? 'a' : 'b';
      r._graceUid = ws.uid || ('anon_' + side);
      r._graceSide = side;
      const other = (side === 'a') ? r.b : r.a;
      if (other && other.room === r) { try { other.sendJson({ t: 'oppDropped', sec: Math.round(GRACE_MS / 1000) }); } catch (_) {} }
      if (r._graceTimer) clearTimeout(r._graceTimer);
      r._graceTimer = setTimeout(function () {
        if (!r.recorded && r._graceUid) { r._graceUid = null; forfeitBySide(r, side, 'timeout'); }
      }, GRACE_MS);
      // ws.room / r.a|r.b 의 죽은 소켓 참조는 유지 → 재접속 시 tryResumeRoom이 교체
    } else { const other = r.a === ws ? r.b : r.a; if (other && other.room === r) other.room = null; activeRooms.delete(r.id); ws.room = null; }
  }
}

// ── 관리자 세션(토큰) ────────────────────────────────────────────────────
const adminSessions = new Map();      // token → 만료시각(ms)
const ADMIN_TTL = 12 * 3600 * 1000;   // 12시간
function adminLogin() {
  const now = Date.now();
  for (const [t, exp] of adminSessions) if (exp <= now) adminSessions.delete(t);   // 만료 청소
  const token = crypto.randomBytes(24).toString('hex');
  adminSessions.set(token, now + ADMIN_TTL);
  return token;
}
function adminAuthed(u, req) {
  const tok = u.searchParams.get('token') || String(req.headers['authorization'] || '').replace(/^Bearer\s+/i, '');
  if (tok && adminSessions.has(tok) && adminSessions.get(tok) > Date.now()) return true;
  if (u.searchParams.get('key') === ADMIN_KEY) return true;   // 하위호환(curl/스크립트)
  return false;
}

// ── 관리자 데이터/액션 ───────────────────────────────────────────────────
function adminData() {
  const now = Date.now();
  let userCount = 0, matchCount = 0, appInstalls = 0, webDevices = 0, activeToday = 0, botCount = 0;
  try { userCount = db.prepare('SELECT COUNT(*) n FROM users WHERE is_bot=0').get().n; } catch (_) {}   // 가입 유저 = 실유저만(봇 제외)
  try { botCount = db.prepare('SELECT COUNT(*) n FROM users WHERE is_bot=1').get().n; } catch (_) {}
  try { matchCount = db.prepare('SELECT COUNT(*) n FROM matches').get().n; } catch (_) {}
  try { appInstalls = db.prepare("SELECT COUNT(*) n FROM installs WHERE platform='app'").get().n; } catch (_) {}
  try { webDevices = db.prepare("SELECT COUNT(*) n FROM installs WHERE platform='web'").get().n; } catch (_) {}
  try { activeToday = db.prepare('SELECT COUNT(*) n FROM installs WHERE last_seen > ?').get(now - 86400000).n; } catch (_) {}
  // 접속 인원 = 로그인한 서로 다른 계정 수(중복 탭/재접속은 1명). 미로그인 소켓은 제외.
  const onlineUids = new Set();
  for (const w of online) if (w.uid) onlineUids.add(w.uid);
  return {
    now,
    online: onlineUids.size,      // 실제 접속 '인원'
    connections: online.size,     // 원시 WS 연결 수(참고)
    userCount, matchCount, botCount,        // userCount=실유저(봇 제외), botCount=봇 수
    appInstalls, webDevices, activeToday,   // 설치(앱)/방문(웹) 기기 수 + 오늘 실행
    // 기기목록(admin '기기' 탭이 소비) — 앱 기기만, 최근 접속순. model/andver는 beacon이 UA에서 파싱해 저장.
    devices: (() => { try { return db.prepare("SELECT cid, platform, first_seen, last_seen, launches, model, andver FROM installs WHERE platform='app' ORDER BY last_seen DESC LIMIT 200").all(); } catch (_) { return []; } })(),
    queue: queue.map((w) => ({ uid: w.uid, nick: w.nick, power: w.power, mode: w.mode || 'ranked', waitMs: now - (w.qtime || now) }))
      .sort((x, y) => y.waitMs - x.waitMs),
    matches: [...activeRooms.values()].map((r) => ({
      id: r.id, durMs: now - r.started, recorded: r.recorded,
      host: { uid: r.a.uid, nick: r.a.nick, power: r.a.power },
      guest: { uid: r.b.uid, nick: r.b.nick, power: r.b.power },
    })),
    // 봇전(서버에 room 없이 로컬 진행) — 대전중으로 잡히게 별도 목록. host=유저, guest=봇(로컬 AI).
    botMatches: [...online].filter((w) => w._botMatch && w.uid).map((w) => ({
      host: { uid: w.uid, nick: w.nick, power: w.power },
      guest: { uid: null, nick: w._botNick || '봇', bot: true },
    })),
    users: db.prepare('SELECT uid,nick,wins,losses,power,is_bot FROM users ORDER BY is_bot ASC, power DESC, wins DESC LIMIT 50').all(),
    recent: db.prepare('SELECT m.id,m.host_uid,m.guest_uid,m.winner_side,m.ended, hu.nick host_nick, gu.nick guest_nick, hu.is_bot host_bot, gu.is_bot guest_bot FROM matches m LEFT JOIN users hu ON hu.uid=m.host_uid LEFT JOIN users gu ON gu.uid=m.guest_uid ORDER BY m.id DESC LIMIT 8').all(),
  };
}
function adminAction(m) {
  if (m.act === 'kick') {                       // 큐에서 추방
    const w = queue.find((x) => x.uid === m.uid);
    if (!w) return { ok: false, err: 'notInQueue' };
    dequeue(w); try { w.sendJson({ t: 'canceled', reason: 'admin' }); } catch (_) {}
    return { ok: true };
  }
  if (m.act === 'forceMatch') {                 // 전투력 무시 강제 매칭
    const a = queue.find((x) => x.uid === m.a), b = queue.find((x) => x.uid === m.b);
    if (!a || !b || a === b) return { ok: false, err: 'notInQueue' };
    makeRoom(a, b); return { ok: true };
  }
  if (m.act === 'endMatch') {                   // 진행중 대전 강제 종료(교착 해소)
    const r = activeRooms.get(m.id | 0);
    if (!r) return { ok: false, err: 'noMatch' };
    for (const s of [r.a, r.b]) { try { s.sendJson({ t: 'oppLeft', reason: 'admin' }); } catch (_) {} s.room = null; }
    activeRooms.delete(r.id); return { ok: true };
  }
  if (m.act === 'ban' || m.act === 'unban') {   // 계정 차단/해제
    const v = m.act === 'ban' ? 1 : 0;
    try { db.prepare('UPDATE users SET banned=? WHERE uid=?').run(v, m.uid); } catch (_) { return { ok: false, err: 'db' }; }
    if (v) {                                     // 차단 즉시: 온라인이면 큐/대전 정리 후 통지
      for (const w of online) if (w.uid === m.uid) {
        dequeue(w);
        if (w.room) { const o = w.room.a === w ? w.room.b : w.room.a; if (o) { o.room = null; try { o.sendJson({ t: 'oppLeft', reason: 'admin' }); } catch (_) {} } activeRooms.delete(w.room.id); w.room = null; }
        try { w.sendJson({ t: 'error', code: 'banned', msg: '차단된 계정입니다' }); } catch (_) {}
      }
    }
    return { ok: true };
  }
  return { ok: false, err: 'unknownAct' };
}

// ── 조회(온디맨드·페이지네이션) — 상시 부담 없음 ─────────────────────────
const USER_SORTS = { power: 'power DESC, wins DESC', wins: 'wins DESC, losses ASC', losses: 'losses DESC', recent: 'created DESC', nick: 'nick COLLATE NOCASE ASC' };
const MATCH_COLS = 'm.id,m.host_uid,m.guest_uid,m.winner_side,m.host_power,m.guest_power,m.dur,m.ended, hu.nick host_nick, gu.nick guest_nick, hu.is_bot host_bot, gu.is_bot guest_bot';
const MATCH_JOIN = 'FROM matches m LEFT JOIN users hu ON hu.uid=m.host_uid LEFT JOIN users gu ON gu.uid=m.guest_uid';
function likeSafe(q) { return '%' + String(q || '').replace(/[%_\\]/g, '') + '%'; }
function adminUsers(q, sort, page) {
  const PAGE = 20; const order = USER_SORTS[sort] || USER_SORTS.power; page = Math.max(1, page || 1);
  const cols = 'uid,nick,wins,losses,power,banned,created,is_bot';
  let total, rows;
  if (q) { const lk = likeSafe(q);
    total = db.prepare('SELECT COUNT(*) n FROM users WHERE nick LIKE ?').get(lk).n;
    rows = db.prepare('SELECT ' + cols + ' FROM users WHERE nick LIKE ? ORDER BY is_bot ASC, ' + order + ' LIMIT ? OFFSET ?').all(lk, PAGE, (page - 1) * PAGE);
  } else {
    total = db.prepare('SELECT COUNT(*) n FROM users').get().n;
    rows = db.prepare('SELECT ' + cols + ' FROM users ORDER BY is_bot ASC, ' + order + ' LIMIT ? OFFSET ?').all(PAGE, (page - 1) * PAGE);
  }
  return { rows, total, page, pageSize: PAGE };
}
function adminUserDetail(uid) {
  const user = db.prepare('SELECT uid,nick,wins,losses,power,banned,created FROM users WHERE uid=?').get(uid);
  if (!user) return { ok: false, err: 'notfound' };
  const matches = db.prepare('SELECT ' + MATCH_COLS + ' ' + MATCH_JOIN + ' WHERE m.host_uid=? OR m.guest_uid=? ORDER BY m.id DESC LIMIT 50').all(uid, uid);
  let live = { online: false, inQueue: false, inMatch: false, vsBot: false };
  for (const w of online) if (w.uid === uid) {
    live.online = true;
    if (queue.includes(w)) live.inQueue = true;
    if (w.room) live.inMatch = true;
    if (w._botMatch) { live.inMatch = true; live.vsBot = true; }   // 봇전도 '대전중'(봇)으로
  }
  return { ok: true, user, matches, live };
}
function adminMatches(page, q) {
  const PAGE = 25; page = Math.max(1, page || 1);
  let total, rows;
  if (q) { const lk = likeSafe(q);
    total = db.prepare('SELECT COUNT(*) n ' + MATCH_JOIN + ' WHERE hu.nick LIKE ? OR gu.nick LIKE ?').get(lk, lk).n;
    rows = db.prepare('SELECT ' + MATCH_COLS + ' ' + MATCH_JOIN + ' WHERE hu.nick LIKE ? OR gu.nick LIKE ? ORDER BY m.id DESC LIMIT ? OFFSET ?').all(lk, lk, PAGE, (page - 1) * PAGE);
  } else {
    total = db.prepare('SELECT COUNT(*) n FROM matches').get().n;
    rows = db.prepare('SELECT ' + MATCH_COLS + ' ' + MATCH_JOIN + ' ORDER BY m.id DESC LIMIT ? OFFSET ?').all(PAGE, (page - 1) * PAGE);
  }
  return { rows, total, page, pageSize: PAGE };
}

// ── 깜짝 이벤트(LiveOps) ─────────────────────────────────────────────────
function activeEvent() {
  try {
    const now = Date.now();
    const row = db.prepare("SELECT * FROM live_events WHERE active=1 ORDER BY id DESC LIMIT 1").get();
    if (!row) return null;
    const endTs = row.start_ts + (row.duration_min || 30) * 60000;
    if (now >= endTs) { try { db.prepare("UPDATE live_events SET active=0 WHERE id=?").run(row.id); } catch (_) {} return null; }
    let generals = [];
    try { generals = row.generals_json ? JSON.parse(row.generals_json) : []; } catch (_) { generals = []; }
    return {
      id: row.id, type: row.type, generalId: row.general_id, generalName: row.general_name,
      generals, stars: row.stars, stageLocal: row.stage_local, stageLabel: row.stage_label,
      recruitPct: row.recruit_pct, rewardStars: row.reward_stars, rewardGold: row.reward_gold,
      freeRecruit: (row.free_recruit == null ? true : !!row.free_recruit),
      testCid: row.test_cid || null,
      title: row.title, body: row.body, startTs: row.start_ts, durationMin: row.duration_min,
      endTs, remainMs: endTs - now,
    };
  } catch (_) { return null; }
}
function createLiveEvent(j) {
  const now = Date.now();
  const type = String(j.type || 'general');   // 'general' | 'star5'
  const durationMin = Math.max(1, Math.min(1440, parseInt(j.durationMin, 10) || 30));
  // 장수 풀(이름 다중선택) — [{id,name}]. 폰마다 랜덤 1명 배정(클라).
  let generals = [];
  try {
    if (Array.isArray(j.generals)) generals = j.generals
      .map((g) => ({ id: String((g && g.id) || ''), name: String((g && g.name) || '') }))
      .filter((g) => g.id);
  } catch (_) { generals = []; }
  // 장(1~20). 미입력(0/빈값) → NULL = 유저 현재 챕터 랜덤 장(클라 결정).
  let stageLocal = parseInt(j.stageLocal, 10);
  if (!(stageLocal >= 1 && stageLocal <= 20)) stageLocal = null;
  const stageLabel = stageLocal ? (stageLocal + '장') : '랜덤 장';
  const freeRecruit = (j.freeRecruit === false) ? 0 : 1;   // 기본 무료(별 차감 없음)
  const ev = {
    type,
    general_id: String((generals[0] && generals[0].id) || ''),
    general_name: String((generals[0] && generals[0].name) || ''),
    stars: parseInt(j.stars, 10) || 5,
    stage_label: stageLabel,
    recruit_pct: Math.max(0, Math.min(100, parseInt(j.recruitPct, 10) || 0)),
    reward_stars: Math.max(0, parseInt(j.rewardStars, 10) || 0),
    reward_gold: Math.max(0, parseInt(j.rewardGold, 10) || 0),
    title: String(j.title || (type === 'star5' ? '⭐ 별 5개 획득 이벤트!' : '⚡ 특별 등용 이벤트!')),
    body: String(j.body || ''),
  };
  // 테스트 모드: 지정 기기(cid)에만 푸시·표시. 빈값이면 전체 공개.
  const testCid = (typeof j.testCid === 'string' && j.testCid.trim()) ? j.testCid.trim().slice(0, 64) : null;
  let id = 0;
  try {
    db.exec("UPDATE live_events SET active=0 WHERE active=1");   // 동시에 하나만 활성
    const r = db.prepare("INSERT INTO live_events(type,general_id,general_name,generals_json,stars,stage_local,stage_id,stage_label,recruit_pct,reward_stars,reward_gold,free_recruit,test_cid,title,body,start_ts,duration_min,active) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,1)")
      .run(ev.type, ev.general_id, ev.general_name, JSON.stringify(generals), ev.stars, stageLocal, '', ev.stage_label, ev.recruit_pct, ev.reward_stars, ev.reward_gold, freeRecruit, testCid, ev.title, ev.body, now, durationMin);
    id = Number(r.lastInsertRowid);
  } catch (e) { return { ok: false, err: String((e && e.message) || e) }; }
  const pushBody = ev.body || ('지금 접속하세요! ' + durationMin + '분 한정');
  const sent = broadcastEventPush(ev.title, pushBody, { kind: 'live_event', eventId: String(id) }, testCid);
  return { ok: true, id, test: !!testCid, tokens: sent };
}
function pushTokenCount() {
  try { return db.prepare("SELECT COUNT(*) c FROM push_tokens").get().c; } catch (_) { return 0; }
}
function broadcastEventPush(title, body, data, targetCid) {
  if (!fcm.fcmEnabled()) return 0;
  let tokens = [];
  try {
    tokens = (targetCid
      ? db.prepare("SELECT token FROM push_tokens WHERE cid=?").all(targetCid)
      : db.prepare("SELECT token FROM push_tokens").all()).map((r) => r.token);
  } catch (_) {}
  tokens.forEach((tok) => {
    fcm.sendToToken(tok, { title, body }, data).catch((e) => {
      const msg = String((e && e.message) || e);
      if (msg.indexOf('UNREGISTERED') >= 0 || msg.indexOf('INVALID_ARGUMENT') >= 0 || msg.indexOf('"code": 404') >= 0 || msg.indexOf(' 404 ') >= 0) {
        try { db.prepare("DELETE FROM push_tokens WHERE token=?").run(tok); } catch (_) {}
      }
    });
  });
  return tokens.length;
}

server.listen(PORT, () => console.log('[mp_server] listening on :' + PORT + '  (public=' + PUB + ', admin=/admin key=' + (process.env.ADMIN_KEY ? '****' : ADMIN_KEY) + ')'));
