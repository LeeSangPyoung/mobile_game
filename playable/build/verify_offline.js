// 오프라인(네트워크 전면차단) 검증: playable_ad.html 이 self-contained 인지 확인
// 사용: node verify_offline.js   → 차단된 네트워크 0 / JS 에러 0 / CTA 도달 여야 정상
const puppeteer = require('puppeteer-core');
const path = require('path');
const CHROME = process.env.CHROME_PATH || 'C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe';
const MG = path.resolve(__dirname, '..', '..');
const FILE = 'file:///' + path.join(MG, 'playable', 'playable_ad.html').replace(/\\/g, '/') + '?ad=1';
(async () => {
  const b = await puppeteer.launch({ executablePath: CHROME, headless: 'new', args: ['--no-sandbox', '--disable-gpu', '--use-gl=swiftshader', '--mute-audio', '--allow-file-access-from-files'] });
  const p = await b.newPage();
  await p.setViewport({ width: 430, height: 932, deviceScaleFactor: 2, isMobile: true, hasTouch: true });
  const errs = [], blocked = new Set();
  p.on('pageerror', e => errs.push(e.message));
  await p.setRequestInterception(true);
  p.on('request', req => {
    const u = req.url();
    if (req.resourceType() === 'document' || u.startsWith('data:') || u.startsWith('blob:')) req.continue();
    else { blocked.add(u.replace(/\?.*$/, '')); req.abort(); }
  });
  await p.goto(FILE, { waitUntil: 'domcontentloaded', timeout: 30000 });
  await new Promise(r => setTimeout(r, 5000));
  // 자동 플레이(유저 시뮬) → CTA까지
  await p.evaluate(() => { window._adAuto = setInterval(function () { try { var d = window._adDbg; if (!d || !d.target) return; var s = _mySide(); var t = castles.find(function (c) { return c.name === d.target; }); if (!t || t.owner === s) return; var m = castles.filter(function (c) { return c.owner === s; }); var src = null, bt = -1; m.forEach(function (c) { var tt = c.troops.spear + c.troops.cavalry + c.troops.archer; if (tt > bt) { bt = tt; src = c; } }); if (src) { ['spear', 'cavalry', 'archer'].forEach(function (u) { if (src.troops[u] > 3) sendArmy(src, t, u, null, false); }); } } catch (e) { } }, 500); });
  let cta = false;
  for (let i = 0; i < 24; i++) { await new Promise(r => setTimeout(r, 2500)); cta = await p.evaluate(() => !!document.getElementById('adCTA')); if (cta) break; }
  await p.screenshot({ path: path.join(__dirname, 'verify_cta.png') });
  console.log('CTA 도달:', cta, '| JS 에러:', errs.length, '| 차단 네트워크:', [...blocked].length);
  errs.slice(0, 5).forEach(e => console.log('  err:', e));
  [...blocked].slice(0, 10).forEach(u => console.log('  net:', u));
  await b.close();
})();
