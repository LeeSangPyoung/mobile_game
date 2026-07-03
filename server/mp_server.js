// mp_server.js — 손가락삼국지 실시간 1v1 중계서버 (의존성 0: Node 내장만 사용)
//   기능: 정적파일 서빙 + WebSocket 중계 + 매칭 큐 + 닉네임(중복체크) + 전적(승/패)
//   실행: node mp_server.js   (환경변수 PORT, 기본 8080)
//   요구: Node 22+ (node:sqlite 내장). 배포: 이 폴더 통째로 복사 후 실행. npm install 불필요.
'use strict';
const http = require('http');
const crypto = require('crypto');
const fs = require('fs');
const path = require('path');
const { DatabaseSync } = require('node:sqlite');

const PORT = Number(process.env.PORT || 8080);
const PUB = path.join(__dirname, 'public');
const db = new DatabaseSync(process.env.DB_PATH || path.join(__dirname, 'mp.db'));
db.exec("CREATE TABLE IF NOT EXISTS users(uid TEXT PRIMARY KEY, nick TEXT UNIQUE, wins INTEGER DEFAULT 0, losses INTEGER DEFAULT 0, created INTEGER)");
db.exec("CREATE TABLE IF NOT EXISTS matches(id INTEGER PRIMARY KEY AUTOINCREMENT, host_uid TEXT, guest_uid TEXT, winner_side INTEGER, ended INTEGER)");

// ── 정적 파일 ────────────────────────────────────────────────────────────
const MIME = { '.html':'text/html; charset=utf-8', '.js':'text/javascript; charset=utf-8', '.css':'text/css; charset=utf-8',
  '.png':'image/png', '.jpg':'image/jpeg', '.jpeg':'image/jpeg', '.webp':'image/webp', '.svg':'image/svg+xml',
  '.json':'application/json; charset=utf-8', '.ogg':'audio/ogg', '.woff2':'font/woff2' };
const server = http.createServer((req, res) => {
  let p = decodeURIComponent((req.url || '/').split('?')[0]);
  if (p === '/' || p === '') p = '/mp_game.html';
  if (p === '/health') { res.writeHead(200); res.end('ok'); return; }
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
function attach(socket) {
  const ws = { socket, uid: null, nick: null, room: null,
    sendJson(o) { wsSend(socket, Buffer.from(JSON.stringify(o))); }, close() { try { socket.end(); } catch (_) {} } };
  let buf = Buffer.alloc(0);
  socket.on('data', (d) => {
    buf = Buffer.concat([buf, d]);
    for (;;) {
      const f = decodeFrame(buf); if (!f) break; buf = f.rest;
      if (f.opcode === 0x8) { onClose(ws); ws.close(); return; }
      if (f.opcode === 0x9) { wsSend(socket, f.payload, 0xA); continue; }   // ping→pong
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
let queue = [];
function dequeue(ws) { queue = queue.filter((x) => x !== ws); }
function enqueue(ws) {
  dequeue(ws);
  queue.push(ws);
  if (queue.length >= 2) {
    const a = queue.shift(), b = queue.shift();   // a=먼저 온 쪽=호스트
    const room = { a, b, recorded: false }; a.room = room; b.room = room;
    a.sendJson({ t: 'matched', role: 'host', opp: b.nick });
    b.sendJson({ t: 'matched', role: 'guest', opp: a.nick });
  } else {
    ws.sendJson({ t: 'queued' });
  }
}
function sendStats(ws) {
  if (!ws || !ws.uid) return;
  const u = db.prepare('SELECT wins,losses FROM users WHERE uid=?').get(ws.uid);
  if (u) ws.sendJson({ t: 'stats', wins: u.wins, losses: u.losses });
}
function recordResult(ws, winnerSide) {
  const room = ws.room; if (!room || room.recorded) return;
  if (ws !== room.a) return;                       // 호스트(권위)만 기록
  room.recorded = true;
  const hostU = room.a.uid, guestU = room.b.uid;
  const winU = winnerSide === 1 ? hostU : guestU, loseU = winnerSide === 1 ? guestU : hostU;
  try {
    if (winU) db.prepare('UPDATE users SET wins=wins+1 WHERE uid=?').run(winU);
    if (loseU) db.prepare('UPDATE users SET losses=losses+1 WHERE uid=?').run(loseU);
    db.prepare('INSERT INTO matches(host_uid,guest_uid,winner_side,ended) VALUES(?,?,?,?)').run(hostU, guestU, winnerSide, Date.now());
  } catch (_) {}
  sendStats(room.a); sendStats(room.b);
}
function onMessage(ws, m) {
  if (!m || typeof m.t !== 'string') return;
  if (m.t === 'hello') {
    if (m.uid) { const u = db.prepare('SELECT * FROM users WHERE uid=?').get(m.uid); if (u) { ws.uid = u.uid; ws.nick = u.nick; ws.sendJson({ t: 'welcome', uid: u.uid, nick: u.nick, wins: u.wins, losses: u.losses }); return; } }
    if (m.nick != null) {
      const nick = String(m.nick).trim().slice(0, 16);
      if (!nick) { ws.sendJson({ t: 'error', code: 'nick', msg: '닉네임을 입력하세요' }); return; }
      if (db.prepare('SELECT uid FROM users WHERE nick=?').get(nick)) { ws.sendJson({ t: 'error', code: 'dup', msg: '이미 사용중인 닉네임입니다' }); return; }
      const uid = 'u' + crypto.randomBytes(8).toString('hex');
      try { db.prepare('INSERT INTO users(uid,nick,wins,losses,created) VALUES(?,?,0,0,?)').run(uid, nick, Date.now()); }
      catch (_) { ws.sendJson({ t: 'error', code: 'dup', msg: '이미 사용중인 닉네임입니다' }); return; }
      ws.uid = uid; ws.nick = nick; ws.sendJson({ t: 'welcome', uid, nick, wins: 0, losses: 0 }); return;
    }
    ws.sendJson({ t: 'error', code: 'login', msg: '로그인 실패' });
  }
  else if (m.t === 'queue') { if (!ws.uid) { ws.sendJson({ t: 'error', code: 'noauth', msg: '닉네임 등록 필요' }); return; } enqueue(ws); }
  else if (m.t === 'cancel') { dequeue(ws); ws.sendJson({ t: 'canceled' }); }
  else if (m.t === 'relay') { const r = ws.room; if (r) { const other = r.a === ws ? r.b : r.a; if (other) other.sendJson({ t: 'relay', m: m.m }); } }
  else if (m.t === 'result') { recordResult(ws, m.winner | 0); }
  else if (m.t === 'stats') { sendStats(ws); }
}
function onClose(ws) {
  dequeue(ws);
  const r = ws.room;
  if (r) {
    const other = r.a === ws ? r.b : r.a;
    if (other && other.room === r) { other.room = null; try { other.sendJson({ t: 'oppLeft' }); } catch (_) {} }
    ws.room = null;
  }
}

server.listen(PORT, () => console.log('[mp_server] listening on :' + PORT + '  (public=' + PUB + ')'));
