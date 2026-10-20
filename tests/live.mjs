import assert from 'node:assert/strict';
import {taipeiDay,ageMinutes,statusText,officialLink,liveMarkup} from '../assets/live.js';
assert.equal(taipeiDay(new Date('2026-10-19T15:30:00Z')),'2026-10-19'); // 23:30 UTC -> next-day Taipei
assert.equal(taipeiDay(new Date('2026-10-19T04:00:00Z')),'2026-10-19');
assert.equal(statusText(4),'比賽進行中');
assert.equal(statusText(3),'比賽結束');
assert.equal(ageMinutes('2026-10-19T00:00:00Z',Date.parse('2026-10-19T00:16:00Z')),16);
assert.equal(officialLink({year:2026,gameSno:4,kindCode:'A'}),'https://www.cpbl.com.tw/box/live?gameSno=4&kindCode=A&year=2026');
assert.equal(officialLink({year:2026,gameSno:4,kindCode:'A&hello=evil'}),'https://www.cpbl.com.tw/schedule');
const obj={schemaVersion:1,date:'2026-10-19',updatedAt:'2026-10-19T11:30:00Z',games:[{id:'2026-A-3',year:2026,gameSno:3,kindCode:'A',away:'<script>alert(1)</script>',home:'主隊',awayScore:0,homeScore:null,statusCode:4,innings:[{inning:1,away:0,home:0}],events:[{inning:1,side:1,hitter:'王測試',content:'安打 <svg onload=alert(1)>',action:'一壘安打',outs:0}]}]};
const html=liveMarkup(obj,'2026-10-19',Date.parse('2026-10-19T11:40:00Z'));
assert.ok(html.includes('0</span>'));
assert.ok(html.includes('&lt;script&gt;'));
assert.ok(!html.includes('<script>'));
assert.ok(!html.includes('<svg'));
assert.ok(html.includes('中職官方即時文字轉播'));
assert.ok(liveMarkup({...obj,games:[]},'2026-10-19').includes('尚無場次'));
assert.throws(()=>liveMarkup({...obj,date:'2026-10-20'},'2026-10-19'));
console.log('CPBL live client checks passed');
import {parseArchiveIndex} from '../assets/live.js';
const hist=parseArchiveIndex({schemaVersion:1, dates:[
 {date:'2026-10-18',games:0},{date:'2026-10-20',games:2},
 {date:'2026-10-19',games:1},{date:'2026-10-20',games:2},
 {date:'2026-10-17',games:-1}
]});
assert.deepEqual(hist.map(v=>v.date),['2026-10-20','2026-10-19','2026-10-18']);
assert.equal(statusText(7),'保留比賽');
assert.throws(()=>parseArchiveIndex({schemaVersion:1,dates:null}));
