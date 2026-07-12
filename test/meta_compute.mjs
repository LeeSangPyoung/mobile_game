// test/meta_compute.mjs — meta.js(SAVE→로드아웃/전투력) 공식 검증 (Node)
//   실행: node test/meta_compute.mjs
import { buildRoster, computeLoadout, computePower, activeDeployUids, UPG_PER } from '../meta.js';
import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

let pass = 0, fail = 0;
const check = (n, c) => { if (c) { pass++; console.log('  ✅ ' + n); } else { fail++; console.log('  ❌ ' + n); } };
const approx = (a, b, e = 1e-6) => Math.abs(a - b) < e;

// 실제 GENERALS_200 로드(assets/generals/roster_200.js는 window.GENERALS_200=... 형태)
const root = path.dirname(path.dirname(fileURLToPath(import.meta.url)));
const rosterSrc = fs.readFileSync(path.join(root, 'assets/generals/roster_200.js'), 'utf8');
const g200 = Function('var window={};' + rosterSrc + ';return window.GENERALS_200;')();
const roster = buildRoster(g200);

console.log('── 1) 로스터 구성 ──');
check('GENERALS_200 로드(>100)', Array.isArray(g200) && g200.length > 100);
check('로스터 구성됨', roster.length > 100);
check('명장 수동버프 적용(관우 unitAtk=0.10)', roster.find((g) => g.id === 'guan_yu').buffs.unitAtk === 0.10);
check('일반장수 절차버프 존재', Object.keys(roster.find((g) => !['guan_yu','liu_bei','cao_cao'].includes(g.id)).buffs).length >= 2);

console.log('── 2) 편성 해석(활성 포메이션 우선) ──');
{
  const save = { formations: { '天': ['u1', 'u2'], '地': ['u3'], '人': [] }, activeFormation: '地',
    generals: [{ uid: 'u1', id: 'guan_yu', lv: 1, stars: 1 }, { uid: 'u3', id: 'liu_bei', lv: 1, stars: 1 }] };
  check('활성 포메이션(地)의 uid 사용', JSON.stringify(activeDeployUids(save)) === JSON.stringify(['u3']));
}

console.log('── 3) generalBuff 공식(강화·별 배수) ──');
{
  // 관우 unitAtk base 0.10. lv3(×1.4), 3성(×1.4) + STAR_FLAT[3]=0.025 → 0.10*1.4*1.4 + 0.025 = 0.196+0.025 = 0.221
  const save = { generals: [{ uid: 'u1', id: 'guan_yu', lv: 3, stars: 3 }], lastDeployGenerals: ['u1'] };
  const lo = computeLoadout(save, roster);
  check('편성 장수 1명', lo.generals.length === 1);
  check('관우 lv3/3성 unitAtk = 0.221', approx(lo.generals[0].atk, 0.10 * 1.4 * 1.4 + 0.025));
  // 크리(3성 base .12/1.55, lv3 → +0.012/+0.016) = 0.132 / 1.566
  check('관우 crit chance ≈ 0.132', approx(lo.generals[0].critChance, Math.min(0.40, 0.12 + 0.012)));
  check('관우 crit mult ≈ 1.566', approx(lo.generals[0].critMult, Math.min(2.0, 1.55 + 0.016)));
}

console.log('── 4) 업그레이드 upgVal 공식 ──');
{
  const save = { upgrades: { unitAtk: 5, castleDef: 3 }, generals: [], lastDeployGenerals: [] };
  const lo = computeLoadout(save, roster);
  check('unitAtk 5레벨 = 1 + 5×0.06 = 1.30', approx(lo.upg.unitAtk, 1 + 5 * UPG_PER.unitAtk));
  check('castleDef 3레벨 = 1 + 3×0.10 = 1.30', approx(lo.upg.castleDef, 1 + 3 * UPG_PER.castleDef));
  check('미투자 항목=1', lo.upg.prodRate === 1);
  check('장수 0명', lo.generals.length === 0);
}

console.log('── 5) 전투력 단조성(강할수록 높다) ──');
{
  const empty = computePower(computeLoadout({ generals: [], lastDeployGenerals: [] }, roster));
  const oneWeak = computePower(computeLoadout({ generals: [{ uid: 'a', id: 'cao_xing', lv: 1, stars: 1 }], lastDeployGenerals: ['a'] }, roster));
  const strong = computePower(computeLoadout({
    upgrades: { unitAtk: 10, castleAtk: 10, prodRate: 10 },
    generals: [
      { uid: 'a', id: 'guan_yu', lv: 6, stars: 5 }, { uid: 'b', id: 'lu_bu', lv: 6, stars: 5 },
      { uid: 'c', id: 'zhao_yun', lv: 5, stars: 4 },
    ], lastDeployGenerals: ['a', 'b', 'c'],
  }, roster));
  console.log('     전투력: 빈편성=' + empty + ' / 약장1=' + oneWeak + ' / 강편성=' + strong);
  check('기본 전투력 1000', empty === 1000);
  check('장수 있으면 > 기본', oneWeak > empty);
  check('강편성 >> 약편성', strong > oneWeak + 500);
}

console.log('\n결과: ' + pass + ' 통과 / ' + fail + ' 실패');
process.exit(fail ? 1 : 0);
