// meta.js — 순수 메타 계산: SAVE(장수 로스터·강화·편성·업그레이드) → 엔진 로드아웃 + 전투력.
//   브라우저·Node 공용(DOM 의존 0). 공식은 prototype.html 배선층과 1:1 일치.
//
//   loadout 형식(engine.js가 소비): { upg:{unitAtk,unitDef,castleAtk,castleDef,prodRate},
//     generals:[{atk,def,cAtk,cDef,prod,critChance,critMult}] }   (각 값은 '분수'/확률, 엔진에서 1+ 처리)
//
//   상위문서: docs/multiplayer_realtime_design.md §1(보유 로스터에서 장수 10명 편성)

export const MAX_DEPLOY_GENERALS = 10;
// 계정 업그레이드(단련소) 레벨당 효과 — prototype UPG_DEFS.per 일치
export const UPG_PER = { castleAtk: 0.08, castleDef: 0.10, prodRate: 0.10, unitAtk: 0.06, unitDef: 0.05 };
export const GENERAL_BUFF_KEYS = ['unitAtk', 'unitDef', 'castleAtk', 'castleDef', 'prodRate'];
// 별 등급/강화 배수 — prototype 상수 일치 (index = stars(1~5) / lv(1~6))
const STAR_MULT = [1.0, 1.0, 1.2, 1.4, 1.7, 2.0];
const STAR_FLAT = [0, 0, 0.012, 0.025, 0.045, 0.075];
const ENHANCE_MULT = [1.0, 1.0, 1.2, 1.4, 1.6, 1.8, 2.0];
const FORMATION_KEYS = ['天', '地', '人'];

// 명장 수동 버프(나머지는 절차생성) — prototype MANUAL_GENERAL_DEFS 그대로
const MANUAL_GENERAL_DEFS = [
  { id: 'liu_bei', name: '유비', buffs: { unitAtk: 0.07, unitDef: 0.05, castleDef: 0.05, castleAtk: 0.05 } },
  { id: 'guan_yu', name: '관우', buffs: { unitAtk: 0.10, unitDef: 0.05, castleAtk: 0.085 } },
  { id: 'zhang_fei', name: '장비', buffs: { unitAtk: 0.10, unitDef: 0.06, castleAtk: 0.075 } },
  { id: 'zhao_yun', name: '조운', buffs: { unitAtk: 0.10, unitDef: 0.10, castleAtk: 0.03 } },
  { id: 'lu_bu', name: '여포', buffs: { unitAtk: 0.10, castleAtk: 0.10, unitDef: 0.05 } },
  { id: 'xiahou_dun', name: '하후돈', buffs: { unitAtk: 0.08, unitDef: 0.05, castleAtk: 0.05 } },
  { id: 'cao_cao', name: '조조', buffs: { unitAtk: 0.06, unitDef: 0.07, castleAtk: 0.06, castleDef: 0.05 } },
  { id: 'cao_xing', name: '조흥', buffs: { unitAtk: 0.04, castleAtk: 0.03 } },
  { id: 'taishi_ci', name: '태사자', buffs: { unitAtk: 0.10, unitDef: 0.07, castleAtk: 0.06 } },
  { id: 'zhuge_liang', name: '제갈량', buffs: { castleDef: 0.06, prodRate: 0.06, unitDef: 0.03 } },
  { id: 'huang_zhong', name: '황충', buffs: { unitAtk: 0.10, castleAtk: 0.07, unitDef: 0.03 } },
  { id: 'huang_gai', name: '황개', buffs: { unitAtk: 0.06, castleAtk: 0.05, unitDef: 0.04 } },
  { id: 'yan_liang', name: '안량', buffs: { unitAtk: 0.10, castleAtk: 0.06, unitDef: 0.04 } },
  { id: 'dong_zhuo', name: '동탁', buffs: { unitAtk: 0.07, unitDef: 0.05, castleDef: 0.05 } },
  { id: 'sima_yi', name: '사마의', buffs: { castleDef: 0.08, unitDef: 0.07, castleAtk: 0.04 } },
  { id: 'gan_ning', name: '감녕', buffs: { unitAtk: 0.09, castleAtk: 0.06, unitDef: 0.05 } },
  { id: 'yuan_shao', name: '원소', buffs: { unitAtk: 0.05, unitDef: 0.05, castleDef: 0.04 } },
  { id: 'sun_quan', name: '손권', buffs: { unitDef: 0.06, castleDef: 0.05, unitAtk: 0.04 } },
  { id: 'zhou_yu', name: '주유', buffs: { castleAtk: 0.07, unitAtk: 0.05, unitDef: 0.04 } },
  { id: 'ma_chao', name: '마초', buffs: { unitAtk: 0.10, unitDef: 0.06, castleAtk: 0.07 } },
  { id: 'sun_ce', name: '손책', buffs: { unitAtk: 0.09, castleAtk: 0.06, unitDef: 0.04 } },
  { id: 'lu_xun', name: '육손', buffs: { unitDef: 0.05, castleAtk: 0.05, prodRate: 0.04, unitAtk: 0.03 } },
  { id: 'pang_tong', name: '방통', buffs: { castleAtk: 0.06, prodRate: 0.04, castleDef: 0.03 } },
  { id: 'guo_jia', name: '곽가', buffs: { castleDef: 0.04, prodRate: 0.04, unitDef: 0.03 } },
  { id: 'dian_wei', name: '전위', buffs: { unitAtk: 0.10, unitDef: 0.08, castleDef: 0.05 } },
  { id: 'xu_chu', name: '허저', buffs: { unitDef: 0.10, unitAtk: 0.08, castleDef: 0.05 } },
  { id: 'zhang_liao', name: '장료', buffs: { unitAtk: 0.09, unitDef: 0.06, castleAtk: 0.055 } },
  { id: 'xu_huang', name: '서황', buffs: { unitAtk: 0.08, castleAtk: 0.07, unitDef: 0.04 } },
  { id: 'wen_chou', name: '문추', buffs: { unitAtk: 0.10, castleAtk: 0.05, unitDef: 0.04 } },
  { id: 'meng_huo', name: '맹획', buffs: { unitAtk: 0.08, unitDef: 0.05, castleAtk: 0.03 } },
  { id: 'hua_xiong', name: '화웅', buffs: { unitAtk: 0.09, castleAtk: 0.04, unitDef: 0.03 } },
  { id: 'gao_shun', name: '고순', buffs: { unitAtk: 0.07, unitDef: 0.07, castleAtk: 0.04 } },
  { id: 'chen_gong', name: '진궁', buffs: { castleDef: 0.04, prodRate: 0.03 } },
  { id: 'li_ru', name: '이유', buffs: { castleDef: 0.04, prodRate: 0.03 } },
  { id: 'li_jue', name: '이각', buffs: { unitAtk: 0.07, castleAtk: 0.04, unitDef: 0.04 } },
  { id: 'guo_si', name: '곽사', buffs: { unitAtk: 0.07, castleAtk: 0.04, unitDef: 0.03 } },
  { id: 'zhang_ji', name: '장제', buffs: { unitAtk: 0.05, castleAtk: 0.03, unitDef: 0.03 } },
  { id: 'zhang_xiu', name: '장수', buffs: { unitAtk: 0.07, unitDef: 0.05, castleAtk: 0.03 } },
  { id: 'jia_xu', name: '가후', buffs: { castleDef: 0.05, prodRate: 0.04, unitDef: 0.03 } },
  { id: 'xun_yu', name: '순욱', buffs: { castleDef: 0.05, prodRate: 0.05 } },
  { id: 'xun_you', name: '순유', buffs: { castleDef: 0.04, prodRate: 0.04 } },
  { id: 'cheng_yu', name: '정욱', buffs: { castleDef: 0.04, unitDef: 0.03 } },
  { id: 'cao_ren', name: '조인', buffs: { unitDef: 0.07, castleDef: 0.06, unitAtk: 0.04 } },
  { id: 'cao_hong', name: '조홍', buffs: { unitDef: 0.06, unitAtk: 0.05, castleDef: 0.03 } },
  { id: 'cao_pi', name: '조비', buffs: { unitAtk: 0.05, unitDef: 0.05, castleDef: 0.04 } },
  { id: 'cao_zhang', name: '조창', buffs: { unitAtk: 0.09, unitDef: 0.05, castleAtk: 0.045 } },
  { id: 'cao_zhi', name: '조식', buffs: { prodRate: 0.04, castleDef: 0.03 } },
  { id: 'cao_ang', name: '조앙', buffs: { unitAtk: 0.05, unitDef: 0.04 } },
  { id: 'cao_chun', name: '조순', buffs: { unitAtk: 0.05, unitDef: 0.05, castleAtk: 0.03 } },
  { id: 'cao_rui', name: '조예', buffs: { castleDef: 0.05, unitDef: 0.04 } },
  { id: 'wei_yan', name: '위연', buffs: { unitAtk: 0.09, unitDef: 0.05, castleAtk: 0.045 } },
  { id: 'zhou_tai', name: '주태', buffs: { unitDef: 0.08, unitAtk: 0.07, castleDef: 0.04 } },
  { id: 'zhang_he', name: '장합', buffs: { unitAtk: 0.08, unitDef: 0.06, castleAtk: 0.045 } },
  { id: 'jiang_wei', name: '강유', buffs: { unitAtk: 0.08, unitDef: 0.06, castleAtk: 0.04 } },
  { id: 'xiahou_yuan', name: '하후연', buffs: { unitAtk: 0.08, castleAtk: 0.06, unitDef: 0.04 } },
  { id: 'deng_ai', name: '등애', buffs: { unitAtk: 0.07, unitDef: 0.05, castleAtk: 0.05 } },
  { id: 'gongsun_zan', name: '공손찬', buffs: { unitAtk: 0.07, unitDef: 0.05, castleDef: 0.03 } },
  { id: 'ma_dai', name: '마대', buffs: { unitAtk: 0.07, unitDef: 0.05, castleAtk: 0.03 } },
  { id: 'ding_feng', name: '정봉', buffs: { unitAtk: 0.06, unitDef: 0.05, castleAtk: 0.03 } },
  { id: 'han_dang', name: '한당', buffs: { unitAtk: 0.06, castleAtk: 0.04, unitDef: 0.04 } },
  { id: 'ling_tong', name: '능통', buffs: { unitAtk: 0.07, unitDef: 0.05, castleAtk: 0.02 } },
  { id: 'cheng_pu', name: '정보', buffs: { unitAtk: 0.05, castleAtk: 0.05, unitDef: 0.04 } },
  { id: 'zhang_bao', name: '장포', buffs: { unitAtk: 0.07, unitDef: 0.05, castleAtk: 0.02 } },
  { id: 'guan_ping', name: '관평', buffs: { unitAtk: 0.06, unitDef: 0.05, castleAtk: 0.02 } },
  { id: 'jiang_qin', name: '장흠', buffs: { unitAtk: 0.05, unitDef: 0.05 } },
  { id: 'lu_su', name: '노숙', buffs: { castleDef: 0.05, prodRate: 0.05, unitDef: 0.03 } },
  { id: 'diao_chan', name: '초선', buffs: { unitDef: 0.03, prodRate: 0.03 } },
  { id: 'sun_jian', name: '손견', buffs: { unitAtk: 0.07, unitDef: 0.05, castleAtk: 0.05 } },
  { id: 'yue_jin', name: '악진', buffs: { unitAtk: 0.08, unitDef: 0.05, castleAtk: 0.04 } },
  { id: 'yu_jin', name: '우금', buffs: { unitDef: 0.06, unitAtk: 0.05, castleDef: 0.04 } },
  { id: 'li_dian', name: '이전', buffs: { unitAtk: 0.06, unitDef: 0.05, castleAtk: 0.03 } },
  { id: 'xiahou_ba', name: '하후패', buffs: { unitAtk: 0.08, unitDef: 0.05, castleAtk: 0.04 } },
  { id: 'guo_huai', name: '곽회', buffs: { unitDef: 0.06, castleDef: 0.05, unitAtk: 0.04 } },
  { id: 'fa_zheng', name: '법정', buffs: { castleAtk: 0.05, prodRate: 0.04, castleDef: 0.03 } },
  { id: 'zhang_song', name: '장송', buffs: { prodRate: 0.04, castleDef: 0.03 } },
  { id: 'ma_su', name: '마속', buffs: { castleDef: 0.04, prodRate: 0.03 } },
  { id: 'zhuge_jin', name: '제갈근', buffs: { castleDef: 0.04, prodRate: 0.04 } },
  { id: 'hua_tuo', name: '화타', buffs: { prodRate: 0.05, castleDef: 0.03 } },
  { id: 'zhang_jiao', name: '장각', buffs: { castleAtk: 0.05, prodRate: 0.05, unitAtk: 0.03 } },
  { id: 'yuan_shu', name: '원술', buffs: { castleDef: 0.05, unitDef: 0.03 } },
  { id: 'liu_biao', name: '유표', buffs: { castleDef: 0.05, prodRate: 0.04 } },
  { id: 'liu_zhang', name: '유장', buffs: { castleDef: 0.04, prodRate: 0.03 } },
  { id: 'cao_zhen', name: '조진', buffs: { unitDef: 0.06, castleDef: 0.05, unitAtk: 0.05, castleAtk: 0.03 } },
  { id: 'cao_xiu', name: '조휴', buffs: { unitAtk: 0.06, unitDef: 0.05, castleAtk: 0.04 } },
  { id: 'cao_shuang', name: '조상', buffs: { unitDef: 0.04, castleDef: 0.04 } },
  { id: 'man_chong', name: '만총', buffs: { castleDef: 0.06, unitDef: 0.05, castleAtk: 0.04 } },
  { id: 'zhong_yao', name: '종요', buffs: { prodRate: 0.05, castleDef: 0.04 } },
  { id: 'zhong_hui', name: '종회', buffs: { castleAtk: 0.05, unitAtk: 0.04, prodRate: 0.04 } },
  { id: 'wang_ping', name: '왕평', buffs: { unitAtk: 0.06, unitDef: 0.06, castleAtk: 0.03 } },
  { id: 'wen_ping', name: '문빙', buffs: { unitDef: 0.06, castleDef: 0.05, unitAtk: 0.04 } },
  { id: 'zhang_ba', name: '장패', buffs: { unitAtk: 0.07, unitDef: 0.05, castleAtk: 0.03 } },
  { id: 'yi_tong', name: '이통', buffs: { unitAtk: 0.06, unitDef: 0.05 } },
  { id: 'han_hao', name: '한호', buffs: { unitDef: 0.05, castleDef: 0.04 } },
  { id: 'lu_qian', name: '여건', buffs: { unitDef: 0.05, castleAtk: 0.03 } },
  { id: 'mao_jie', name: '모개', buffs: { prodRate: 0.05, castleDef: 0.03 } },
  { id: 'liu_ye', name: '유엽', buffs: { castleAtk: 0.05, prodRate: 0.04, castleDef: 0.03 } },
  { id: 'xu_sheng', name: '서성', buffs: { unitAtk: 0.06, unitDef: 0.06, castleAtk: 0.03 } },
  { id: 'zhang_zhao', name: '장소', buffs: { castleDef: 0.06, prodRate: 0.05 } },
  { id: 'zhang_hong', name: '장굉', buffs: { castleDef: 0.04, prodRate: 0.04 } },
  { id: 'zhu_ran', name: '주연', buffs: { unitDef: 0.06, unitAtk: 0.05, castleAtk: 0.03 } },
  { id: 'zhu_zhi', name: '주치', buffs: { unitAtk: 0.05, unitDef: 0.05 } },
  { id: 'zhu_huan', name: '주환', buffs: { unitAtk: 0.06, unitDef: 0.05, castleAtk: 0.02 } },
  { id: 'bu_zhi', name: '보즐', buffs: { castleDef: 0.04, prodRate: 0.04 } },
  { id: 'gan_ze', name: '감택', buffs: { prodRate: 0.05, castleDef: 0.03 } },
  { id: 'yu_fan', name: '우번', buffs: { castleDef: 0.04, prodRate: 0.04 } },
  { id: 'he_qi', name: '하제', buffs: { unitAtk: 0.06, unitDef: 0.05 } },
  { id: 'pan_zhang', name: '반장', buffs: { unitAtk: 0.07, unitDef: 0.05, castleAtk: 0.03 } },
  { id: 'ma_zhong', name: '마충', buffs: { unitAtk: 0.06, unitDef: 0.04 } },
  { id: 'quan_cong', name: '전종', buffs: { unitAtk: 0.06, unitDef: 0.05 } },
  { id: 'da_qiao', name: '대교', buffs: { unitDef: 0.03, prodRate: 0.03 } },
  { id: 'xiao_qiao', name: '소교', buffs: { unitDef: 0.03, prodRate: 0.03 } },
  { id: 'guan_xing', name: '관흥', buffs: { unitAtk: 0.08, unitDef: 0.05, castleAtk: 0.03 } },
  { id: 'guan_suo', name: '관색', buffs: { unitAtk: 0.07, unitDef: 0.05 } },
  { id: 'liu_shan', name: '유선', buffs: { castleDef: 0.04 } },
  { id: 'liu_feng', name: '유봉', buffs: { unitAtk: 0.06, unitDef: 0.05 } },
  { id: 'ma_liang', name: '마량', buffs: { castleDef: 0.04, prodRate: 0.05 } },
  { id: 'liao_hua', name: '요화', buffs: { unitAtk: 0.06, unitDef: 0.05 } },
  { id: 'zhou_cang', name: '주창', buffs: { unitAtk: 0.06, unitDef: 0.05 } },
  { id: 'yan_yan', name: '엄안', buffs: { unitAtk: 0.06, unitDef: 0.05, castleAtk: 0.03 } },
  { id: 'li_yan', name: '이엄', buffs: { unitAtk: 0.05, castleDef: 0.05, prodRate: 0.03 } },
  { id: 'fei_yi', name: '비의', buffs: { castleDef: 0.05, prodRate: 0.05 } },
  { id: 'jiang_wan', name: '장완', buffs: { castleDef: 0.05, prodRate: 0.05 } },
  { id: 'dong_yun', name: '동윤', buffs: { castleDef: 0.04, prodRate: 0.04 } },
  { id: 'huang_quan', name: '황권', buffs: { castleDef: 0.05, unitDef: 0.03 } },
  { id: 'zhang_yi', name: '장익', buffs: { unitAtk: 0.06, unitDef: 0.05 } },
  { id: 'zhuge_zhan', name: '제갈첨', buffs: { unitAtk: 0.05, castleDef: 0.05, prodRate: 0.03 } },
  { id: 'meng_da', name: '맹달', buffs: { unitAtk: 0.06, unitDef: 0.05 } },
  { id: 'jian_yong', name: '간옹', buffs: { castleDef: 0.04, prodRate: 0.03 } },
  { id: 'mi_zhu', name: '미축', buffs: { prodRate: 0.05, castleDef: 0.03 } },
  { id: 'sun_qian', name: '손건', buffs: { castleDef: 0.04, prodRate: 0.03 } },
  { id: 'li_hui', name: '이회', buffs: { unitDef: 0.05, castleDef: 0.03 } },
  { id: 'zhang_ren', name: '장임', buffs: { unitAtk: 0.07, unitDef: 0.05, castleAtk: 0.03 } },
  { id: 'yuan_tan', name: '원담', buffs: { unitAtk: 0.06, unitDef: 0.05 } },
  { id: 'yuan_shang', name: '원상', buffs: { unitAtk: 0.05, unitDef: 0.05 } },
  { id: 'tian_feng', name: '전풍', buffs: { castleDef: 0.05, prodRate: 0.05, unitDef: 0.03 } },
  { id: 'ju_shou', name: '저수', buffs: { castleDef: 0.05, prodRate: 0.05 } },
  { id: 'shen_pei', name: '심배', buffs: { castleDef: 0.05, prodRate: 0.03 } },
  { id: 'gao_lan', name: '고람', buffs: { unitAtk: 0.07, unitDef: 0.05 } },
  { id: 'guo_tu', name: '곽도', buffs: { castleDef: 0.03, prodRate: 0.03 } },
  { id: 'feng_ji', name: '봉기', buffs: { castleDef: 0.03, prodRate: 0.03 } },
  { id: 'xin_pi', name: '신비', buffs: { castleDef: 0.04, prodRate: 0.04 } },
  { id: 'ma_teng', name: '마등', buffs: { unitAtk: 0.07, unitDef: 0.05, castleAtk: 0.04 } },
  { id: 'han_sui', name: '한수', buffs: { unitAtk: 0.05, unitDef: 0.05 } },
  { id: 'zhang_lu', name: '장로', buffs: { castleDef: 0.06, prodRate: 0.04 } },
  { id: 'kong_rong', name: '공융', buffs: { castleDef: 0.04, prodRate: 0.04 } },
  { id: 'tao_qian', name: '도겸', buffs: { castleDef: 0.05, prodRate: 0.03 } },
  { id: 'liu_yu', name: '유우', buffs: { castleDef: 0.04, prodRate: 0.04 } },
  { id: 'wang_yun', name: '왕윤', buffs: { castleDef: 0.05, prodRate: 0.04 } },
  { id: 'ji_ling', name: '기령', buffs: { unitAtk: 0.06, unitDef: 0.04 } },
  { id: 'he_jin', name: '하진', buffs: { castleDef: 0.04 } },
  { id: 'zuo_ci', name: '좌자', buffs: { prodRate: 0.05, castleDef: 0.04 } },
  { id: 'yu_ji', name: '우길', buffs: { prodRate: 0.05, castleDef: 0.03 } },
  { id: 'gongsun_kang', name: '공손강', buffs: { unitAtk: 0.05, unitDef: 0.05 } },
];

function hashGeneralId(id) {
  let h = 2166136261;
  for (const ch of String(id || '')) { h ^= ch.charCodeAt(0); h = Math.imul(h, 16777619); }
  return h >>> 0;
}
function generatedGeneralBuffs(id, name, index) {
  const h = hashGeneralId(`${id}:${name}:${index}`);
  const first = h % GENERAL_BUFF_KEYS.length;
  let second = Math.floor(h / 7) % GENERAL_BUFF_KEYS.length;
  if (second === first) second = (second + 2) % GENERAL_BUFF_KEYS.length;
  let third = Math.floor(h / 37) % GENERAL_BUFF_KEYS.length;
  if (third === first || third === second) third = (third + 1) % GENERAL_BUFF_KEYS.length;
  const buffs = {};
  buffs[GENERAL_BUFF_KEYS[first]] = 0.045 + (h % 4) * 0.005;
  buffs[GENERAL_BUFF_KEYS[second]] = 0.030 + (Math.floor(h / 11) % 4) * 0.005;
  if (h % 3 === 0) buffs[GENERAL_BUFF_KEYS[third]] = 0.020 + (Math.floor(h / 17) % 3) * 0.005;
  Object.keys(buffs).forEach((k) => { buffs[k] = Math.round(buffs[k] * 1000) / 1000; });
  return buffs;
}

// 전체 로스터 구성: GENERALS_200(id/name 쌍) + 명장 수동버프 오버레이, 나머지는 절차생성.
export function buildRoster(pairs) {
  const manualById = new Map(MANUAL_GENERAL_DEFS.map((g) => [g.id, g]));
  const rawPairs = Array.isArray(pairs) && pairs.length ? pairs : MANUAL_GENERAL_DEFS.map((g) => [g.id, g.name]);
  const seen = new Set();
  const list = [];
  rawPairs.forEach((pair, index) => {
    const id = pair && String(pair[0] || '').trim();
    const name = pair && String(pair[1] || '').trim();
    if (!id || !name || seen.has(id)) return;
    seen.add(id);
    const base = manualById.get(id) || { id, name, buffs: generatedGeneralBuffs(id, name, index) };
    list.push({ id, name: base.name || name, buffs: base.buffs });
  });
  return list;
}

function clampStars(v) { return Math.max(1, Math.min(5, (v | 0) || 1)); }
function clampLv(v) { return Math.max(1, Math.min(6, (v | 0) || 1)); }

// 장수 1개 버프 해석 — prototype generalBuff 일치: base × ENHANCE_MULT[lv] × STAR_MULT[stars] (+STAR_FLAT)
function generalBuff(def, lv, stars, key) {
  if (!def || !def.buffs) return 0;
  const st = clampStars(stars), base = def.buffs[key] || 0;
  let v = base * ENHANCE_MULT[clampLv(lv)] * (STAR_MULT[st] || 1);
  if (key === 'unitAtk') v += STAR_FLAT[st];
  else if (key === 'unitDef') v += STAR_FLAT[st] * 0.6;
  return v;
}
// 크리티컬(등급+레벨) — prototype commanderCritStats 일치
function commanderCritStats(stars, lv) {
  const base = { 1: { chance: 0.05, mult: 1.20 }, 2: { chance: 0.08, mult: 1.40 }, 3: { chance: 0.12, mult: 1.55 },
    4: { chance: 0.16, mult: 1.70 }, 5: { chance: 0.20, mult: 1.85 } }[clampStars(stars)] || { chance: 0.05, mult: 1.20 };
  const L = clampLv(lv);
  return {
    chance: Math.min(0.40, base.chance + Math.min(0.12, (L - 1) * 0.006)),
    mult: Math.min(2.0, base.mult + Math.min(0.15, (L - 1) * 0.008)),
  };
}
function upgVal(upgrades, key) { return 1 + ((upgrades && upgrades[key]) || 0) * UPG_PER[key]; }

// 활성 편성 uid 목록 — 활성 포메이션 우선, 없으면 lastDeployGenerals, 없으면 天.
export function activeDeployUids(save) {
  save = save || {};
  const k = FORMATION_KEYS.includes(save.activeFormation) ? save.activeFormation : null;
  const f = save.formations || {};
  let src = [];
  if (k && Array.isArray(f[k]) && f[k].length) src = f[k];
  else if (Array.isArray(save.lastDeployGenerals) && save.lastDeployGenerals.length) src = save.lastDeployGenerals;
  else if (Array.isArray(f['天']) && f['天'].length) src = f['天'];
  return src.slice(0, MAX_DEPLOY_GENERALS);
}

// SAVE + roster → 엔진 로드아웃. 편성이 비면 업그레이드만 반영된 로드아웃(장수 0).
export function computeLoadout(save, roster) {
  save = save || {};
  const byId = new Map((roster || []).map((g) => [g.id, g]));
  const upgrades = save.upgrades || {};
  const upg = {
    unitAtk: upgVal(upgrades, 'unitAtk'), unitDef: upgVal(upgrades, 'unitDef'),
    castleAtk: upgVal(upgrades, 'castleAtk'), castleDef: upgVal(upgrades, 'castleDef'),
    prodRate: upgVal(upgrades, 'prodRate'),
  };
  const instById = new Map((save.generals || []).map((i) => [i.uid, i]));
  const generals = [];
  for (const uid of activeDeployUids(save)) {
    const inst = instById.get(uid); if (!inst) continue;
    const def = byId.get(inst.id); if (!def) continue;
    const lv = inst.lv || 1, stars = inst.stars || 1;
    const crit = commanderCritStats(stars, lv);
    generals.push({
      atk: generalBuff(def, lv, stars, 'unitAtk'), def: generalBuff(def, lv, stars, 'unitDef'),
      cAtk: generalBuff(def, lv, stars, 'castleAtk'), cDef: generalBuff(def, lv, stars, 'castleDef'),
      prod: generalBuff(def, lv, stars, 'prodRate'),
      critChance: crit.chance, critMult: crit.mult,
      _id: def.id, _name: def.name, _lv: lv, _stars: stars,   // UI 표시용(엔진은 무시)
    });
  }
  return { upg, generals };
}

// 전투력(매칭 브래킷용) — 로드아웃을 단일 스칼라로. 기준 1000, 장수·업그레이드가 많을수록 상승.
export function computePower(loadout) {
  if (!loadout) return 1000;
  const u = loadout.upg || {};
  let p = 1000;
  p += (((u.unitAtk || 1) - 1) + ((u.unitDef || 1) - 1) + ((u.castleAtk || 1) - 1) + ((u.castleDef || 1) - 1) + ((u.prodRate || 1) - 1)) * 500;
  for (const g of loadout.generals || []) {
    p += ((g.atk || 0) + (g.def || 0) + (g.cAtk || 0) + (g.cDef || 0) + (g.prod || 0)) * 350;
    p += (g.critChance || 0) * (g.critMult || 1) * 200;
    p += 50;   // 편성 인원 자체 가치
  }
  return Math.round(p);
}
