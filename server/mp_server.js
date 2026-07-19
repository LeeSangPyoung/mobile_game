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

const PORT = Number(process.env.PORT || 8080);
const ADMIN_KEY = process.env.ADMIN_KEY || 'samguk-admin';
const PUB = path.join(__dirname, 'public');
const db = new DatabaseSync(process.env.DB_PATH || path.join(__dirname, 'mp.db'));
db.exec("CREATE TABLE IF NOT EXISTS users(uid TEXT PRIMARY KEY, nick TEXT UNIQUE, wins INTEGER DEFAULT 0, losses INTEGER DEFAULT 0, created INTEGER)");
db.exec("CREATE TABLE IF NOT EXISTS matches(id INTEGER PRIMARY KEY AUTOINCREMENT, host_uid TEXT, guest_uid TEXT, winner_side INTEGER, ended INTEGER)");
// 설치/실행 집계 — 앱·게임 실행 시 기기 고유 id(cid) 비콘. platform=app|web.
db.exec("CREATE TABLE IF NOT EXISTS installs(cid TEXT PRIMARY KEY, platform TEXT, first_seen INTEGER, last_seen INTEGER, launches INTEGER DEFAULT 0)");
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
    if (m.uid) { const u = db.prepare('SELECT * FROM users WHERE uid=?').get(m.uid); if (u) { if (u.banned) { ws.sendJson({ t: 'error', code: 'banned', msg: '차단된 계정입니다' }); return; } ws.uid = u.uid; ws.nick = u.nick; ws.power = u.power || DEFAULT_POWER; ws.sendJson({ t: 'welcome', uid: u.uid, nick: u.nick, wins: u.wins, losses: u.losses, power: u.power, draws: u.draws }); try { tryResumeRoom(ws); } catch (_) {} try { evictStaleSessions(ws); } catch (_) {}  return; } }
    if (m.nick != null) {
      const v = validateNick(m.nick);
      if (v.err) { ws.sendJson({ t: 'error', code: 'nick', msg: v.err }); return; }
      const nick = v.nick;
      if (db.prepare('SELECT uid FROM users WHERE nick=?').get(nick)) { ws.sendJson({ t: 'error', code: 'dup', msg: '이미 사용중인 닉네임입니다' }); return; }
      const uid = 'u' + crypto.randomBytes(8).toString('hex');
      try { db.prepare('INSERT INTO users(uid,nick,wins,losses,created,power) VALUES(?,?,0,0,?,?)').run(uid, nick, Date.now(), DEFAULT_POWER); }
      catch (_) { ws.sendJson({ t: 'error', code: 'dup', msg: '이미 사용중인 닉네임입니다' }); return; }
      ws.uid = uid; ws.nick = nick; ws.power = DEFAULT_POWER; ws.sendJson({ t: 'welcome', uid, nick, wins: 0, losses: 0, power: DEFAULT_POWER, draws: 0 }); return;
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

server.listen(PORT, () => console.log('[mp_server] listening on :' + PORT + '  (public=' + PUB + ', admin=/admin key=' + (process.env.ADMIN_KEY ? '****' : ADMIN_KEY) + ')'));
