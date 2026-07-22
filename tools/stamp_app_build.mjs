// tools/stamp_app_build.mjs — 앱 번들 index.html에 versionCode를 심는다.
//   window.__APP_BUILD__ = <versionCode> 가 있어야 강제 업데이트 게이트가 앱에서 동작한다.
//   웹(app.wooriban.org)에는 이 스탬프가 없으므로 게이트가 돌지 않는다(웹은 항상 최신).
//   build.gradle의 versionCode를 읽어 자동으로 맞추므로 APK와 항상 일치한다.
//
//   실행(웹 최신화 cp 직후): node tools/stamp_app_build.mjs
import fs from 'fs';
import path from 'path';
import { fileURLToPath } from 'url';

const root = path.dirname(path.dirname(fileURLToPath(import.meta.url)));
const gradle = fs.readFileSync(path.join(root, 'app/android/app/build.gradle'), 'utf8');
const m = gradle.match(/versionCode\s+(\d+)/);
if (!m) { console.error('versionCode를 build.gradle에서 찾지 못함'); process.exit(1); }
const versionCode = parseInt(m[1], 10);

const idxPath = path.join(root, 'app/www/index.html');
let html = fs.readFileSync(idxPath, 'utf8');

// 기존 스탬프 제거(재빌드 시 중복 방지) 후 <head> 바로 뒤에 삽입.
html = html.replace(/<script>window\.__APP_BUILD__=\d+;<\/script>\n?/g, '');
const stamp = `<script>window.__APP_BUILD__=${versionCode};</script>\n`;
if (html.indexOf('<head>') >= 0) {
  html = html.replace('<head>', '<head>\n' + stamp);
} else {
  html = stamp + html;   // <head>가 없으면 맨 앞
}
fs.writeFileSync(idxPath, html);
console.log('앱 빌드 스탬프 삽입 완료: window.__APP_BUILD__=' + versionCode + ' → app/www/index.html');
