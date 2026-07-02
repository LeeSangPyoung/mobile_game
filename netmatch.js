// netmatch.js — 호스트 권위 실시간 1v1 대전 넷코드 (전송 계층 비의존)
//
// 설계문서 §4: P2P 호스트 권위. 호스트 폰이 진짜 시뮬(engine.js)을 돌리고,
//   게스트는 명령만 보내고 호스트가 준 상태를 렌더. 여기서는 '전송(channel)'을 주입받아
//   BroadcastChannel(같은 PC 2탭) / WebRTC DataChannel(원격) 어느 것과도 동작한다.
//
// channel 인터페이스: { send(msgObj), onMessage(cb) }  (직렬화는 채널이 담당)
//
// 프로토콜:
//   Host→Guest  START { seed, map, youSide }
//   Host→Guest  STATE { tick, snap }              // 권위 스냅샷(주기적)
//   Host→Guest  END   { winner, reason }
//   Guest→Host  CMD   { cmd:{type:'SEND_ARMY',fromId,toId,unit} }
//   Guest→Host  SURRENDER {}

import { SimEngine } from './engine.js';

// ── 호스트: 권위 시뮬 + 양측 명령 적용 + 스냅샷 방송 ──────────────────────
export class HostMatch {
  constructor(mapDef, seed, channel, opts = {}) {
    this.channel = channel;
    this.seed = seed >>> 0;
    this.mapDef = mapDef;
    this.eng = new SimEngine(mapDef, this.seed);
    this.hostSide = opts.hostSide || 1;    // 호스트가 조종하는 진영
    this.guestSide = opts.guestSide || 2;  // 게스트가 조종하는 진영
    this.stepDt = 1 / 15;
    this.snapEvery = opts.snapEvery || 2;  // n틱마다 스냅샷(2 → ~7.5Hz)
    this._sinceSnap = 0;
    this.over = false;
    channel.onMessage((m) => this._onGuest(m));
  }
  start() {
    this.channel.send({ t: 'START', seed: this.seed, map: this.mapDef, youSide: this.guestSide });
    this._broadcast();
  }
  hostCommand(cmd) { this._applyCommand(cmd, this.hostSide); }   // 로컬(호스트) 플레이어 입력
  _onGuest(m) {
    if (!m) return;
    if (m.t === 'HELLO') { // 게스트 늦참가 → 매치정보+현재상태 재전송
      this.channel.send({ t: 'START', seed: this.seed, map: this.mapDef, youSide: this.guestSide });
      this._broadcast();
      return;
    }
    if (this.over) return;
    if (m.t === 'CMD') this._applyCommand(m.cmd, this.guestSide);
    else if (m.t === 'SURRENDER') this._forceWin(this.hostSide, 'surrender');
  }
  // 명령 검증 — 해당 사이드의 성만 조종 가능(치팅 방지: 소유권 확인)
  _applyCommand(cmd, side) {
    if (this.over || !cmd || cmd.type !== 'SEND_ARMY') return;
    const from = this.eng.castles[cmd.fromId];
    if (!from || from.owner !== side) return;
    this.eng.enqueue('net', { type: 'SEND_ARMY', fromId: cmd.fromId, toId: cmd.toId, unit: cmd.unit });
  }
  _forceWin(side, reason) {
    if (this.over) return;
    this.eng.winner = side; this.over = true;
    this._broadcast();
    this.channel.send({ t: 'END', winner: side, reason });
  }
  // 고정 15Hz 스텝 — 호스트 루프가 매 틱 호출
  tick() {
    if (this.over) return;
    const ev = this.eng.step(this.stepDt);
    if (++this._sinceSnap >= this.snapEvery) { this._broadcast(); this._sinceSnap = 0; }
    if (this.eng.winner != null) {
      this.over = true;
      this._broadcast();
      const w = ev.find((e) => e.type === 'win');
      this.channel.send({ t: 'END', winner: this.eng.winner, reason: (w && w.reason) || 'homeCapture' });
    }
  }
  _broadcast() { this.channel.send({ t: 'STATE', tick: this.eng.tick, snap: this.eng.snapshot() }); }
}

// ── 게스트: 명령 송신 + 권위 스냅샷 수신/보관(렌더용) ──────────────────────
export class GuestMatch {
  constructor(channel, opts = {}) {
    this.channel = channel;
    this.youSide = null;
    this.map = null; this.seed = null;
    this.snap = null; this.prevSnap = null; this.lastRecvAt = 0;
    this.winner = null; this.reason = null; this.over = false;
    this.onStart = opts.onStart || (() => {});
    this.onState = opts.onState || (() => {});
    this.onEnd = opts.onEnd || (() => {});
    channel.onMessage((m) => this._onHost(m));
  }
  _onHost(m) {
    if (!m) return;
    if (m.t === 'START') { this.seed = m.seed; this.map = m.map; this.youSide = m.youSide; this.onStart(m); }
    else if (m.t === 'STATE') { this.prevSnap = this.snap; this.snap = m.snap; this.onState(m); }
    else if (m.t === 'END') { this.over = true; this.winner = m.winner; this.reason = m.reason; this.onEnd(m); }
  }
  join() { this.channel.send({ t: 'HELLO' }); }                          // 참가 시 호스트에 상태 요청
  command(cmd) { if (!this.over) this.channel.send({ t: 'CMD', cmd }); } // 호스트로 전송(권위는 호스트)
  surrender() { this.channel.send({ t: 'SURRENDER' }); }
}

// ── 인메모리 페어 채널 (테스트/같은-프로세스용). 직렬화 왕복 포함. ──────────
export function makeLoopbackPair() {
  const ends = [{ cb: null }, { cb: null }];
  const mk = (self, other) => ({
    onMessage(cb) { self.cb = cb; },
    send(msg) { const copy = JSON.parse(JSON.stringify(msg)); if (other.cb) other.cb(copy); },
  });
  return [mk(ends[0], ends[1]), mk(ends[1], ends[0])];
}
