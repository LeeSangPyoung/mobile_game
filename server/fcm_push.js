// fcm_push.js — FCM HTTP v1 발송 (의존성 0, Node 내장만). 우리반 ExpoPushService.java 이식.
//   서비스계정(JWT RS256) → OAuth2 액세스토큰(캐시) → fcm.googleapis.com/v1/.../messages:send
//   재활용 프로젝트: ourclass-c2ec6 (서비스계정 키 공유). 안드로이드 전용(iOS 미지원).
'use strict';
const fs = require('fs');
const path = require('path');
const crypto = require('crypto');

const SA_PATH = process.env.FIREBASE_SA_PATH
  || path.join(__dirname, 'secrets', 'firebase-service-account.json');

let _sa = null;
function serviceAccount() {
  if (_sa) return _sa;
  _sa = JSON.parse(fs.readFileSync(SA_PATH, 'utf8'));
  return _sa;
}
function fcmEnabled() {
  try { return fs.existsSync(SA_PATH); } catch (_) { return false; }
}

function b64url(input) {
  return Buffer.from(input).toString('base64')
    .replace(/\+/g, '-').replace(/\//g, '_').replace(/=+$/, '');
}

let _tok = { value: '', exp: 0 };
async function getAccessToken() {
  const now = Math.floor(Date.now() / 1000);
  if (_tok.value && now < _tok.exp - 60) return _tok.value;   // 캐시(만료 60초 전까지)
  const sa = serviceAccount();
  const header = b64url(JSON.stringify({ alg: 'RS256', typ: 'JWT' }));
  const claim = b64url(JSON.stringify({
    iss: sa.client_email,
    scope: 'https://www.googleapis.com/auth/firebase.messaging',
    aud: 'https://oauth2.googleapis.com/token',
    iat: now, exp: now + 3600,
  }));
  const signInput = header + '.' + claim;
  const signer = crypto.createSign('RSA-SHA256');
  signer.update(signInput); signer.end();
  const jwt = signInput + '.' + b64url(signer.sign(sa.private_key));

  const body = 'grant_type=' + encodeURIComponent('urn:ietf:params:oauth:grant-type:jwt-bearer')
    + '&assertion=' + encodeURIComponent(jwt);
  const res = await fetch('https://oauth2.googleapis.com/token', {
    method: 'POST',
    headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
    body,
  });
  const j = await res.json();
  if (!res.ok || !j.access_token) {
    throw new Error('OAuth2 token 실패: ' + res.status + ' ' + JSON.stringify(j));
  }
  _tok = { value: j.access_token, exp: now + (j.expires_in || 3600) };
  return _tok.value;
}

// 공통 발송. target = { topic } 또는 { token }
async function sendMessage(target, notification, data) {
  const sa = serviceAccount();
  const token = await getAccessToken();
  const message = Object.assign({}, target, {
    notification: notification || undefined,
    data: data ? Object.fromEntries(Object.entries(data).map(([k, v]) => [k, String(v)])) : undefined,
    android: { priority: 'high', notification: { channel_id: 'events' } },
  });
  const url = 'https://fcm.googleapis.com/v1/projects/' + sa.project_id + '/messages:send';
  const res = await fetch(url, {
    method: 'POST',
    headers: { 'Authorization': 'Bearer ' + token, 'Content-Type': 'application/json' },
    body: JSON.stringify({ message }),
  });
  const j = await res.json().catch(() => ({}));
  if (!res.ok) throw new Error('FCM send 실패: ' + res.status + ' ' + JSON.stringify(j));
  return j;   // { name: "projects/ourclass-c2ec6/messages/..." }
}

function sendToTopic(topic, notification, data) {
  return sendMessage({ topic }, notification, data);
}
function sendToToken(fcmToken, notification, data) {
  return sendMessage({ token: fcmToken }, notification, data);
}

module.exports = { fcmEnabled, getAccessToken, sendToTopic, sendToToken, sendMessage };
