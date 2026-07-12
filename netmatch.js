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
//   Guest→Host  HELLO { loadout? }   // 참가 + (메타)장수 로드아웃 전달
//   Guest→Host  SURRENDER {}
//
// 메타(장수 로드아웃): opts.hostLoadout이 있으면 pvp 메타 모드. 호스트는 게스트의 HELLO로
//   상대 로드아웃을 받은 뒤에야 엔진을 생성(양측 보정 주입). 로드아웃은 engine이 클램프(치팅방지).

import { SimEngine } from './engine.js';

// ── 호스트: 권위 시뮬 + 양측 명령 적용 + 스냅샷 방송 ──────────────────────
export class HostMatch {
  constructor(mapDef, seed, channel, opts = {}) {
    this.channel = channel;
    this.seed = seed >>> 0;
    this.mapDef = mapDef;
    this.hostSide = opts.hostSide || 1;    // 호스트가 조종하는 진영
    this.guestSide = opts.guestSide || 2;  // 게스트가 조종하는 진영
    this.stepDt = 1 / 15;
    this.snapEvery = opts.snapEvery || 2;  // n틱마다 스냅샷(2 → ~7.5Hz)
    this._sinceSnap = 0;
    this.over = false;
    // 메타 로드아웃(옵션). 있으면 게스트 로드아웃 수신 후 엔진 생성.
    this.hostLoadout = opts.hostLoadout || null;
    this.useLoadouts = !!this.hostLoadout;
    this.guestLoadout = null;
    this.eng = this.useLoadouts ? null : new SimEngine(mapDef, this.seed);  // 비메타: 기존처럼 즉시 생성
    channel.onMessage((m) => this._onGuest(m));
  }
  _buildEngine() {
    const engOpts = {};
    if (this.useLoadouts) {
      engOpts.loadouts = {};
      engOpts.loadouts[this.hostSide] = this.hostLoadout;
      engOpts.loadouts[this.guestSide] = this.guestLoadout || { upg: {}, generals: [] };
    }
    this.eng = new SimEngine(this.mapDef, this.seed, engOpts);
  }
  start() {
    this.channel.send({ t: 'START', seed: this.seed, map: this.mapDef, youSide: this.guestSide });
    if (this.eng) this._broadcast();   // 비메타: 엔진 준비됨. 메타: 게스트 HELLO 후 방송.
  }
  hostCommand(cmd) { this._applyCommand(cmd, this.hostSide); }   // 로컬(호스트) 플레이어 입력
  _onGuest(m) {
    if (!m) return;
    if (m.t === 'HELLO') { // 게스트 참가(+로드아웃) → 필요시 엔진생성, 매치정보+현재상태 (재)전송
      if (m.loadout && this.useLoadouts) this.guestLoadout = m.loadout;
      if (!this.eng) this._buildEngine();
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
    if (this.over || !this.eng || !cmd || cmd.type !== 'SEND_ARMY') return;
    const from = this.eng.castles[cmd.fromId];
    if (!from || from.owner !== side) return;
    this.eng.enqueue('net', { type: 'SEND_ARMY', fromId: cmd.fromId, toId: cmd.toId, unit: cmd.unit });
  }
  _forceWin(side, reason) {
    if (this.over) return;
    if (this.eng) this.eng.winner = side;
    this.over = true;
    this._broadcast();
    this.channel.send({ t: 'END', winner: side, reason });
  }
  // 고정 15Hz 스텝 — 호스트 루프가 매 틱 호출
  tick() {
    if (this.over || !this.eng) return;
    const ev = this.eng.step(this.stepDt);
    if (++this._sinceSnap >= this.snapEvery) { this._broadcast(); this._sinceSnap = 0; }
    if (this.eng.winner != null) {
      this.over = true;
      this._broadcast();
      const w = ev.find((e) => e.type === 'win');
      this.channel.send({ t: 'END', winner: this.eng.winner, reason: (w && w.reason) || 'homeCapture' });
    }
  }
  _broadcast() { if (!this.eng) return; this.channel.send({ t: 'STATE', tick: this.eng.tick, snap: this.eng.snapshot() }); }
}

// ── 게스트: 명령 송신 + 권위 스냅샷 수신/보관(렌더용) ──────────────────────
export class GuestMatch {
  constructor(channel, opts = {}) {
    this.channel = channel;
    this.loadout = opts.loadout || null;   // 내 장수 로드아웃(메타). join 시 호스트에 전달.
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
  join() { this.channel.send({ t: 'HELLO', loadout: this.loadout || undefined }); }  // 참가 + (메타)로드아웃 전달
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
