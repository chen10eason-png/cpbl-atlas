import assert from 'node:assert/strict';
import {requiredPA,requiredOuts,enrichBatter,enrichPitcher,leagueFipConstant,withQualification,RATE_BAT,RATE_PIT} from '../assets/advanced.js';
for(const [g,pa] of [[1,3],[10,31],[57,177],[59,183],[60,186],[90,279],[100,310],[120,372]])assert.equal(requiredPA(g),pa);
assert.equal(requiredOuts(120),360);assert.equal(requiredPA(null),null);
assert.equal(requiredPA(0),null);
const teams=[{id:'ACN',w:36,l:24,t:0},{id:'ADD',w:70,l:50,t:0}];
let rows=withQualification([
  {id:'a',teamId:'ADD',PA:371}, {id:'b',teamId:'ADD',PA:372},
  {id:'c',teamId:'ACN',PA:186},
  {id:'d',teamId:'ACN',PA:190,_teamIds:new Set(['ACN','ADD'])},
],teams,'batting');
assert.deepEqual(rows.map(x=>x.qualified),[false,true,true,false]);
assert.deepEqual(rows.map(x=>x.threshold),[372,372,186,372]);
const x=enrichBatter({PA:100,AB:90,H:30,'2B':8,'3B':1,HR:3,TB:49,BB:7,HBP:1,SF:2,SO:12,SB:4,CS:1,GO:18,FO:22});
assert.equal(x.xbh,12);assert.equal(x.xbhpct,40);
assert.ok(Math.abs(x.sec-(49-30+7+4-1)/90)<1e-9);
assert.equal(x.sbpct,80);assert.ok(Math.abs(x.kpct-12)<1e-9);
assert.equal(x.rc,(30+7)*49/(90+7));
const pitcher={outs:360,ER:40,H:100,HR:12,BB:30,IBB:2,HBP:5,SO:95,BF:500,NP:2000,GO:90,FO:80};
const c=leagueFipConstant([pitcher]);const p=enrichPitcher(pitcher,c);
assert.ok(Math.abs(p.era-3)<1e-9);assert.ok(Math.abs(p.fip-p.era)<1e-9);
assert.equal(p.kbbpct,((95-30)/500)*100);
assert.equal(enrichPitcher({...pitcher,IBB:null},c).fip,null);
assert.equal(leagueFipConstant([{...pitcher,IBB:null}]),null);
assert.ok(RATE_BAT.has('ops'));assert.ok(!RATE_BAT.has('HR'));
assert.ok(RATE_PIT.has('era'));assert.ok(!RATE_PIT.has('SO'));
console.log('Advanced metrics, qualifications, transferred players PASS');
