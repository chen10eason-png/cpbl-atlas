#!/usr/bin/env python3
"""Fail-closed official CPBL 2025+ importer.

Requires: requests, pandas, lxml, beautifulsoup4. Queries only CPBL first-party
pages, once per sync at modest rate, with token and pagination. Source may change.
Never substitutes demo data when official source is unavailable.
"""
import argparse
from datetime import datetime, timezone
import hashlib
from io import StringIO
import json
import re
import sys
import time
from pathlib import Path
from urllib.parse import urlparse

from sync import DATA, atomic_json, innings_outs, ratio
from sync_halves import fetch_team_year

try:
    import pandas as pd
    import requests
    from bs4 import BeautifulSoup
except ImportError as exc:
    raise SystemExit('Install optional requirements: pip install -r requirements-sync.txt') from exc

BASE='https://www.cpbl.com.tw'
TEAM_IDS={'中信兄弟':'ACN','統一7-ELEVEn獅':'ADD','樂天桃猿':'AJL','富邦悍將':'AEO','味全龍':'AAA','台鋼雄鷹':'AKP'}
MAX_BYTES=6_000_000

def get_response(session,method,url,**kwargs):
    parsed=urlparse(url)
    if parsed.scheme!='https' or parsed.hostname not in ('cpbl.com.tw','www.cpbl.com.tw'):
        raise ValueError('CPBL official HTTPS host required')
    time.sleep(0.6)
    r=session.request(method,url,timeout=25,allow_redirects=False,**kwargs)
    r.raise_for_status()
    if not 200<=r.status_code<300 or len(r.content)>MAX_BYTES:
        raise RuntimeError(f'Invalid CPBL response: {r.status_code}/{len(r.content)} bytes')
    if not r.encoding or r.encoding.lower() in ('iso-8859-1','latin-1'):r.encoding='utf-8'
    return r.text

def parse_table(html):
    try:
        tables=pd.read_html(StringIO(html),flavor='lxml')
    except ValueError as exc:
        raise RuntimeError('No official data table') from exc
    if not tables:raise RuntimeError('Missing official table')
    table=tables[0]
    if isinstance(table.columns,pd.MultiIndex):
        table.columns=[next((str(x) for x in reversed(key) if not str(x).startswith('Unnamed')),str(key[0])) for key in table.columns]
    return table

def extract_token(html):
    soup=BeautifulSoup(html,'lxml')
    tok=soup.select_one('input[name="__RequestVerificationToken"]')
    if not tok or not tok.get('value'):raise RuntimeError('Anti-forgery token not found')
    return tok['value']

def parse_ident(label):
    label=re.sub(r'\s+',' ',str(label)).strip()
    label=re.sub(r'^\d+\s+','',label)
    for team in sorted(TEAM_IDS,key=len,reverse=True):
        if label.startswith(team+' '):
            name=label[len(team):].strip().strip('*▲#')
            return team,name
    raise ValueError(f'Unrecognized official team/player: {label[:80]}')

def crawl_recordall(s,year,position):
    url=f'{BASE}/stats/recordall?kindcode=A&position={position}&sortby=01&year={year}'
    page=get_response(s,'GET',url)
    token=extract_token(page)
    pages,results=1,[]
    for idx in range(100):
        payload={'__RequestVerificationToken':token,'ExecAction':'Q','IndexOfPages':str(idx),
                 'Sortby':'01','KindCode':'A','Year':str(year),'Online':'01',
                 'Position':position,'DefenceType':'99','PageSize':'500'}
        html=get_response(s,'POST',f'{BASE}/stats/recordallaction',data=payload,headers={'Referer':url})
        total=re.search(r'total-paging="(\d+)"',html)
        if not total:raise RuntimeError('Missing CPBL page count; refusing truncated import')
        reported=int(total.group(1))
        if reported<1 or reported>100 or idx>0 and reported!=pages:
            raise RuntimeError('Invalid/inconsistent pagination')
        pages=reported
        table=parse_table(html)
        if table.empty:raise RuntimeError('Empty CPBL page')
        results.extend(table.to_dict('records'))
        if idx+1==pages:break
    else:raise RuntimeError('Excessive CPBL pagination')
    return results

def integer(row,key):
    val=str(row.get(key,'0')).strip().replace(',','').replace('（','').replace('）','')
    try:return int(float(val))
    except (ValueError,TypeError):return 0

def label(row):
    return str(next(iter(row.values())))

def player_id(name,team,roster,year):
    # Prefer verified 10-digit official roster ID; otherwise use year-specific
    # synthetic ID to avoid falsely linking an unidentified player across years.
    official=roster.get((name,team))
    if official:return official
    return f'temp{year}'+hashlib.sha256((name+'\0'+team).encode()).hexdigest()[:14]

def roster_ids(session):
    html=get_response(session,'GET',f'{BASE}/player')
    soup=BeautifulSoup(html,'lxml')
    roster={}
    for root in soup.select('.PlayersList'):
        team=''
        for child in root.descendants:
            if getattr(child,'name',None)=='dt':
                team=child.get_text(' ',strip=True)
            if getattr(child,'name',None)=='a' and '/team/person' in child.get('href',''):
                name=child.get_text(' ',strip=True).strip('*#▲')
                idmatch=re.search(r'[?&]acnt=(\d{10})',child['href'])
                if idmatch and team in TEAM_IDS:roster[(name,team)]=idmatch.group(1)
    return roster

def season_batter(row,roster,year):
    team,name=parse_ident(label(row))
    keys={'G':'出賽數','PA':'打席','AB':'打數','RBI':'打點','R':'得分','H':'安打','1B':'一安','2B':'二安','3B':'三安','HR':'全壘打','TB':'壘打數','SO':'被三振','SB':'盜壘','GIDP':'雙殺打','SH':'犧短','SF':'犧飛','BB':'四壞','HBP':'死球','CS':'盜壘刺'}
    o={'id':player_id(name,team,roster,year),'name':name,'team':team,'teamId':TEAM_IDS[team], 'identityVerified':(name,team) in roster}
    o.update({k:integer(row,v) for k,v in keys.items()})
    for k in ('IBB','GO','FO'):o[k]=None
    o['avg']=ratio(o['H'],o['AB']);o['obp']=ratio(o['H']+o['BB']+o['HBP'],o['AB']+o['BB']+o['HBP']+o['SF']);o['slg']=ratio(o['TB'],o['AB'])
    o['ops']=round(o['obp']+o['slg'],5) if o['obp'] is not None and o['slg'] is not None else None
    o['iso']=round(o['slg']-o['avg'],5) if o['slg'] is not None and o['avg'] is not None else None
    o['babip']=ratio(o['H']-o['HR'],o['AB']-o['SO']-o['HR']+o['SF']);o['kpct']=ratio(o['SO']*100,o['PA']);o['bbpct']=ratio(o['BB']*100,o['PA'])
    return o

def season_pitcher(row,roster,year):
    team,name=parse_ident(label(row))
    keys={'G':'出賽數','GS':'先發','GR':'救援','CG':'完投','SHO':'完封','W':'勝場','L':'敗場','SV':'救援成功','HLD':'中繼成功','BF':'打席','NP':'投球數','H':'被安打','HR':'被全壘打','BB':'四壞','HBP':'死球','SO':'奪三振','WP':'暴投','BK':'投手犯規','R':'失分','ER':'自責分'}
    o={'id':player_id(name,team,roster,year),'name':name,'team':team,'teamId':TEAM_IDS[team], 'identityVerified':(name,team) in roster}
    o.update({k:integer(row,v) for k,v in keys.items()})
    for k in ('NBB','IBB','GO','FO'):o[k]=None
    o['IP']=str(row.get('投球局數','0.0')).strip();o['outs']=innings_outs(o['IP'])
    o['era']=ratio(o['ER']*27,o['outs']);o['whip']=ratio((o['BB']+o['H'])*3,o['outs']);o['k9']=ratio(o['SO']*27,o['outs']);o['bb9']=ratio(o['BB']*27,o['outs'])
    return o

def yearly_standings(s,year):
    """Recover complete validated official first and second half standings."""
    team_rows=[];halves={'first':[],'second':[]}
    for name,club in TEAM_IDS.items():
        stub={'year':year,'id':club,'name':name,'short':name[:2], 'w':0,'l':0,'t':0}
        part=fetch_team_year(s,stub,year,allow_unreconciled=True)
        for k in ('first','second'):
            record={**{i:stub[i] for i in ('year','id','name','short')},**part[k]}
            halves[k].append(record)
        team_rows.append({**stub,**{x:part['first'][x]+part['second'][x] for x in ('w','l','t')}})
    return team_rows,halves

def run(year):
    s=requests.Session();s.headers.update({'User-Agent':'Mozilla/5.0 (compatible; independent CPBL stats research)'})
    b=crawl_recordall(s,year,'01');p=crawl_recordall(s,year,'02')
    roster=roster_ids(s)
    batting=[season_batter(r,roster,year) for r in b];pitching=[season_pitcher(r,roster,year) for r in p]
    if len(batting)<100 or len(pitching)<50:raise RuntimeError(f'Incomplete official player coverage: {len(batting)}/{len(pitching)}')
    if any(not x['name'] or not x['team'] for x in batting+pitching):raise RuntimeError('Missing player/team names')
    for kind,rs in [('batting',batting),('pitching',pitching)]:
        ids=[(r['name'],r['team']) for r in rs]
        if len(ids)!=len(set(ids)):raise RuntimeError(f'Duplicate {kind} player/team rows')
    standings,halves=yearly_standings(s,year)
    if len(standings)!=6:raise RuntimeError('Official team coverage incomplete')
    if not (DATA/'manifest.json').exists():raise RuntimeError('Historical manifest missing; refusing partial official write')
    data={'year':year,'source':'cpbl.com.tw','sourceLicense':'Official public numerical statistics',
          'importedAt':datetime.now(timezone.utc).isoformat(timespec='seconds'),
          'batting':batting,'pitching':pitching,'fielding':[], 'teams':standings,'halves':halves,
          'warnings':['Official historical ID not verified for all entries','Fielding per-player data not integrated']}
    atomic_json(DATA/f'{year}.json',data)
    manifest_path=DATA/'manifest.json'
    if not manifest_path.exists():raise RuntimeError('First import historical archive before newer seasons')
    manifest=json.loads(manifest_path.read_text('utf-8'))
    manifest['years']=sorted(set(manifest['years']+[year]));manifest['maxYear']=max(manifest['years'])
    manifest['generatedAt']=data['importedAt']
    manifest['freshness']='Official 2025+ snapshots + 1990–2024 historical archive'
    manifest['currentSeasonSource']='https://www.cpbl.com.tw/stats/recordall'
    atomic_json(manifest_path,manifest)
    print(f'PASS {year}: {len(batting)} batters / {len(pitching)} pitchers / {len(standings)} teams')

if __name__=='__main__':
    parser=argparse.ArgumentParser()
    parser.add_argument('--year',type=int,required=True)
    args=parser.parse_args()
    if args.year not in (2025,2026):raise SystemExit('Only explicitly verified 2025–2026 seasons are allowed')
    run(args.year)
