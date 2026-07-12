// 관리자 데모: 근접전투력 2쌍=진행중 대전 2건, 격차 큰 2명=대기 큐. 접속 유지.
const PORT=8080; const sleep=ms=>new Promise(r=>setTimeout(r,ms));
function cli(nick){ return new Promise(res=>{ const ws=new WebSocket('ws://127.0.0.1:'+PORT); const a={ws,msgs:[]}; ws.onmessage=e=>a.msgs.push(JSON.parse(e.data)); ws.onopen=()=>{ws.send(JSON.stringify({t:'hello',nick}));res(a);}; }); }
const defs=[
  ['관우_대협',2600],['장비_맹장',2560],   // 근접 → 매칭
  ['조운_상산',1900],['마초_서량',1850],   // 근접 → 매칭
  ['여포_봉선',4800],['조조_맹덕',3300],   // 격차 큼 → 대기
];
const cs=[];
for(const [n,p] of defs){ const c=await cli(n); c.pw=p; cs.push(c); await sleep(140); }
await sleep(300);
for(const c of cs){ c.ws.send(JSON.stringify({t:'queue',power:c.pw})); await sleep(120); }
await sleep(400);
console.log('[seed] 진입 완료(진행중 대전 2 + 대기 2 예상). 접속 유지중.');
setInterval(()=>{ for(const c of cs){ try{c.ws.send(JSON.stringify({t:'stats'}));}catch(_){} } }, 20000);
await new Promise(()=>{});
