const puppeteer=require('puppeteer-core');
(async()=>{
const b=await puppeteer.launch({executablePath:'C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe',headless:'new',args:['--no-sandbox','--disable-gpu','--use-gl=swiftshader','--mute-audio']});
const p=await b.newPage();
await p.setViewport({width:412,height:820,deviceScaleFactor:2});
await p.goto('file:///D:/workspace_game2/mobile_game/prototype.html?cheat=1',{waitUntil:'domcontentloaded',timeout:30000});
await new Promise(r=>setTimeout(r,3500));
await p.evaluate(()=>{
  SAVE.generals=[];
  ['liu_bei','ma_teng','cao_cao','guan_yu','lu_bu','zhang_fei','zhao_yun'].forEach((id,i)=>addOwnedGeneral(id,i%3+1,(i%5)+1));
  showDex();
});
await new Promise(r=>setTimeout(r,800));
await p.screenshot({path:'D:/workspace_game2/mobile_game/playable/build/dex_shot.png'});
console.log('saved');
await b.close();})();
