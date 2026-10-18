import {manifest,loadSeason,loadCareer,div,fmtIp} from './data.js';
import {applySeasonMetrics,withQualification,RATE_BAT,RATE_PIT} from './advanced.js';
const $=s=>document.querySelector(s);
const escapeHtml=s=>String(s??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
const fmt=(val,n=0)=>val===null||val===undefined||!Number.isFinite(Number(val))?'—':Number(val).toLocaleString('en-US',{minimumFractionDigits:n,maximumFractionDigits:n});
const pct=(val,n=1)=>val==null?'—':fmt(val,n)+'%';
const pages={overview:['總覽','從職棒元年到現在，找到每個球季背後的故事。'],batting:['打者數據','歷年打擊排行榜，切換球季、球隊與進階指標。'],pitching:['投手數據','每一顆好球的價值，都藏在數字裡。'],fielding:['守備數據','查詢各守備位置刺殺、助殺、失誤、守備率及雙殺。'],teams:['球隊戰績','歷年每支球隊的勝敗與球季表現。'],insights:['聯盟分析','從全聯盟和各隊角度解讀打擊、投球與得失分。'],official:['中職資訊','官方賽程、成績看板、球員異動、年度獎項與進階分析入口。'],compare:['球員比較','同球季一對一比較，讓數據說話。'],about:['數據說明','透明揭露資料年份、來源、公式與使用限制。']};
const state={page:'overview',year:2024,season:null,years:[],source:null,search:'',team:'all',sort:'',desc:true,pageNo:0,compare:[null,null],compareKind:'batting',qualifiedOnly:true,standingPart:'all',metricView:'all',fieldPos:'all',fieldMinTC:0,fieldSort:'TC'};
const BAT_FIELDS=[['name','球員'],['team','球隊'],['G','G'],['PA','PA'],['AB','AB'],['H','H'],['HR','HR'],['RBI','RBI'],['R','R'],['BB','BB'],['SO','SO'],['avg','AVG'],['obp','OBP'],['slg','SLG'],['ops','OPS'],['iso','ISO'],['babip','BABIP'],['kpct','K%'],['bbpct','BB%'],['xbh','XBH'],['xbhpct','XBH%'],['sec','SecA'],['gp','GPA'],['rc','RC'],['sbpct','SB%'],['bbk','BB/K'],['gofo','GO/FO'],['hrPct','HR%'],['tbPerPA','TB/PA'],['paPerHR','PA/HR'],['bbMinusK','BB−K%'],['opsPlusOfficial','OPS+ 官'],['bipPctOfficial','BIP% 官'],['qual','資格']];
const PIT_FIELDS=[['name','球員'],['team','球隊'],['G','G'],['GS','GS'],['W','W'],['L','L'],['SV','SV'],['HLD','HLD'],['IP','IP'],['SO','SO'],['BB','BB'],['ER','ER'],['era','ERA'],['whip','WHIP'],['k9','K/9'],['bb9','BB/9'],['h9','H/9'],['hr9','HR/9'],['kbb','K/BB'],['kpct','K%'],['bbpct','BB%'],['kbbpct','K-BB%'],['pPerInning','P/IP'],['pPerBatter','P/BF'],['fip','FIP'],['eraPlusOfficial','ERA+ 官'],['hrPct','HR/BF%'],['ipPerGame','IP/G'],['qual','資格']];
const BASIC_BAT=new Set(['name','team','G','PA','AB','H','HR','RBI','R','BB','SO','avg','obp','slg','ops','qual']);
const ADV_BAT=new Set(['name','team','PA','avg','obp','slg','ops','iso','babip','kpct','bbpct','xbh','xbhpct','sec','gp','rc','sbpct','bbk','gofo','hrPct','tbPerPA','paPerHR','bbMinusK','opsPlusOfficial','bipPctOfficial','qual']);
const BASIC_PIT=new Set(['name','team','G','GS','W','L','SV','HLD','IP','SO','BB','ER','era','whip','qual']);
const ADV_PIT=new Set(['name','team','IP','SO','BB','era','whip','k9','bb9','h9','hr9','kbb','kpct','bbpct','kbbpct','pPerInning','pPerBatter','fip','eraPlusOfficial','hrPct','ipPerGame','qual']);
const battingNums=new Set(['avg','obp','slg','ops','iso','babip','sec','gp','bbk','gofo','tbPerPA','paPerHR']);
const pitDecimals=new Set(['era','whip','k9','bb9','h9','hr9','kbb','pPerInning','pPerBatter','fip','gofo','ipPerGame']);
function metricValue(row,key){if(key==='IP')return row.outs??0;if(key==='qual')return Number(row.qualified);return row[key]??(row[key]===0?0:-Infinity)}
function fieldFormat(row,key){if(key==='qual')return row.threshold==null?'—':`${row.qualified?'✓':'–'} ${row.PA??row.IP}/${row.PA==null?row.threshold/3:row.threshold}${row.PA==null?' IP':' PA'}`;if(key==='IP')return row.IP;if(battingNums.has(key))return fmt(row[key],3);if(pitDecimals.has(key))return fmt(row[key],2);if(key.endsWith('pct')||['hrPct','bbMinusK','bipPctOfficial'].includes(key))return pct(row[key]);if(['name','team'].includes(key))return escapeHtml(row[key]);return fmt(row[key])}
function withSeason(){if(!state.season)throw Error('球季尚未載入');return state.season}
function grouped(kind,teamFilter='all'){
  const raw=withSeason()[kind]||[];
  const rows=teamFilter==='all'?raw:raw.filter(r=>r.teamId===teamFilter);
  const m=new Map();
  const rates=kind==='batting'?RATE_BAT:RATE_PIT;
  for(const r of rows){
    if(!m.has(r.id)){m.set(r.id,{...r,_teams:new Set([r.team]),_teamIds:new Set([r.teamId])});continue;}
    const o=m.get(r.id);o._teams.add(r.team);o._teamIds.add(r.teamId);
    for(const [key,val] of Object.entries(r)){
      if(['id','name','team','teamId','pos','IP','_teams','_teamIds','qual','threshold','qualified'].includes(key)||rates.has(key)||!Number.isFinite(val))continue;
      o[key]=(o[key]||0)+val;
    }
    if(kind==='pitching')o.IP=fmtIp(o.outs);
  }
  const united=[...m.values()].map(r=>({...r,team:r._teams.size>1?'多隊':r.team,
    opsPlusOfficial:r._teams.size>1?null:r.opsPlusOfficial,
    bipPctOfficial:r._teams.size>1?null:r.bipPctOfficial,
    fipOfficial:r._teams.size>1?null:r.fipOfficial,
    eraPlusOfficial:r._teams.size>1?null:r.eraPlusOfficial}));
  const enhanced=applySeasonMetrics(united,kind,kind==='pitching'?raw:[]);
  return withQualification(enhanced,withSeason().teams,kind);
}
const teamOptions=()=>{const teams=withSeason().teams;return `<option value="all">全部球隊</option>${teams.map(t=>`<option value="${escapeHtml(t.id)}" ${t.id===state.team?'selected':''}>${escapeHtml(t.name)}</option>`).join('')}`};
function statsCards(entries){return `<div class="stats-grid">${entries.map(([label,val,foot,icon])=>`<div class="stat-card"><div class="stat-label">${label}<i>${icon||'↗'}</i></div><div class="stat-value">${val}</div><div class="stat-unit">${foot}</div></div>`).join('')}</div>`}
function panel(title,subtitle,inner,action=''){return `<div class="panel"><div class="panel-header"><div><h2>${title}</h2><p>${subtitle}</p></div>${action}</div>${inner}</div>`}
function barChart(rows,key,dec=0){const values=rows.map(r=>Math.max(0,Number(r[key]||0))),max=Math.max(...values,1);return `<div class="chart">${rows.map((r,i)=>`<div class="bar-row"><div class="bar-name">${escapeHtml(r.name)}</div><div class="bar-track"><div class="bar-fill" style="width:${Math.round(values[i]/max*100)}%"></div></div><div class="bar-num">${fmt(values[i],dec)}</div></div>`).join('')}</div>`}
function overview(){
  const d=withSeason(),b=grouped('batting'),p=grouped('pitching');
  const seasonHr=b.reduce((s,r)=>s+r.HR,0),totalPA=b.reduce((s,r)=>s+r.PA,0),totalAB=b.reduce((s,r)=>s+r.AB,0),hits=b.reduce((s,r)=>s+r.H,0);
  const leaders=b.filter(r=>r.qualified&&r.ops!=null).sort((a,c)=>c.ops-a.ops).slice(0,7);
  const hr=[...b].sort((a,c)=>c.HR-a.HR).slice(0,6);
  const era=p.filter(r=>r.qualified&&r.era!=null).sort((a,c)=>a.era-c.era).slice(0,6);
  const top=panel('OPS 領先群','達規定打席 · 3.1 × 所屬球隊已賽場數',leaders.length?barChart(leaders,'ops',3):'<p class="notes">尚無達規定打席的球員。</p>',`<button class="muted-link" data-go="batting">完整打者排行 ↗</button>`);
  const hrPanel=panel('全壘打排行榜','累積項目不設最低打席門檻',`<table class="mini-table"><thead><tr><th>#</th><th>球員</th><th>球隊</th><th style="text-align:right">HR</th></tr></thead><tbody>${hr.map((r,i)=>`<tr><td class="rank">${i+1}</td><td>${escapeHtml(r.name)}</td><td>${escapeHtml(r.team)}</td><td style="text-align:right">${r.HR}</td></tr>`).join('')}</tbody></table>`, `<button class="muted-link" data-go="batting">查看全部 ↗</button>`);
  return `${statsCards([['球季球隊',fmt(d.teams.length),'參賽球隊數','◫'],['年度打者',fmt(b.length),'曾有打擊紀錄球員','◉'],['總全壘打',fmt(seasonHr),'球季打者全壘打合計','↗'],['聯盟打擊率',fmt(div(hits,totalAB),3),`共 ${fmt(totalPA)} 打席`,'◆']])}<div class="section-grid">${top}${hrPanel}</div><div class="section-label"><h2>投手焦點</h2><small>ERA 榜採規定投球局數</small></div><div class="section-grid">${panel('防禦率排行榜','至少完成球隊已賽場數等量的投球局數',`<table class="mini-table"><thead><tr><th>#</th><th>球員</th><th>球隊</th><th style="text-align:right">ERA</th></tr></thead><tbody>${era.map((r,i)=>`<tr><td class="rank">${i+1}</td><td>${escapeHtml(r.name)}</td><td>${escapeHtml(r.team)}</td><td style="text-align:right">${fmt(r.era,2)}</td></tr>`).join('')}</tbody></table>${era.length?'':'<p class="notes">尚無符合規定投球局數的球員。</p>'}`,`<button class="muted-link" data-go="pitching">完整投手排行 ↗</button>`)}${panel('球季使用說明','歷年球季與進階分析',`<div class="fineprint">各排行榜依官方累積數值計算；比率榜需符合打席／投球局數門檻。<p>已可計算 GPA、SecA、RC、XBH%、K-BB%、P/IP 等進階指標。FIP 只有在相關原始欄位齊全時才計算，資料缺值顯示「—」。</p>2025–2026 最新紀錄需正式來源連接器通過驗證後才會顯示。</div>`)}</div>`;
}
function tablePage(kind){
  const isB=kind==='batting';
  const selection=state.metricView==='basic'?(isB?BASIC_BAT:BASIC_PIT):state.metricView==='advanced'?(isB?ADV_BAT:ADV_PIT):null;
  const fields=(isB?BAT_FIELDS:PIT_FIELDS).filter(([key])=>!selection||selection.has(key));
  const sort=state.sort||(isB?'ops':'SO');
  const rateSort=(isB?RATE_BAT:RATE_PIT).has(sort);
  const allRows=grouped(kind,state.team).filter(r=>!state.search||[r.name,r.team,r.id].some(s=>String(s).toLowerCase().includes(state.search.toLowerCase())));
  const activeQualification=state.qualifiedOnly&&rateSort;
  const rows=activeQualification?allRows.filter(r=>r.qualified):allRows;
  rows.sort((a,b)=>{const av=metricValue(a,sort),bv=metricValue(b,sort);let cmp;
    if(typeof av==='string'||typeof bv==='string')cmp=String(av??'').localeCompare(String(bv??''),'zh-Hant');
    else cmp=(Number.isFinite(av)?av:-Infinity)-(Number.isFinite(bv)?bv:-Infinity);
    return state.desc?-cmp:cmp;
  });
  const size=30,maxPage=Math.max(0,Math.ceil(rows.length/size)-1);state.pageNo=Math.min(state.pageNo,maxPage);
  const display=rows.slice(state.pageNo*size,(state.pageNo+1)*size);
  const stat=isB?[['查詢打者',fmt(rows.length),'目前排行榜與篩選條件','◉'],['達標人數',fmt(allRows.filter(r=>r.qualified).length),'根據球隊已賽場數判斷','✓'],['全壘打',fmt(rows.reduce((s,r)=>s+r.HR,0)),'表列球員合計','↗'],['OPS 中位數',fmt((()=>{const v=rows.map(r=>r.ops).filter(Number.isFinite).sort((a,b)=>a-b);return v.length?v[Math.floor(v.length/2)]:null})(),3),'表列球員・未加權','◆']]:[['查詢投手',fmt(rows.length),'目前排行榜與篩選條件','◆'],['達標人數',fmt(allRows.filter(r=>r.qualified).length),'規定投球局數','✓'],['奪三振',fmt(rows.reduce((s,r)=>s+r.SO,0)),'表列投手合計','↗'],['救援成功',fmt(rows.reduce((s,r)=>s+r.SV,0)),'表列投手合計','◉']];
  return `${statsCards(stat)}<div class="panel"><div class="panel-header"><div><h2>${isB?'打擊數據排行榜':'投球數據排行榜'}</h2><p>點擊欄位排序，查看各項可靠推算的進階指標</p></div><button class="action" id="download">↓ 匯出 CSV</button></div>
    <div class="filters"><input id="search" class="search" type="search" placeholder="搜尋姓名、球隊或球員 ID" value="${escapeHtml(state.search)}"><select id="team" class="filter-select">${teamOptions()}</select><select id="metric-view" class="filter-select" aria-label="選擇數據欄位類型"><option value="all" ${state.metricView==='all'?'selected':''}>所有數據</option><option value="basic" ${state.metricView==='basic'?'selected':''}>基本數據</option><option value="advanced" ${state.metricView==='advanced'?'selected':''}>進階數據</option></select><label class="qual-toggle"><input id="qualified-only" type="checkbox" ${state.qualifiedOnly?'checked':''}><span>比率排名僅列達標球員</span></label><button class="action" id="clear-filters">清除篩選</button></div>
    <p class="notes qual-explain">${activeQualification?`已依規定篩選：${isB?'PA ≥ 球隊已賽場數 × 3.1（四捨五入）':'IP ≥ 球隊已賽場數'}。`:`本表目前依 ${escapeHtml(sort)} 排序；${rateSort?'顯示未達資格者（不列入正式達標榜）。':'累積項目不設打席或投球局數門檻。'}`} 不同球隊門檻可能不同，轉隊球員依其所屬各隊最多已賽場數保守計算。可左右滑動查看進階欄位。</p>
    <div class="table-scroll"><table class="data-table"><thead><tr><th>#</th>${fields.map(([k,n])=>`<th data-sort="${k}" class="${state.sort===k?'sorted':''}" title="點擊排序">${n}${state.sort===k?(state.desc?' ↓':' ↑'):''}</th>`).join('')}</tr></thead><tbody>${display.length?display.map((r,i)=>`<tr><td>${i+1+state.pageNo*size}</td>${fields.map(([k])=>`<td>${k==='name'?`<button class="player-link" data-player="${escapeHtml(r.id)}" data-kind="${kind}">${escapeHtml(r.name)}</button>`:k==='team'?`<span class="tag">${escapeHtml(r.team)}</span>`:fieldFormat(r,k)}</td>`).join('')}</tr>`).join(''):`<tr><td colspan="${fields.length+1}">目前沒有符合條件的球員；可取消達標篩選或切換排名欄位。</td></tr>`}</tbody></table></div><div class="table-bottom"><div>共 ${fmt(rows.length)} 位球員 · 第 ${state.pageNo+1} / ${maxPage+1} 頁</div><div class="pager"><button id="prev" ${state.pageNo===0?'disabled':''}>上一頁</button><button id="next" ${state.pageNo===maxPage?'disabled':''}>下一頁</button></div></div><p class="notes">打擊／投球成績按球員 ID 彙總同季跨隊表現；搜尋單一球隊只顯示該隊成績。FIP 根據當季聯盟自責分計算校正常數，僅在 IBB、HBP 等原始欄位齊全時提供。資格門檻是嚴格達標榜，不計官方少打席補算特例。</p></div>`;
}
function teamPage(){
  const d=withSeason(),parts=d.halves||{};
  const part=state.standingPart;
  const isSplit=part!=='all';
  const singleYears=new Set([1998,1999]);
  const active=isSplit?parts[part]:d.teams;
  const tabs=`<div class="standing-tabs" role="group" aria-label="選擇半季"><button data-part="first" class="${part==='first'?'selected':''}" ${singleYears.has(state.year)?'disabled title="該年不分上下半季"':''}>上半季</button><button data-part="second" class="${part==='second'?'selected':''}" ${singleYears.has(state.year)?'disabled title="該年不分上下半季"':''}>下半季</button><button data-part="all" class="${part==='all'?'selected':''}">全年</button></div>`;
  if(!Array.isArray(active)||active.length===0){return `${panel(`${state.year} 球季戰績`,isSplit?'資料缺漏不以全年數字假裝半季戰績':'官方年度戰績',tabs+`<div class="empty">${singleYears.has(state.year)?'本年度採單一球季制，沒有上下半季戰績。':'此年度尚無通過驗證的'+(part==='first'?'上':'下')+'半季官方戰績快照。請先執行半季資料同步；全年戰績仍可查詢。'}</div><p class="notes">半季資料與年度資料分開儲存。官方來源未完成驗證時，顯示缺漏而非推估。</p>`)}`;}
  const teams=[...active].map(t=>({...t,pct:div(t.w,t.w+t.l)})).sort((a,b)=>(b.pct??-1)-(a.pct??-1)||b.w-a.w);
  const top=teams[0];const title=part==='first'?'上半季':part==='second'?'下半季':'全年';
  return `${panel(`${state.year} ${title}球隊戰績`,'依年份切換上下半季與全年',tabs)}${statsCards([['參賽隊數',fmt(teams.length),title+'一軍例行賽','◫'],['聯盟場次',fmt(Math.round(teams.reduce((s,t)=>s+t.w+t.l+t.t,0)/2)),'按已完成戰績估算','◉'],['最高勝率球隊',escapeHtml(top?.short||top?.name||'—'),`${top?.w??0} 勝`,'↗'],['最高勝率',fmt(top?.pct,3),'和局不計入勝率','◆']])}<div class="section-label"><h2>${state.year} ${title}排行榜</h2><small>名次依勝率與勝場排列；官方特別排名依其規定</small></div><div class="team-grid">${teams.map((t,i)=>`<button class="team-card" data-team-go="${escapeHtml(t.id)}"><div class="team-title"><div class="team-monogram">${escapeHtml((t.short||t.name).slice(0,1))}</div><div><span class="rank">#${i+1}</span> ${escapeHtml(t.name)}</div></div><div class="team-record">${t.w}<span style="color:#778a8f">–</span>${t.l}<span style="font-size:13px;color:#8c9da2">–${t.t}</span></div><div class="team-meter"><div style="width:${Math.round((t.pct||0)*100)}%"></div></div><div class="team-small">勝率 ${fmt(t.pct,3)} · ${t.w+t.l+t.t} 場比賽${Number.isFinite(t.homeW)?`<p>主場 ${t.homeW}-${t.homeL}-${t.homeT} · 客場 ${t.awayW}-${t.awayL}-${t.awayT}</p>`:''}</div></button>`).join('')}</div><div class="section-label"><h2>歷年賽制說明</h2></div>${panel('半季、全年與冠軍資格','上下半季冠軍不等於全年勝率第一',`<div class="fineprint">半季資料需由官方歷年球隊戰績逐隊核對並經完整性驗證。1998、1999 年採單一球季，不會捏造半季排名。其他特殊賽季與總冠軍資格須依當年度聯盟制度判斷；此處的勝率排序不是直接授予季冠軍。<p>若選擇球隊卡片，將切換到該隊的<strong>全年</strong>打者統計，而非半季個人成績。</p></div>`)}`;
}

const FIELD_FIELDS=[['name','球員'],['team','球隊'],['pos','位置'],['G','G'],['TC','TC'],['PO','PO'],['A','A'],['E','E'],['DP','DP'],['TP','TP'],['PB','PB'],['CS','CS'],['SB','SB'],['fpct','FPCT']];
const POS={P:'投手',C:'捕手','1B':'一壘','2B':'二壘','3B':'三壘',SS:'游擊',LF:'左外野',CF:'中外野',RF:'右外野',OF:'外野',DH:'指定打擊'};
function fieldingPage(){
  const available=withSeason().fielding||[];
  if(!available.length)return panel(`${state.year} 守備數據`, '目前僅載入完成來源驗證的守備紀錄', '<div class="empty">此年度尚未匯入個別球員守備成績。打擊與投手資料可正常查看，這裡不會把缺漏守備率顯示成 0。</div><div class="links-group"><a class="source-btn" href="https://www.cpbl.com.tw/" target="_blank" rel="noopener">開啟中職官方網站 ↗</a></div>');
  const rows=available.filter(r=>(state.team==='all'||r.teamId===state.team)&&
      (state.fieldPos==='all'||r.pos===state.fieldPos)&&(r.TC>=state.fieldMinTC)&&
      (!state.search||[r.name,r.team,r.id].some(t=>String(t||'').toLowerCase().includes(state.search.toLowerCase()))));
  const sort=state.sort&&FIELD_FIELDS.some(([key])=>key===state.sort)?state.sort:state.fieldSort;
  rows.sort((a,b)=>{const av=a[sort],bv=b[sort];const cmp=typeof av==='string'||typeof bv==='string'?String(av??'').localeCompare(String(bv??''),'zh-Hant'):(Number.isFinite(av)?av:-Infinity)-(Number.isFinite(bv)?bv:-Infinity);return state.desc?-cmp:cmp});
  const filteredPos=[...new Set(available.map(r=>r.pos))].sort();
  const size=30;state.pageNo=Math.min(state.pageNo,Math.max(0,Math.ceil(rows.length/size)-1));
  const display=rows.slice(state.pageNo*size,(state.pageNo+1)*size);
  return `${statsCards([['防守紀錄',fmt(available.length),'各球員／守備位置紀錄','◈'],['篩選結果',fmt(rows.length),'符合位置與守備機會','✓'],['總刺殺',fmt(rows.reduce((a,r)=>a+r.PO,0)),'目前表列球員','◆'],['總助殺',fmt(rows.reduce((a,r)=>a+r.A,0)),'目前表列球員','↗']])}
  <div class="panel"><div class="panel-header"><div><h2>${state.year} 年守備排行榜</h2><p>每個守備位置一筆紀錄；TC 為守備機會，FPCT = (刺殺+助殺)/守備機會</p></div><button class="action" id="download-fielding">↓ CSV</button></div>
  <div class="filters"><input id="search" class="search" type="search" placeholder="搜尋球員、球隊" value="${escapeHtml(state.search)}"><select class="filter-select" id="team">${teamOptions()}</select>
  <select class="filter-select" id="field-pos"><option value="all">全部守備位置</option>${filteredPos.map(pos=>`<option value="${escapeHtml(pos)}" ${pos===state.fieldPos?'selected':''}>${escapeHtml(POS[pos]||pos)}</option>`).join('')}</select>
  <select class="filter-select" id="field-tc">${[0,25,50,100,200].map(n=>`<option value="${n}" ${n===state.fieldMinTC?'selected':''}>至少 ${n} 守備機會</option>`).join('')}</select><button class="action" id="clear-filters">清除</button></div>
  <div class="table-scroll"><table class="data-table"><thead><tr><th>#</th>${FIELD_FIELDS.map(([key,label])=>`<th data-sort="${key}" class="${sort===key?'sorted':''}">${label}${sort===key?(state.desc?' ↓':' ↑'):''}</th>`).join('')}</tr></thead><tbody>${display.map((r,i)=>`<tr><td>${state.pageNo*size+i+1}</td>${FIELD_FIELDS.map(([key])=>`<td>${key==='name'||key==='team'||key==='pos'?escapeHtml(key==='pos'?(POS[r.pos]||r.pos):r[key]):fmt(r[key],key==='fpct'?3:0)}</td>`).join('')}</tr>`).join('')}</tbody></table></div>
  <div class="table-bottom"><span>找到 ${rows.length} 筆 · 第 ${state.pageNo+1} / ${Math.max(1,Math.ceil(rows.length/size))} 頁</span><div class="pager"><button id="prev" ${state.pageNo===0?'disabled':''}>上一頁</button><button id="next" ${(state.pageNo+1)*size>=rows.length?'disabled':''}>下一頁</button></div></div><p class="notes">單一球員可能出現在不同守備位置。此處「守備機會」條件是研究篩選，不是聯盟正式守備王認定。</p></div>`;
}
function insightPage(){
  const d=withSeason();const b=d.batting,p=d.pitching;
  const sums=(rs,key)=>rs.reduce((s,r)=>s+Number(r[key]||0),0);
  const ab=sums(b,'AB'),hits=sums(b,'H'),pa=sums(b,'PA'),hr=sums(b,'HR'),bb=sums(b,'BB'),hbp=sums(b,'HBP'),sf=sums(b,'SF'),tb=sums(b,'TB');
  const teamNames=new Map(d.teams.map(t=>[t.id,t.name]));
  const teams=[...teamNames].map(([id,name])=>{
    const hitters=b.filter(r=>r.teamId===id),arms=p.filter(r=>r.teamId===id);
    const a=sums(hitters,'AB'),h=sums(hitters,'H'),t=sums(hitters,'TB'),walk=sums(hitters,'BB'),hbp=sums(hitters,'HBP'),sac=sums(hitters,'SF'),outs=sums(arms,'outs');
    const avg=div(h,a),obp=div(h+walk+hbp,a+walk+hbp+sac),slg=div(t,a);
    return {id,name,PA:sums(hitters,'PA'),HR:sums(hitters,'HR'),R:sums(hitters,'R'),SO:sums(hitters,'SO'),
      SB:sums(hitters,'SB'),avg,obp,slg,ops:obp!=null&&slg!=null?obp+slg:null,
      teamEra:div(27*sums(arms,'ER'),outs),k9:div(27*sums(arms,'SO'),outs),whip:div(3*(sums(arms,'H')+sums(arms,'BB')),outs),outs};
  });
  teams.sort((a,b)=>(b.ops??-1)-(a.ops??-1));
  const tableCols=[['name','球隊'],['PA','PA'],['avg','AVG'],['obp','OBP'],['slg','SLG'],['ops','OPS'],['HR','HR'],['R','R'],['SO','K'],['SB','SB'],['teamEra','ERA'],['whip','WHIP'],['k9','K/9']];
  return `${statsCards([['聯盟 OPS',fmt((()=>{const o=div(hits+bb+hbp,ab+bb+hbp+sf),sl=div(tb,ab);return o==null||sl==null?null:o+sl})(),3),'依全聯盟累積打擊紀錄計算','◆'],['聯盟全壘打',fmt(hr),'所有球隊打者合計','↗'],['聯盟三振',fmt(sums(b,'SO')),'打者被三振數','◉'],['聯盟打席',fmt(pa),'已收錄球員打席合計','▦']])}
    <div class="section-label"><h2>${state.year} 各隊進攻／投球概況</h2><small>由球員累積紀錄彙整，非官方獨立球隊統計</small></div>
    ${panel('球隊進階比較','OPS、ERA、K/9 等統一使用原始球員加總後計算，不平均個別球員的比率。',`<div class="table-scroll"><table class="data-table"><thead><tr><th>#</th>${tableCols.map(([,label])=>`<th>${label}</th>`).join('')}</tr></thead><tbody>${teams.map((t,i)=>`<tr><td>${i+1}</td>${tableCols.map(([key])=>`<td>${key==='name'?escapeHtml(t[key]):['avg','obp','slg','ops'].includes(key)?fmt(t[key],3):['teamEra','whip','k9'].includes(key)?fmt(t[key],2):fmt(t[key])}</td>`).join('')}</tr>`).join('')}</tbody></table></div><p class="notes">這裡 ERA 是已收錄投手的自責分與出局數合計；打者得分是個人記錄加總。比率可能與官方球隊統計存在統計口徑差異。</p>`)}
    <div class="section-label"><h2>聯盟數據比較</h2></div><div class="section-grid">${panel('球隊 OPS','全隊累計打擊結果計算',barChart(teams.filter(t=>t.ops!=null),'ops',3))}${panel('球隊全壘打','當年球隊球員全壘打加總',barChart([...teams].sort((a,b)=>b.HR-a.HR),'HR'))}</div>`;
}
const OFFICIAL_LINKS=[
  ['中職賽程','官方月曆、列表、比賽球場','https://www.cpbl.com.tw/schedule'],
  ['成績看板／Box Score','逐局戰況、先發、球員單場成績','https://www.cpbl.com.tw/box'],
  ['單項排行榜','打擊率、全壘打、ERA、勝投等','https://www.cpbl.com.tw/stats/toplist'],
  ['全記錄查詢','2025、2026 官方打投數值及進階欄位','https://www.cpbl.com.tw/stats/recordall'],
  ['歷年全壘打明細','依打者、投手、年度、場次檢索全壘打','https://www.cpbl.com.tw/stats/hr/'],
  ['歷年球隊戰績','上下半季與全年戰績、主客場數據','https://www.cpbl.com.tw/standings/season'],
  ['中華職棒進階排行榜','擊球彈道、球速轉速、擊球初速、PR','https://stats.cpbl.com.tw/rankings'],
  ['中華職棒進階賽程','2026 一軍、二軍與季後賽','https://stats.cpbl.com.tw/schedule'],
  ['球員點將錄','球員名單、基本介紹與個人成績','https://www.cpbl.com.tw/player'],
  ['中職新聞公告','聯盟賽事公告、異動與最新消息','https://www.cpbl.com.tw/']
];
function officialPage(){
  const have2025=state.years.includes(2025),have2026=state.years.includes(2026);
  return `<div class="panel"><div class="panel-header"><div><h2>2025 / 2026 資料接入狀態</h2><p>官方資料實際同步成功後才會在本站出現年份，不宣稱已完成仍不存在的匯入。</p></div></div>
    <div class="filters"><span class="data-badge ${have2025?'':'missing'}">2025 ${have2025?'已有驗證快照':'尚待官方同步'}</span><span class="data-badge ${have2026?'':'missing'}">2026 ${have2026?'已有驗證快照':'尚待官方同步'}</span></div>
    <p class="notes">2025 和 2026 官網已提供打者、投手數據；ATLAS 需要在 GitHub Actions 或其他可連線環境中成功下載、核對並輸出相應年度快照。2026 進階站的 Trackman 等資料不會自動等同本地已匯入。</p></div>
    <div class="section-label"><h2>中職官網功能入口</h2><small>本站尚未完成獨立匯入的項目連往聯盟原始資料</small></div>
    <div class="portal-grid">${OFFICIAL_LINKS.map(([title,detail,url])=>`<a class="portal-card" href="${url}" target="_blank" rel="noopener noreferrer"><strong>${title}</strong><span>${detail}</span><small>前往官方網站 ↗</small></a>`).join('')}</div>
    <div class="section-label"><h2>進階分析資料規劃</h2></div>
    ${panel('進階統計必須有正確資料來源','當年度官方欄位、追蹤資料與長期歷史資料，必須區分可用年度。',`<div class="metric-explainer" style="padding:0 23px 22px"><div><b>已可自行計算</b><p>AVG、OBP、OPS、BABIP、ISO、RC、K/9、WHIP、聯盟年度比較等。</p></div><div><b>來源有提供，待完整同步</b><p>2025/26 官方 OPS+、ERA+、FIP；2026 進階站球種、擊球分布、PR 等。</p></div><div><b>仍需模型或事件紀錄</b><p>WAR、wRC+、WPA、RE24、守備 UZR、Framing；不能直接由年度統計表推算。</p></div></div>`)}
  `;
}

function comparePage(){const kind=state.compareKind;const rows=grouped(kind).sort((a,b)=>a.name.localeCompare(b.name,'zh-Hant'));const fields=kind==='batting'?[['avg','AVG'],['obp','OBP'],['slg','SLG'],['ops','OPS'],['HR','HR'],['RBI','RBI'],['H','H'],['SO','SO']]:[['era','ERA'],['whip','WHIP'],['k9','K/9'],['SO','SO'],['W','W'],['SV','SV'],['BB','BB'],['outs','投球出局數']];const options=slot=>`<option value="">請選擇球員</option>${rows.map(r=>`<option value="${escapeHtml(r.id)}" ${r.id===state.compare[slot]?'selected':''}>${escapeHtml(r.name)} · ${escapeHtml(r.team)}</option>`).join('')}`;const a=rows.find(r=>r.id===state.compare[0]),b=rows.find(r=>r.id===state.compare[1]);return `${panel('球員一對一比較','限同球季、同類型球員。不同年代需先校正聯盟環境。',`<div class="filters"><select class="filter-select" id="compare-kind"><option value="batting" ${kind==='batting'?'selected':''}>打者</option><option value="pitching" ${kind==='pitching'?'selected':''}>投手</option></select></div><div class="compare-row"><select class="compare-select" id="compare-a">${options(0)}</select><select class="compare-select" id="compare-b">${options(1)}</select></div>${a&&b?`<div class="compare-row"><div class="compare-box"><div class="team-monogram" style="margin:auto">${escapeHtml(a.name.slice(0,1))}</div><b>${escapeHtml(a.name)}</b><p>${escapeHtml(a.team)}</p></div><div class="compare-box"><div class="team-monogram" style="margin:auto">${escapeHtml(b.name.slice(0,1))}</div><b>${escapeHtml(b.name)}</b><p>${escapeHtml(b.team)}</p></div></div><div class="compare-bars">${fields.map(([key,label])=>{const av=Number(a[key]||0),bv=Number(b[key]||0),mx=Math.max(av,bv,0.001);const val=k=>key==='outs'?fmtIp(k):fieldFormat({[key]:k},key);return `<div class="comparison-line"><div class="left-val">${val(av)}</div><div class="split-track"><span style="width:${av/mx*100}%"></span></div><b>${label}</b><div class="split-track right"><span style="width:${bv/mx*100}%"></span></div><div class="right-val">${val(bv)}</div></div>`}).join('')}</div>`:`<p class="notes">選好左右兩位球員，即可顯示各項數據差異。球員名單來自選定年度的官方歷史資料。</p>`}`)}`}
function aboutPage(){return `${panel('資料來源與授權','開放原始數據、有據可查，不把預測冒充紀錄',`<div class="fineprint"><p><b>目前可實際查詢的資料：1990–2024 年中職一軍例行賽。</b> 打者、投手、守備、球隊歷年成績來自 ldkrsi/cpbl-opendata（MIT 授權），原始資料是由中華職棒官網蒐集、勘誤整理。</p><p>網站會先使用專案的靜態驗證快照；尚未建立快照時，直接從開源資料專案讀取 CSV。來源有更新不代表官方即時更新，因此頁面不顯示「即時」字眼。</p><p><b>2025、2026：</b> ${state.years.includes(2026)||state.years.includes(2025)?"已列入選單的近年球季是透過中職官方全記錄查詢另行匯入；若未列入，代表尚未通過資料驗證。2025/26 守備細節及 Trackman 尚未匯入。":"尚未匯入目前可查詢的資料庫。"} 2025 年另有野球革命公開的逐場資料（ODC-By）；2026 年中職進階數據站有追蹤統計，但僅含該年度資料。這些來源仍需要獨立欄位與授權驗證後才能進一步整合。</p></div><div class="links-group"><a class="source-btn" href="https://github.com/ldkrsi/cpbl-opendata" target="_blank" rel="noopener">歷年開源資料 ↗</a><a class="source-btn" href="https://www.cpbl.com.tw/" target="_blank" rel="noopener">CPBL 官方 ↗</a><a class="source-btn" href="https://stats.cpbl.com.tw/" target="_blank" rel="noopener">CPBL 進階數據 ↗</a><a class="source-btn" href="https://github.com/rebas-tw/rebas.tw-open-data" target="_blank" rel="noopener">Rebas Open Data ↗</a></div>`)}<div class="section-label"><h2>數據計算方式</h2></div><div class="panel"><div class="panel-header"><h2>基礎進階指標</h2></div><div class="term-grid">${[['AVG 打擊率','H / AB'],['OBP 上壘率','(H + BB + HBP) / (AB + BB + HBP + SF)'],['SLG 長打率','TB / AB'],['OPS 整體攻擊指數','OBP + SLG'],['ISO 純長打率','SLG − AVG'],['BABIP 場內被安打率','(H − HR) / (AB − SO − HR + SF)'],['ERA 防禦率','ER × 9 / 真實投球局數'],['WHIP 每局被上壘數','(BB + H) / 真實投球局數'],['K/9 每九局三振','SO × 9 / 真實投球局數'],['BB/9 每九局保送','BB × 9 / 真實投球局數'],['SecA 次級打擊率','(TB − H + BB + SB − CS) / AB'],['GPA 打擊產出','(1.8 × OBP + SLG) / 4'],['RC 基礎得分創造','(H + BB) × TB / (AB + BB)'],['XBH% 長打占安打比例','(二壘打 + 三壘打 + 全壘打) / H'],['K-BB% 投手三振保送率差','(SO − BB) × 100 / BF'],['P/IP 每局投球數','NP / 真實投球局數'],['FIP（條件式）','(13HR + 3(BB − IBB + HBP) − 2SO) / IP + 當季聯盟常數（只在原始欄位完整時提供）']].map(([label,desc])=>`<div class="term"><b>${label}</b><p>${escapeHtml(desc)}</p></div>`).join('')}</div><p class="notes">投球局數例如 5.1 是 5 局 1 個出局數，並非 5.1 局。歷年原始資料可能存在改名、球員異動及未蒐集欄位；缺值不等於 0。未提供球場修正係數及逐球事件前，不計算 WAR、wRC+、UZR 等指標。</p></div>`}
function updateHeader(){const [name,desc]=pages[state.page];$('#crumb-page').textContent=name;$('#page-heading').innerHTML=`中職數據<span>${escapeHtml(name)}</span>`;$('#page-description').textContent=desc;document.querySelectorAll('[data-page]').forEach(a=>a.classList.toggle('active',a.dataset.page===state.page))}
function render(){updateHeader();if(state.page==='about'){$('#content').innerHTML=aboutPage();return}if(state.page==='official'){$('#content').innerHTML=officialPage();return}if(!state.season){$('#content').innerHTML='<div class="loading">正在載入球季資料…</div>';return}try{$('#content').innerHTML=state.page==='overview'?overview():state.page==='batting'?tablePage('batting'):state.page==='pitching'?tablePage('pitching'):state.page==='fielding'?fieldingPage():state.page==='teams'?teamPage():state.page==='insights'?insightPage():state.page==='official'?officialPage():comparePage();wire()}catch(e){$('#content').innerHTML=`<div class="error">頁面載入失敗：${escapeHtml(e.message)}</div>`}}
function wire(){document.querySelectorAll('[data-go]').forEach(x=>x.addEventListener('click',()=>nav(x.dataset.go)));document.querySelectorAll('[data-sort]').forEach(x=>x.addEventListener('click',()=>{const s=x.dataset.sort;state.desc=state.sort===s?!state.desc:true;state.sort=s;state.pageNo=0;render()}));$('#team')?.addEventListener('change',e=>{state.team=e.target.value;state.pageNo=0;render()});$('#search')?.addEventListener('input',e=>{const t=e.target;const start=t.selectionStart;state.search=t.value;state.pageNo=0;render();const el=$('#search');el.focus();el.setSelectionRange(start,start)});$('#clear-filters')?.addEventListener('click',()=>{state.search='';state.team='all';state.pageNo=0;state.qualifiedOnly=true;state.fieldPos='all';state.fieldMinTC=0;render()});$('#qualified-only')?.addEventListener('change',e=>{state.qualifiedOnly=e.target.checked;state.pageNo=0;render()});$('#metric-view')?.addEventListener('change',e=>{state.metricView=e.target.value;state.sort='';state.pageNo=0;render()});document.querySelectorAll('[data-part]').forEach(x=>x.addEventListener('click',()=>{state.standingPart=x.dataset.part;render()}));$('#next')?.addEventListener('click',()=>{state.pageNo++;render()});$('#prev')?.addEventListener('click',()=>{state.pageNo--;render()});$('#download')?.addEventListener('click',exportCsv);$('#field-pos')?.addEventListener('change',e=>{state.fieldPos=e.target.value;state.pageNo=0;render()});$('#field-tc')?.addEventListener('change',e=>{state.fieldMinTC=Number(e.target.value);state.pageNo=0;render()});$('#download-fielding')?.addEventListener('click',exportFieldingCsv);document.querySelectorAll('[data-player]').forEach(x=>x.addEventListener('click',()=>openPlayer(x.dataset.player,x.dataset.kind)));document.querySelectorAll('[data-team-go]').forEach(x=>x.addEventListener('click',()=>{state.team=x.dataset.teamGo;nav('batting')}));$('#compare-kind')?.addEventListener('change',e=>{state.compareKind=e.target.value;state.compare=[null,null];render()});$('#compare-a')?.addEventListener('change',e=>{state.compare[0]=e.target.value;render()});$('#compare-b')?.addEventListener('change',e=>{state.compare[1]=e.target.value;render()})}
function exportFieldingCsv(){
  const rows=(withSeason().fielding||[]).filter(r=>(state.team==='all'||r.teamId===state.team)&&(state.fieldPos==='all'||r.pos===state.fieldPos)&&r.TC>=state.fieldMinTC&&(!state.search||[r.name,r.team].some(x=>x.includes(state.search))));
  const q=x=>'"'+String(x??'').replace(/"/g,'""')+'"';
  const csv='\ufeff'+[FIELD_FIELDS.map(([,label])=>label).map(q).join(','),...rows.map(r=>FIELD_FIELDS.map(([key])=>r[key]).map(q).join(','))].join('\r\n');
  const url=URL.createObjectURL(new Blob([csv],{type:'text/csv;charset=utf-8'}));const a=document.createElement('a');a.href=url;a.download=`CPBL-fielding-${state.year}.csv`;a.click();setTimeout(()=>URL.revokeObjectURL(url),1000);
}
function exportCsv(){
  const kind=state.page,fields=kind==='batting'?BAT_FIELDS:PIT_FIELDS;
  const sort=state.sort||(kind==='batting'?'ops':'SO');
  let rows=grouped(kind,state.team).filter(r=>!state.search||[r.name,r.team,r.id].some(s=>String(s).toLowerCase().includes(state.search.toLowerCase())));
  if(state.qualifiedOnly&&(kind==='batting'?RATE_BAT:RATE_PIT).has(sort))rows=rows.filter(r=>r.qualified);
  rows.sort((a,b)=>{const av=metricValue(a,sort),bv=metricValue(b,sort);const cmp=typeof av==='string'||typeof bv==='string'?String(av).localeCompare(String(bv),'zh-Hant'):av-bv;return state.desc?-cmp:cmp;});
  const quote=s=>'"'+String(s??'').replace(/"/g,'""')+'"';
  const csv=['\ufeff'+['球員ID',...fields.map(x=>x[1])].map(quote).join(','),...rows.map(r=>[r.id,...fields.map(([key])=>key==='qual'?`${r.qualified?'達標':'未達標'} / 門檻 ${r.threshold??'資料缺漏'}`:r[key]??'')].map(quote).join(','))].join('\r\n');
  const blob=new Blob([csv],{type:'text/csv;charset=utf-8'}),url=URL.createObjectURL(blob),a=document.createElement('a');
  a.href=url;a.download=`CPBL-${kind}-${state.year}.csv`;a.click();setTimeout(()=>URL.revokeObjectURL(url),1000);
}
async function openPlayer(id,kind){const r=grouped(kind).find(x=>x.id===id);if(!r)return;const overlay=$('#overlay'),panel=$('#detail-panel');overlay.classList.remove('hidden');document.body.style.overflow='hidden';const isB=kind==='batting';const keys=isB?[['PA','打席'],['H','安打'],['HR','全壘打'],['avg','AVG'],['obp','OBP'],['ops','OPS']]:[['G','出賽'],['IP','投球局數'],['SO','奪三振'],['era','ERA'],['whip','WHIP'],['SV','救援成功']];panel.innerHTML=`<div class="detail-head"><div><div class="eyebrow">PLAYER PROFILE · ${state.year}</div><h2>${escapeHtml(r.name)}</h2><div class="detail-meta">${escapeHtml(r.team)} · 球員 ID ${escapeHtml(id)}${/^\d{10}$/.test(id)?` · <a href="https://www.cpbl.com.tw/team/person?acnt=${id}" target="_blank" rel="noopener" style="color:var(--lime)">CPBL 官網球員卡 ↗</a>`:''}</div></div><button class="detail-close" id="close-detail">✕ 關閉</button></div><div class="detail-stats">${keys.map(([k,n])=>`<div class="detail-stat"><small>${n}</small><b>${fieldFormat(r,k)}</b></div>`).join('')}</div><h3 class="detail-subtitle">歷年生涯紀錄</h3><p class="detail-hint">如需完整生涯數據，可以讀取歷年開源紀錄；歷年姓名可能與當年正式登錄名不同。</p><button class="action primary" id="load-career">載入已收錄年度生涯紀錄</button><div id="career-data"></div>`;$('#close-detail').addEventListener('click',closePlayer);$('#load-career').addEventListener('click',async()=>{const btn=$('#load-career');btn.disabled=true;btn.textContent='正在取得球季紀錄…';try{const result=await loadCareer(id,kind,(done,total)=>{btn.textContent=`讀取進度 ${done}/${total} 球季`});const entries=result.rows;const groupedByYear=new Map();for(const s of entries){const k=s.year;if(!groupedByYear.has(k))groupedByYear.set(k,[]);groupedByYear.get(k).push(s)}$('#career-data').innerHTML=groupedByYear.size?`<table class="detail-years"><thead><tr><th>年度</th><th>球隊</th><th>${isB?'PA':'IP'}</th><th>${isB?'H':'SO'}</th><th>${isB?'HR':'ERA'}</th></tr></thead><tbody>${[...groupedByYear].map(([y,ss])=>ss.map(s=>`<tr><td>${y}</td><td>${escapeHtml(s.team)}</td><td>${isB?fmt(s.PA):s.IP}</td><td>${isB?fmt(s.H):fmt(s.SO)}</td><td>${isB?fmt(s.HR):fmt(s.era,2)}</td></tr>`).join('')).join('')}</tbody></table>`:'<p class="detail-hint">找不到其他球季紀錄。</p>';btn.textContent=result.failedYears.length?'部分年份取得失敗':'生涯紀錄已載入';if(result.failedYears.length){$('#career-data').insertAdjacentHTML('afterbegin',`<p class="detail-hint">尚有 ${result.failedYears.length} 個年份讀取失敗，本表不保證完整。未成功年份：${result.failedYears.join(', ')}</p>`)}}catch(e){btn.textContent='取得失敗，請重試';btn.disabled=false}})}
function closePlayer(){const el=$('#overlay');el.classList.add('hidden');document.body.style.overflow=''}
$('#overlay').addEventListener('click',e=>{if(e.target.id==='overlay')closePlayer()});document.addEventListener('keydown',e=>{if(e.key==='Escape')closePlayer()});
function nav(page){if(!pages[page])page='overview';state.page=page;state.search='';state.sort='';state.pageNo=0;location.hash=page;render()}
async function changeYear(year){state.year=year;state.team='all';state.search='';state.sort='';state.pageNo=0;state.compare=[null,null];state.standingPart='all';$('#content').innerHTML='<div class="loading">正在讀取 '+year+' 年球季…</div>';$('#source-status').textContent=`${year} 年資料載入中`;try{state.season=await loadSeason(year);$('#source-status').textContent=`${year} 年資料載入成功 · ${state.season.method==='snapshot'?'經驗證快照':'歷史開放資料'}`;$('#source-caption').textContent=`打者 ${state.season.batting.length} 筆、投手 ${state.season.pitching.length} 筆、球隊 ${state.season.teams.length} 支 · ${state.season.importedAt?'資料擷取 '+state.season.importedAt.slice(0,10):'歷史紀錄'} · 非即時`;render()}catch(e){state.season=null;$('#source-status').textContent='讀取失敗（舊資料不會被改寫）';$('#source-caption').textContent='請檢查來源是否可連線，或稍後重試';$('#content').innerHTML=`<div class="error">${escapeHtml(year+' 球季無法載入：'+e.message)}<div style="margin-top:14px"><button class="action" id="retry">重新讀取</button></div></div>`;$('#retry').addEventListener('click',()=>changeYear(year))}}
async function boot(){state.source=await manifest();state.years=state.source.years;const yearSelect=$('#year');yearSelect.innerHTML=state.years.map(y=>`<option value="${y}">${y} 球季</option>`).join('');const hash=location.hash.replace('#','');state.page=pages[hash]?hash:'overview';yearSelect.addEventListener('change',e=>changeYear(Number(e.target.value)));window.addEventListener('hashchange',()=>{const hash=location.hash.replace('#','');if(hash!==state.page&&pages[hash])nav(hash)});await changeYear(Number(yearSelect.value));}boot();
