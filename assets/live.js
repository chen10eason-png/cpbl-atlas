/* CPBL ATLAS live centre: displays timestamped official-source snapshots.
   GitHub Pages cannot provide second-by-second updates; the official broadcast
   remains available via direct links for truly up-to-date commentary. */
const byId=id=>document.getElementById(id);
const esc=s=>String(s??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
const dtParts=d=>Object.fromEntries(new Intl.DateTimeFormat('en-GB',{timeZone:'Asia/Taipei',year:'numeric',month:'2-digit',day:'2-digit'}).formatToParts(d).map(x=>[x.type,x.value]));
export const taipeiDay=(d=new Date())=>{const x=dtParts(d);return `${x.year}-${x.month}-${x.day}`;};
export const formatTime=date=>{const d=new Date(date);return Number.isFinite(d.getTime())?new Intl.DateTimeFormat('zh-TW',{timeZone:'Asia/Taipei',month:'2-digit',day:'2-digit',hour:'2-digit',minute:'2-digit',hour12:false}).format(d):'未知';};
export const ageMinutes=(date,now=Date.now())=>{const t=Date.parse(date);return Number.isFinite(t)?Math.max(0,Math.floor((now-t)/60000)):Infinity;};
export function statusText(code){return ({1:'尚未開賽',3:'比賽結束',4:'比賽進行中',5:'取消',6:'延賽',7:'保留比賽'})[Number(code)]||'狀態待確認';}
const statusStyle=code=>Number(code)===4?'active':Number(code)===3?'final':Number(code)===1?'scheduled':'other';
export function officialLink(g){const y=Number(g.year),s=Number(g.gameSno),k=String(g.kindCode||'');if(!Number.isInteger(y)||y<1990||y>2035||!Number.isInteger(s)||s<=0||s>99999||!/^[A-Z]$/.test(k))return 'https://www.cpbl.com.tw/schedule';return `https://www.cpbl.com.tw/box/live?gameSno=${s}&kindCode=${k}&year=${y}`;}
function score(n){return Number.isInteger(n)&&n>=0?String(n):'—';}
function gameCard(g,old){const events=Array.isArray(g.events)?g.events:[], innings=Array.isArray(g.innings)?g.innings:[];
 const recent=events.at(-1),inning=recent?.inning ? `${recent.inning} 局${recent.side===1?'上':recent.side===2?'下':''}` : '';
 const last=recent?.hitter ? `${esc(recent.hitter)} · ${esc(recent.action||recent.content||'最新紀錄')}` : '詳細資訊以中職官網為準';
 const canDetail=events.length>0 || innings.length>0;
 const scoreBoard=innings.length?`<div class="live-line-scroll"><table class="live-line"><thead><tr><th>隊伍</th>${innings.map(x=>`<th>${x.inning}</th>`).join('')}<th>R</th><th>H</th><th>E</th></tr></thead><tbody><tr><td>${esc(g.away)}</td>${innings.map(x=>`<td>${score(x.away)}</td>`).join('')}<td>${score(g.awayScore)}</td><td>${score(g.awayHits)}</td><td>${score(g.awayErrors)}</td></tr><tr><td>${esc(g.home)}</td>${innings.map(x=>`<td>${score(x.home)}</td>`).join('')}<td>${score(g.homeScore)}</td><td>${score(g.homeHits)}</td><td>${score(g.homeErrors)}</td></tr></tbody></table></div>`:'';
 const diamond=recent&&g.statusCode===4&&Number.isInteger(recent.outs)?`<div class="live-situation"><div class="live-bso"><span><b>B</b> ${score(recent.balls)}</span><span><b>S</b> ${score(recent.strikes)}</span><span><b>O</b> ${score(recent.outs)}</span></div><div class="base-diamond" aria-label="壘包狀態：一壘${recent.first?'有人':'空'}、二壘${recent.second?'有人':'空'}、三壘${recent.third?'有人':'空'}"><span class="base second ${recent.second?'occupied':''}"></span><span class="base third ${recent.third?'occupied':''}"></span><span class="base first ${recent.first?'occupied':''}"></span></div></div>`:'';
 return `<article class="live-match"><div class="live-match-top"><span class="live-state ${statusStyle(g.statusCode)}">${statusText(g.statusCode)}</span><span class="live-meta">${esc(g.stadium||'球場未提供')} · ${esc(g.startAt ? String(g.startAt).slice(11,16) : '')} · ${esc(({A:'一軍例行賽',C:'總冠軍賽',E:'季後挑戰賽',D:'二軍例行賽',F:'二軍總冠軍賽'})[g.kindCode]||g.kindCode||'')} 第 ${esc(g.gameSno)} 場</span></div>
 <div class="live-scoreline"><div class="live-side"><small>客隊 AWAY</small><b>${esc(g.away)}</b></div><div class="live-score"><span>${score(g.awayScore)}</span><em>:</em><span>${score(g.homeScore)}</span></div><div class="live-side home"><small>主隊 HOME</small><b>${esc(g.home)}</b></div></div>
 ${canDetail?scoreBoard:''}${diamond}<div class="live-current"><strong>${esc(inning||'比賽狀況')}</strong><span>${old?'資料已過期 · ':''}${last}</span></div>
 <div class="live-actions"><button type="button" class="action" data-live-game="${esc(g.id)}">${canDetail?'檢視逐打席':'場次資訊'}</button><a class="action primary" href="${officialLink(g)}" target="_blank" rel="noopener noreferrer">中職官方即時文字轉播 ↗</a><a class="action" href="${esc(g.statsUrl||'https://stats.cpbl.com.tw/schedule')}" target="_blank" rel="noopener noreferrer">進階數據賽事頁 ↗</a></div>
 <div class="live-events hidden" id="live-events-${esc(g.id)}">${events.length?`<h3>最近 ${Math.min(events.length,80)} 筆戰況（最新在前）</h3><div class="live-filters" role="group" aria-label="打席事件篩選"><button type="button" class="selected" data-live-filter="all">全部</button><button type="button" data-live-filter="scoring">得分</button><button type="button" data-live-filter="hits">安打</button><button type="button" data-live-filter="walks">保送</button><button type="button" data-live-filter="homers">全壘打</button></div><div class="live-log">${[...events].reverse().map(e=>`<div class="live-play" data-kind="${e.scored?'scoring ':''}${/安打|全壘打/.test(e.action||'')?'hits ':''}${/保送|四壞|敬遠/.test(e.action||'')?'walks ':''}${/全壘打/.test(e.action||'')?'homers ':''}"><small>${score(e.inning)} 局${e.side===1?'上':e.side===2?'下':''} · ${esc(e.hitter||'打席紀錄')} ${e.outs==null?'':`· ${score(e.outs)} 出局`}</small><strong>${esc(e.action||'打席進行')}</strong><p>${esc(e.content||'詳情請見官方轉播')}</p></div>`).join('')}</div>`:'<p class="notes">這場目前沒有可供顯示的逐打席資料，請開啟中職官方文字轉播。</p>'}</div></article>`;
}
export function liveMarkup(data,selectedDay=taipeiDay(),now=Date.now()){
 if(!data||data.schemaVersion!==1||data.date!==selectedDay||!Array.isArray(data.games))throw Error('轉播資料格式或日期不符');
 const isHistorical=selectedDay<taipeiDay(new Date(now));
 const old=!isHistorical&&ageMinutes(data.updatedAt,now)>15;
 const time=esc(formatTime(data.updatedAt));
 const badge=isHistorical?'<span class="live-fresh">已同步的歷史賽事</span>':old?'<span class="live-fresh late">快照已過期，不代表當前比分</span>':'<span class="live-fresh">最近取得的官方資料快照</span>';
 const title=data.games.length?`${data.games.length} 場比賽 · ${selectedDay}`:`${selectedDay} 尚無場次`;
 return `<div class="live-readout"><div>${badge}<h2>${title}</h2><p>最後成功更新：${time}（臺灣時間）${old?' · 建議直接開啟官方文字轉播':''}</p></div><a href="https://www.cpbl.com.tw/schedule" target="_blank" rel="noopener noreferrer" class="source-btn">官方賽程 ↗</a></div>
 ${data.games.length?`<div class="live-match-list">${data.games.map(g=>gameCard(g,old)).join('')}</div>`:'<div class="empty live-none">${selectedDay}：已成功查詢官方場次清單，當日沒有賽事紀錄。可在上方選擇「最近有比賽的日期」查看過去的比賽。</div>'}
 ${data.detailFailures?`<p class="live-note">${data.detailFailures} 場的逐球明細暫時未能取得；比分清單及官方原站入口仍可使用。</p>`:''}${data.missingKinds?.length?`<p class="live-note">部分賽事類別暫時無法同步：${esc(data.missingKinds.join('、'))}，當日場次清單可能不完整。</p>`:''}`;
}
export function parseArchiveIndex(payload){
 if(!payload||payload.schemaVersion!==1||!Array.isArray(payload.dates))throw Error('歷史索引格式不正確');
 const seen=new Set();return payload.dates.filter(x=>{
   if(!x||typeof x.date!=='string'||!/^20\d\d-\d\d-\d\d$/.test(x.date)||!Number.isInteger(x.games)||x.games<0||x.games>32||seen.has(x.date))return false;
   seen.add(x.date);return true;
 }).sort((a,b)=>b.date.localeCompare(a.date));
}
let token=0,interval=null,chosenDay=taipeiDay();
async function readArchiveIndex(){
 try{
  const response=await fetch(`./data/live/index.json?t=${Date.now()}`,{cache:'no-store'});
  if(!response.ok)throw Error(`索引 HTTP ${response.status}`);
  const days=parseArchiveIndex(await response.json());
  const panel=byId('live-recent');if(!panel)return;
  const matches=days.filter(d=>d.games>0).slice(0,12);
  if(matches.length){
   panel.innerHTML=`<strong>最近有比賽的日期</strong> <span class="live-recent-days">${matches.map(d=>`<button type="button" class="action" data-live-day="${esc(d.date)}">${esc(d.date.slice(5))} · ${d.games} 場</button>`).join('')}</span>`;
   panel.querySelectorAll('[data-live-day]').forEach(b=>b.addEventListener('click',()=>{
     chosenDay=b.dataset.liveDay;byId('live-date').value=chosenDay;refresh();
   }));
  }else{
   panel.textContent=days.length?'目前同步紀錄中沒有已開賽的日期。':'資料庫已有索引，但尚未回補比賽紀錄。';
  }
 }catch(e){const panel=byId('live-recent');if(panel)panel.innerHTML='<strong>比賽歷史尚未同步。</strong> 請確認 GitHub Actions 的官方資料同步是否成功；不是「中職沒有比賽」。';}
}
export function teardownLive(){token++;if(interval)clearInterval(interval);interval=null;}
async function readDay(day,id){
 const box=byId('live-results');if(!box)return;
 const url=`./data/live/${day}.json?t=${Date.now()}`;
 try{
  const res=await fetch(url,{cache:'no-store'});
  if(!res.ok)throw Error(`尚無該日期的資料快照（HTTP ${res.status}）`);
  if(Number(res.headers.get('content-length'))>1000000)throw Error('快照檔案異常過大');
  const data=await res.json();
  if(id!==token||!byId('live-results'))return;
  box.innerHTML=liveMarkup(data,day);
  box.querySelectorAll('[data-live-game]').forEach(el=>el.addEventListener('click',()=>{
   const match=[...box.querySelectorAll('.live-events')].find(x=>x.id===`live-events-${el.dataset.liveGame}`);
   if(match){match.classList.toggle('hidden');el.textContent=match.classList.contains('hidden')?'檢視逐打席':'收合逐打席';}
  }));
  box.querySelectorAll('[data-live-filter]').forEach(el=>el.addEventListener('click',()=>{
    const parent=el.closest('.live-events');
    parent.querySelectorAll('[data-live-filter]').forEach(b=>b.classList.toggle('selected',b===el));
    parent.querySelectorAll('.live-play').forEach(item=>{item.hidden=el.dataset.liveFilter!=='all'&&!item.dataset.kind.split(' ').includes(el.dataset.liveFilter)});
  }));
 }catch(e){if(id!==token||!byId('live-results'))return;box.innerHTML=`<div class="empty live-none"><h3>尚未取得 ${esc(day)} 的戰況快照</h3><p>${esc(e.message)}</p><p>這代表 ATLAS 沒有該日已驗證的快照，<b>不代表該日沒有比賽</b>。官方資料同步尚未成功、該日期未回補，或資料來源暫時無法存取。此處不會顯示模擬比分。</p><div class="live-links"><a href="https://stats.cpbl.com.tw/schedule" target="_blank" rel="noopener noreferrer" class="action primary">前往中職進階數據賽程 ↗</a><a href="https://www.cpbl.com.tw/schedule" target="_blank" rel="noopener noreferrer" class="action">中職官方賽程 ↗</a></div></div>`;}
}
function refresh(){const id=++token;return readDay(chosenDay,id)}
export function renderLive(container){teardownLive();chosenDay=taipeiDay();
 const minDay=new Date(Date.now()-365*86400000);const min=taipeiDay(minDay),today=taipeiDay();
 container.innerHTML=`<div class="live-hero"><div><div class="eyebrow"><span class="green-dot"></span> CPBL LIVE CENTRE</div><h2>球場戰況，即時掌握。</h2><p>官方來源快照 · GitHub Actions 比賽時段約每 5 分鐘抓取（可能延遲）。瀏覽器每分鐘檢查快照。零延遲逐球資訊請使用官方文字轉播。</p></div><a class="action primary" href="https://www.cpbl.com.tw/schedule" target="_blank" rel="noopener noreferrer">中職官方賽程 ↗</a></div>
 <div class="live-toolbar"><label for="live-date">比賽日期</label><input id="live-date" type="date" class="filter-select" value="${chosenDay}" min="${min}" max="${today}"><button type="button" class="action" id="live-today">今天</button><button type="button" class="action" id="live-reload">重新取得快照 ↻</button><small>資料非同步直播；每筆戰況皆標示來源時間</small></div>
 <div id="live-recent" class="live-recent"><span>正在查詢歷史比賽索引…</span></div>
 <div id="live-results" aria-live="polite"><div class="loading">正在讀取中職官方戰況快照…</div></div>
 <div class="live-disclosure">本頁為第三方製作的準即時文字戰況整理，不是中職官方授權轉播，也不提供未經授權的比賽影片。官方網站的即時更新頻率、場次資料及使用權利均以原站為準。</div>`;
 byId('live-date').addEventListener('change',e=>{if(e.target.value){chosenDay=e.target.value;byId('live-results').innerHTML='<div class="loading">正在載入該日戰況…</div>';refresh()}});
 byId('live-today').addEventListener('click',()=>{chosenDay=taipeiDay();byId('live-date').value=chosenDay;refresh()});
 byId('live-reload').addEventListener('click',()=>refresh());
 refresh();
 readArchiveIndex();
 interval=setInterval(()=>{if(chosenDay===taipeiDay()&&document.visibilityState!=='hidden')refresh()},60000);
}
