// 장수가 **모든 상태에서 눈에 보이는가**를 재는 검사.
//
// 왜 필요한가:
//   "마초가 공격받을 때 잠시 사라진다" 는 제보가 있었다. 에셋도 멀쩡하고
//   빠지는 프레임도 없었는데, 피격 깜빡임이 알파를 0.55 로 낮추는 방식이라
//   은백색 갑옷인 마초가 밝은 배경에 그대로 묻혔다. 어두운 장수만 보고
//   만든 연출이 밝은 장수에서 무너진 것이다.
//
// 어떻게 재나:
//   같은 프레임을 두 번 그린다 — 캐릭터를 그린 것과 안 그린 것.
//   **그림이 실제로 덮은 픽셀에서만** 두 장의 색 차이를 평균낸다.
//   자세가 크든 작든 휘둘리지 않고 '거기 있는 게 보이는가' 만 남는다.
//
//   node tools/check_visibility.mjs             # 가장 밝은 장수(공손찬)
//   node tools/check_visibility.mjs lu_bu       # 특정 장수
//
//   기준: 대기 대비 55% 미만이면 안 보이는 것으로 본다.
//   화면섬광(격돌 순간의 흰 번쩍임)은 66~69% 로 나오는데, 이건 양쪽 모두에게
//   똑같이 걸리는 의도된 연출이라 문제가 아니다.

import { spawn } from 'node:child_process';
import { mkdtemp, readFile } from 'node:fs/promises';
import { tmpdir } from 'node:os';
import { join } from 'node:path';
const CHROME='C:/Program Files/Google/Chrome/Application/chrome.exe';
const wait=ms=>new Promise(r=>setTimeout(r,ms));
const profile=await mkdtemp(join(tmpdir(),'vis-'));
const child=spawn(CHROME,['--headless=new','--disable-gpu','--disable-background-timer-throttling','--remote-debugging-port=0',`--user-data-dir=${profile}`,'--window-size=430,932','http://127.0.0.1:5173/duel_v2.html'],{stdio:'ignore'});
let p; for(let i=0;i<80;i++){try{p=(await readFile(join(profile,'DevToolsActivePort'),'utf8')).split(/\r?\n/)[0];break;}catch{await wait(150);}}
await wait(700);
const pages=await (await fetch(`http://127.0.0.1:${p}/json`)).json();
const sock=new WebSocket(pages.find(x=>x.type==='page').webSocketDebuggerUrl);
let id=0;const pend=new Map();
sock.onmessage=e=>{const m=JSON.parse(e.data);if(m.id&&pend.has(m.id)){pend.get(m.id)(m.result);pend.delete(m.id);}};
await new Promise(r=>sock.onopen=r);
const send=(mm,pp={})=>new Promise(r=>{const i=++id;pend.set(i,r);sock.send(JSON.stringify({id:i,method:mm,params:pp}));});
const ev=async e=>{const r=await send('Runtime.evaluate',{expression:e,returnByValue:true,awaitPromise:true});
  if(r.exceptionDetails) throw new Error(JSON.stringify(r.exceptionDetails).slice(0,400)); return r.result?.value;};
await send('Runtime.enable'); await wait(5500);
const who = process.argv[2] || 'gongsun_zan';
await ev(`pickP.value='${who}'; pickB.value='hua_xiong'; useTouch(); ovGo.click(); 1`); await wait(2900);
await ev(`intro.dispatchEvent(new PointerEvent('pointerdown')); 1`); await wait(3200);
await ev(`window.__loopOff=true;(function(){const raf=requestAnimationFrame;window.requestAnimationFrame=cb=>window.__loopOff?0:raf(cb);})();1`);
await wait(300);
const CODE = ['(()=>{',
 'window.updateAI=function(){};',
 'var c=document.querySelector("canvas"), g=c.getContext("2d");',
 // 캐릭터 영역만 잘라 '그렸을 때'와 '안 그렸을 때'의 차이를 잰다
 'var grab=function(){',
 '  var sx=Math.round(c.width*0.10), sw=Math.round(c.width*0.42);',
 '  var sy=Math.round(c.height*0.28), sh=Math.round(c.height*0.30);',
 '  return g.getImageData(sx,sy,sw,sh).data; };',
 // 자세 크기에 휘둘리지 않게, **그림이 실제로 덮은 픽셀에서만** 대비를 잰다.
 'var diff=function(a,b){ var s=0,n=0; for(var i=0;i<a.length;i+=4){',
 '  var d=(Math.abs(a[i]-b[i])+Math.abs(a[i+1]-b[i+1])+Math.abs(a[i+2]-b[i+2]))/3;',
 '  if(d>3){ s+=d; n++; } } return n? [s/n, n] : [0,0]; };',
 'var orig=drawStatePose;',
 'var probe=function(label, setup){',
 '  setup();',
 '  render(); var on=grab();',
 '  window.drawStatePose=function(){}; render(); var off=grab();',
 '  window.drawStatePose=orig;',
 '  var d=diff(on,off); return [label, d[0], d[1]]; };',
 'var out=[];',
 'var base=function(){ resetMatch(); phase="fight"; P.x=B.x-420; P.z=B.z; };',
 'out.push(probe("대기", function(){ base(); }));',
 'out.push(probe("걷기", function(){ base(); P.state="walk"; P.gait=40; }));',
 'out.push(probe("가드", function(){ base(); P.guardHeld=true; P.guardT=20; }));',
 'out.push(probe("저스트가드", function(){ base(); P.guardHeld=true; P.guardT=2; }));',
 'out.push(probe("예비동작", function(){ base(); startMove(P,"heavy"); for(var i=0;i<10;i++) update(); }));',
 'out.push(probe("타격중", function(){ base(); startMove(P,"heavy"); for(var i=0;i<24;i++) update(); }));',
 'out.push(probe("피격(약)", function(){ base(); P.state="hurt"; P.st=2; P.hitFlash=14; P.hurtHeavy=false; }));',
 'out.push(probe("피격(강)", function(){ base(); P.state="hurt"; P.st=2; P.hitFlash=13; P.hurtHeavy=true; }));',
 'out.push(probe("피격 깜빡 켜짐", function(){ base(); P.state="hurt"; P.st=2; P.hitFlash=14; }));',
 'out.push(probe("피격 깜빡 꺼짐", function(){ base(); P.state="hurt"; P.st=2; P.hitFlash=12; }));',
 'out.push(probe("경직", function(){ base(); P.state="stunned"; P.st=5; P.stunTimer=60; }));',
 'out.push(probe("무적중", function(){ base(); P.inv=8; }));',
 'out.push(probe("쓰러짐", function(){ base(); P.state="ko"; P.st=5; }));',
 'out.push(probe("누움", function(){ base(); P.state="ko"; P.st=40; }));',
 'out.push(probe("화면섬광", function(){ base(); hitStop=22; }));',
 'return out;})()'].join(String.fromCharCode(10));
const rows = await ev(CODE);
const base = rows[0][1];
console.log(`${'상태'.padEnd(16)}${'대비'.padStart(7)}${'덮은픽셀'.padStart(9)}  대기 대비`);
for (const [n,v,px] of rows) {
  const pct = v/base*100;
  const tag = pct < 55 ? '  ← 안 보인다' : pct < 75 ? '  ← 흐리다' : '';
  console.log(`${n.padEnd(16)}${v.toFixed(1).padStart(7)}${String(px).padStart(9)}  ${pct.toFixed(0).padStart(4)}%${tag}`);
}
sock.close(); child.kill();
