// 광고 자산을 webp로 재압축 → assets_inline.json (data URI 맵) 생성
// 사용: node compress.js   (puppeteer-core + 로컬 Chrome 필요)
const puppeteer = require('puppeteer-core');
const fs = require('fs');
const path = require('path');

const CHROME = process.env.CHROME_PATH || 'C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe';
const MG = path.resolve(__dirname, '..', '..');           // mobile_game
const AROOT = path.join(MG, 'assets');                    // assets 루트
const toFileUrl = p => 'file:///' + p.replace(/\\/g, '/');

// {상대경로, 목표폭, 품질}
const LIST = [
  ['castles/castle_neutral.png', 480, 0.82],
  ['castles/castle_ally.png', 480, 0.82],
  ['castles/castle_enemy.png', 480, 0.82],
  ['result/result_victory_bg.png', 760, 0.80],
  ['battle/bg_battle_02_snow.jpg', 720, 0.78],
  ['generals/halfbody_v6/han_hao.webp', 220, 0.80],
];
// 배지가 그리는 war_v6 얼굴 아이콘 — 주요 장수(faces/ 보유 id) 전부 인라인
for (const f of fs.readdirSync(path.join(AROOT, 'generals/faces')).filter(n => /\.png$/i.test(n))) {
  const id = f.replace(/\.png$/i, '');
  const v6 = 'generals/face_icons/war_v6_halfbody_style_transparent/' + id + '_war_face_icon_v6_cute50.png';
  if (fs.existsSync(path.join(AROOT, v6))) LIST.push([v6, 180, 0.82]);
}

(async () => {
  // 로컬 이미지 로드를 위한 빈 페이지(같은 오리진)
  const blank = path.join(AROOT, '_blank.html');
  fs.writeFileSync(blank, '<!doctype html><meta charset=utf-8><title>blank</title>');
  const b = await puppeteer.launch({ executablePath: CHROME, headless: 'new', args: ['--no-sandbox', '--disable-gpu', '--use-gl=swiftshader', '--allow-file-access-from-files'] });
  const p = await b.newPage();
  await p.goto(toFileUrl(blank), { waitUntil: 'domcontentloaded' });
  const out = {}; let total = 0;
  for (const [rel, w, q] of LIST) {
    const r = await p.evaluate((rel, w, q) => new Promise(res => {
      const im = new Image();
      im.onload = () => { try {
        const scale = Math.min(1, w / im.naturalWidth); const cw = Math.round(im.naturalWidth * scale), ch = Math.round(im.naturalHeight * scale);
        const c = document.createElement('canvas'); c.width = cw; c.height = ch;
        c.getContext('2d').drawImage(im, 0, 0, cw, ch);
        res({ ok: true, du: c.toDataURL('image/webp', q) });
      } catch (e) { res({ ok: false, err: String(e) }); } };
      im.onerror = () => res({ ok: false, err: 'load fail' });
      im.src = rel;
    }), rel, w, q);
    if (r.ok) { const bytes = Math.round(r.du.length * 3 / 4); total += bytes; out[rel] = r.du; console.log((bytes / 1024).toFixed(1).padStart(7) + 'KB  ' + rel); }
    else console.log('  FAIL ' + rel + ': ' + r.err);
  }
  fs.writeFileSync(path.join(__dirname, 'assets_inline.json'), JSON.stringify(out));
  fs.unlinkSync(blank);
  console.log('\n압축 자산 합계: ' + (total / 1048576).toFixed(2) + 'MB → assets_inline.json');
  await b.close();
})();
