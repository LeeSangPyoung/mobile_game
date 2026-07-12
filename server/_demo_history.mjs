const PORT=8080; const sleep=ms=>new Promise(r=>setTimeout(r,ms));
function cli(nick){ return new Promise(res=>{ const ws=new WebSocket('ws://127.0.0.1:'+PORT); const a={ws,msgs:[]}; ws.onmessage=e=>a.msgs.push(JSON.parse(e.data)); ws.onopen=()=>{ws.send(JSON.stringify({t:'hello',nick}));res(a);}; }); }
async function match(n1,p1,n2,p2,winnerSide){
  const A=await cli(n1), B=await cli(n2); await sleep(200);
  A.ws.send(JSON.stringify({t:'queue',power:p1})); await sleep(80);
  B.ws.send(JSON.stringify({t:'queue',power:p2})); await sleep(350);
  const hostIsA=A.msgs.some(m=>m.t==='matched'&&m.role==='host');
  const host=hostIsA?A:B;
  if(!A.msgs.some(m=>m.t==='matched')){ console.log('  ⚠ '+n1+' vs '+n2+' 미매칭(gap 큼)'); }
  host.ws.send(JSON.stringify({t:'result',winner:winnerSide})); await sleep(250);
  A.ws.close(); B.ws.close(); await sleep(150);
}
await match('황충_노장',2650,'서황_장군',2560,1);
await match('사마의_책사',3350,'맹획_남만',3280,1);
await match('전위_친위',1950,'문추_하북',1880,2);
await match('태사자_강동',2200,'화웅_선봉',2130,1);
await match('황충_노장',2650,'태사자_강동',2200,1);   // 황충 2승
console.log('[history] 완료 대전 기록');
