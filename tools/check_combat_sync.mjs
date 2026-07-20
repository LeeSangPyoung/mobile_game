// tools/check_combat_sync.mjs — 싱글(prototype.html)과 멀티(engine.js)의 전투 상수가
//   같은지 검사한다. 다르면 빌드를 중단시킨다.
//
//   왜 필요한가: 전투 엔진이 두 벌(prototype.html = 싱글, engine.js = 온라인 대전)이라
//   밸런스 숫자를 한쪽만 고쳐도 아무 에러 없이 조용히 달라진다. 온라인 대전은 락스텝이라
//   두 기기의 계산이 어긋나면 승패가 서로 다르게 보이는 데스싱크가 난다.
//   실제로 SPEAR_TANK(창병 탱커)와 SHOOT_RANGE(궁병 사거리)가 이렇게 어긋난 적이 있다.
//
//   실행: node tools/check_combat_sync.mjs   (build_mp_server_client.mjs가 자동 호출)

import fs from 'fs';
import path from 'path';
import { fileURLToPath } from 'url';

// 두 엔진이 반드시 같아야 하는 전투 상수. 밸런스 상수를 새로 만들면 여기에 추가할 것.
const KEYS = [
  'SHOOT_RANGE',    // 궁병 사거리
  'ENGAGE_DIST',    // 근접 교전 거리
  'DMG_RATE',       // 근접 피해 배율
  'ENGAGE_WARMUP',  // 교전 예열 시간
  'SPEAR_TANK',     // 창병 피해 감소
  'SPEAR_SIEGE',    // 창병 공성 배수
];

// `const NAME = ...;` 에서 값을 뽑는다. prototype.html은 `() => 200 * ...`, engine.js는
// `200 * ...` 형태라 화살표 함수 껍데기와 공백을 벗겨 같은 모양으로 만든 뒤 비교한다.
function readConst(src, key) {
  const m = src.match(new RegExp('const\\s+' + key + '\\s*=\\s*([^;]+);'));
  if (!m) return null;
  return m[1]
    .replace(/^\(\s*\)\s*=>\s*/, '')   // `() =>` 제거
    .replace(/\/\/.*$/gm, '')          // 줄 끝 주석 제거
    .replace(/\s+/g, '')               // 공백 전부 제거
    .trim();
}

export function checkCombatSync(root) {
  const proto = fs.readFileSync(path.join(root, 'prototype.html'), 'utf8');
  const engine = fs.readFileSync(path.join(root, 'engine.js'), 'utf8');

  const bad = [];
  for (const key of KEYS) {
    const a = readConst(proto, key);
    const b = readConst(engine, key);
    if (a === null || b === null) {
      bad.push({ key, a: a === null ? '(없음)' : a, b: b === null ? '(없음)' : b, why: '상수를 찾지 못함' });
    } else if (a !== b) {
      bad.push({ key, a, b, why: '값이 다름' });
    }
  }

  if (bad.length) {
    console.error('\n❌ 전투 상수 불일치 — 빌드 중단');
    console.error('   싱글(prototype.html)과 멀티(engine.js)의 전투 숫자가 어긋났습니다.');
    console.error('   이대로 두면 온라인 대전에서 승패가 서로 다르게 보일 수 있습니다.\n');
    for (const d of bad) {
      console.error(`   ${d.key}  (${d.why})`);
      console.error(`      prototype.html : ${d.a}`);
      console.error(`      engine.js      : ${d.b}`);
    }
    console.error('\n   → 양쪽을 같은 값으로 맞춘 뒤 다시 빌드하세요.\n');
    return false;
  }

  console.log(`전투 상수 동기화 확인: ${KEYS.length}개 일치 (싱글 ↔ 멀티)`);
  return true;
}

// 단독 실행 시
if (process.argv[1] && path.resolve(process.argv[1]) === path.resolve(fileURLToPath(import.meta.url))) {
  const root = path.dirname(path.dirname(fileURLToPath(import.meta.url)));
  process.exit(checkCombatSync(root) ? 0 : 1);
}
