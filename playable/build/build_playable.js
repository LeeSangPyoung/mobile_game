// prototype.html + inject.txt + 인라인 자산/폰트 → 자체완결 단일 HTML 플레이어블
// 출력: ../playable_ad.html   (사용: node build_playable.js)
const fs = require('fs');
const path = require('path');
const MG = path.resolve(__dirname, '..', '..');          // mobile_game
const TRANSPARENT = 'data:image/gif;base64,R0lGODlhAQABAIAAAAAAAP///yH5BAEAAAAALAAAAAABAAEAAAIBRAA7';
const b64 = f => fs.readFileSync(f).toString('base64');

const font = {
  noto: 'data:font/woff2;base64,' + b64(path.join(__dirname, 'NotoSerifKR-ad.woff2')),
  zcool: 'data:font/woff2;base64,' + b64(path.join(MG, 'assets/fonts/ZCOOLXiaoWei-subset.woff2')),
  mashan: 'data:font/woff2;base64,' + b64(path.join(MG, 'assets/fonts/MaShanZheng-subset.woff2')),
};
const INLINE = JSON.parse(fs.readFileSync(path.join(__dirname, 'assets_inline.json'), 'utf8'));
// 승리배경은 CSS 변수 --advic 로 1벌만 (중복 인라인 방지)
const VICTORY = INLINE['result/result_victory_bg.png'];
delete INLINE['result/result_victory_bg.png'];

let html = fs.readFileSync(path.join(MG, 'prototype.html'), 'utf8');

// 1) @font-face → data URI
html = html.replace(/url\('\.\/assets\/fonts\/NotoSerifKR-subset\.woff2[^']*'\)/g, "url('" + font.noto + "')");
html = html.replace(/url\('\.\/assets\/fonts\/ZCOOLXiaoWei-subset\.woff2[^']*'\)/g, "url('" + font.zcool + "')");
html = html.replace(/url\('\.\/assets\/fonts\/MaShanZheng-subset\.woff2[^']*'\)/g, "url('" + font.mashan + "')");

// 2) roster 외부 스크립트 인라인
const roster = fs.readFileSync(path.join(MG, 'assets/generals/roster_200.js'), 'utf8');
html = html.replace('<script src="./assets/generals/roster_200.js"></script>', '<script>\n' + roster + '\n</' + 'script>');

// 3) shim + __INLINE 맵 + --advic 을 <head> 최상단 주입
const shim = '<script>(function(){'
  + 'var T="' + TRANSPARENT + '";var M=window.__INLINE||{};'
  + 'function keyOf(u){ if(!u) return null; u=String(u).split("?")[0]; var i=u.indexOf("/assets/"); return i>=0?u.slice(i+8):null; }'
  + 'function rw(u){ if(u==null) return u; var s=String(u); if(s.slice(0,5)==="data:"||s.slice(0,5)==="blob:") return u; var k=keyOf(s); if(k&&M[k]) return M[k]; if(s.indexOf("/assets/")>=0||/^https?:/.test(s)||s.charAt(0)==="."||s.charAt(0)==="/") return T; return u; }'
  + 'try{ var d=Object.getOwnPropertyDescriptor(HTMLImageElement.prototype,"src"); Object.defineProperty(HTMLImageElement.prototype,"src",{get:function(){return d.get.call(this);},set:function(v){d.set.call(this,rw(v));},configurable:true}); }catch(e){}'
  + 'try{ var sa=Element.prototype.setAttribute; Element.prototype.setAttribute=function(n,v){ if(this&&this.tagName==="IMG"&&n==="src"){ v=rw(v); } return sa.call(this,n,v); }; }catch(e){}'
  + 'try{ window.WebSocket=function(){ this.readyState=3; this.close=function(){}; this.send=function(){}; this.addEventListener=function(){}; this.removeEventListener=function(){}; }; window.WebSocket.CONNECTING=0;window.WebSocket.OPEN=1;window.WebSocket.CLOSING=2;window.WebSocket.CLOSED=3; }catch(e){}'
  + 'try{ window.fetch=function(){ return Promise.reject(new Error("offline")); }; }catch(e){}'
  + 'try{ window.XMLHttpRequest=function(){ this.open=function(){}; this.send=function(){}; this.setRequestHeader=function(){}; this.addEventListener=function(){}; this.abort=function(){}; }; }catch(e){}'
  + 'try{ var AN=function(){ return {play:function(){return Promise.resolve();},pause:function(){},load:function(){},addEventListener:function(){},removeEventListener:function(){},canPlayType:function(){return "";},cloneNode:function(){return AN();},set src(v){},get src(){return "";},currentTime:0,volume:1,loop:false,muted:true}; }; window.Audio=AN; }catch(e){}'
  + '})();</' + 'script>';
const inlineMap = '<script>window.__INLINE=' + JSON.stringify(INLINE) + ';</' + 'script>';
const vicVar = '<style>:root{--advic:url("' + VICTORY + '")}</' + 'style>';
html = html.replace(/<head>/i, '<head>\n' + vicVar + '\n' + inlineMap + '\n' + shim);

// 4) inject(ad) → </body> 앞
const inject = fs.readFileSync(path.join(__dirname, 'inject.txt'), 'utf8');
html = html.replace('</body>', inject + '\n</body>');

// 5) 최종 HTML 잔여 이미지 자산 URL 일괄 치환 (정적 img·CSS·JS) — 맵 있으면 data URI, 없으면 투명
html = html.replace(/(?:\.?\/)?assets\/([A-Za-z0-9_\/.\-]+\.(?:png|jpe?g|webp|svg|gif))(?:\?[^"')\s]*)?/g, (m, key) => INLINE[key] || TRANSPARENT);

const out = path.join(MG, 'playable', 'playable_ad.html');
fs.writeFileSync(out, html);
console.log('생성: playable/playable_ad.html  ' + (fs.statSync(out).size / 1048576).toFixed(2) + 'MB');
