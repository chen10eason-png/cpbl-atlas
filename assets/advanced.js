/** Derived metrics from verified season counting stats. All missing denominators yield null. */
export const ratio=(a,b)=>Number.isFinite(a)&&Number.isFinite(b)&&b>0?a/b:null;
export const requiredPA=games=>Number.isFinite(games)&&games>0?Math.floor(games*3.1+0.5+1e-9):null;
export const requiredOuts=games=>Number.isFinite(games)&&games>0?games*3:null;
export const RATE_BAT=new Set(['avg','obp','slg','ops','iso','babip','kpct','bbpct','sec','gp','rc','sbpct','bbk','xbhpct','gofo']);
export const RATE_PIT=new Set(['era','whip','k9','bb9','h9','hr9','kbb','kpct','bbpct','kbbpct','pPerInning','pPerBatter','fip','gofo']);
export function enrichBatter(o){
  const x={...o};
  x.avg=ratio(x.H,x.AB);x.obp=ratio(x.H+x.BB+x.HBP,x.AB+x.BB+x.HBP+x.SF);
  x.slg=ratio(x.TB,x.AB);x.ops=x.obp==null||x.slg==null?null:x.obp+x.slg;
  x.iso=x.slg==null||x.avg==null?null:x.slg-x.avg;
  x.babip=ratio(x.H-x.HR,x.AB-x.SO-x.HR+x.SF);
  x.kpct=ratio(x.SO*100,x.PA);x.bbpct=ratio(x.BB*100,x.PA);
  x.xbh=x['2B']+x['3B']+x.HR;
  x.xbhpct=ratio(x.xbh*100,x.H);
  x.gp=x.obp==null||x.slg==null?null:(1.8*x.obp+x.slg)/4;
  x.sec=ratio(x.TB-x.H+x.BB+x.SB-x.CS,x.AB);
  x.rc=ratio((x.H+x.BB)*x.TB,x.AB+x.BB); // basic Runs Created, NOT linear weights
  x.bbk=ratio(x.BB,x.SO);
  x.sbpct=ratio(x.SB*100,x.SB+x.CS);
  x.gofo=ratio(x.GO,x.FO);
  return x;
}
export function enrichPitcher(o,fipConstant=null){
  const x={...o};const outs=x.outs;
  x.era=ratio(x.ER*27,outs);x.whip=ratio((x.H+x.BB)*3,outs);
  x.k9=ratio(x.SO*27,outs);x.bb9=ratio(x.BB*27,outs);
  x.h9=ratio(x.H*27,outs);x.hr9=ratio(x.HR*27,outs);
  x.kbb=ratio(x.SO,x.BB);x.kpct=ratio(x.SO*100,x.BF);
  x.bbpct=ratio(x.BB*100,x.BF);
  x.kbbpct=x.kpct==null||x.bbpct==null?null:x.kpct-x.bbpct;
  x.pPerInning=ratio(x.NP*3,outs);x.pPerBatter=ratio(x.NP,x.BF);
  x.gofo=ratio(x.GO,x.FO);
  x.fip=Number.isFinite(fipConstant)&&Number.isFinite(x.IBB)&&Number.isFinite(x.HBP)&&outs>0
    ? ratio((13*x.HR+3*(x.BB-x.IBB+x.HBP)-2*x.SO)*3,outs)+fipConstant:null;
  return x;
}
export function leagueFipConstant(pitching){
  if (!pitching.length || pitching.some(x=>!Number.isFinite(x.IBB)||!Number.isFinite(x.HBP)))return null;
  const outs=pitching.reduce((s,r)=>s+(r.outs||0),0);
  if(outs<=0)return null;
  const er=pitching.reduce((s,r)=>s+r.ER,0);
  const core=pitching.reduce((s,r)=>s+13*r.HR+3*(r.BB-r.IBB+r.HBP)-2*r.SO,0);
  return er*27/outs-core*3/outs;
}
export function applySeasonMetrics(rows,kind,allPitching=[]){
  const c=kind==='pitching'?leagueFipConstant(allPitching.length?allPitching:rows):null;
  return rows.map(r=>kind==='batting'?enrichBatter(r):enrichPitcher(r,c));
}
/** Use player total PA/IP across clubs and most conservative team-game count on transfers. */
export function withQualification(rows,teams,kind){
  const byTeam=new Map(teams.map(t=>[t.id,t.w+t.l+t.t]));
  return rows.map(r=>{
    const ids=r._teamIds?[...r._teamIds]:[r.teamId];
    const games=ids.map(id=>byTeam.get(id)).filter(Number.isFinite);
    const target=games.length?Math.max(...games):null;
    const threshold=kind==='batting'?requiredPA(target):requiredOuts(target);
    const tally=kind==='batting'?r.PA:r.outs;
    return {...r,threshold,qualified:threshold!=null&&tally>=threshold};
  });
}
