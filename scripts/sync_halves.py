#!/usr/bin/env python3
"""Fetch only verified official half-season standings; retain old snapshots on failure.

Sources: CPBL official /team/teamrecord pages. For 1998–99 CPBL used a single
season, so the UI disables half-season views. Does not synthesize half-seasons.
"""
import argparse
import datetime as dt
import json
import re
import sys
import time
from io import StringIO
from urllib.parse import urlencode
from pathlib import Path

import pandas as pd
import requests

from sync import DATA, atomic_json

BASE='https://www.cpbl.com.tw/team/teamrecord'
# Candidate official historical/current team links. The response is *only* used
# when W/L/T totals exactly reconcile to a separately sourced annual standing.
EXPLICIT_TEAMNO={'ACC':'ACC011','ABB':'ABB011','ADD':'ADD011','AJL':'AJL011','AEO':'AEO022'}
SINGLE_SEASON_YEARS={1998,1999}

def candidate_urls(team_id):
    ids=[]
    if team_id in EXPLICIT_TEAMNO:ids.append(EXPLICIT_TEAMNO[team_id])
    ids.extend([team_id+'011',team_id+'022'])
    urls=[BASE+'?'+urlencode({'teamNo':value}) for value in dict.fromkeys(ids)]
    urls.append(BASE+'?'+urlencode({'ClubNo':team_id.lower()}))
    return urls

def parse_team_history(html):
    """Return {year: {first/second: WLT, 'all': WLT}}, no estimated values."""
    try:tables=pd.read_html(StringIO(html),flavor='lxml')
    except (ValueError,ImportError) as exc:raise ValueError('Official team history table not found') from exc
    target=None
    for table in tables:
        columns=[str(c) if not isinstance(c,tuple) else '/'.join(map(str,c)) for c in table.columns]
        if any('年度' in c for c in columns) and all(any(k in c for c in columns) for k in ('勝','敗','和')):
            target=table;break
    if target is None:raise ValueError('Cannot identify official season standings table')
    result={}
    for values in target.itertuples(index=False,name=None):
        fields=list(values)
        label=str(fields[0]).strip().replace(' ','')
        m=re.fullmatch(r'(19\d\d|20\d\d)(?:[(（](上|下)[)）])?',label)
        if not m:continue
        year=int(m.group(1));part={'上':'first','下':'second',None:'all'}[m.group(2)]
        def val(index):
            v=str(fields[index]).strip().replace(',','')
            if not re.fullmatch(r'\d+(?:\.0+)?',v):raise ValueError(f'Invalid count for {label}: {v}')
            return int(float(v))
        # The official table's first five columns are 年度 出賽數 勝 敗 和
        if len(fields)<5:raise ValueError('Official history table has too few fields')
        g,w,l,t=map(val,(1,2,3,4))
        if w+l+t!=g:raise ValueError(f'Official history WLT total mismatch: {label}')
        r={'w':w,'l':l,'t':t}
        if len(fields)>=12:
            hw,hl,ht,aw,al,at=map(val,(6,7,8,9,10,11))
            if hw+aw!=w or hl+al!=l or ht+at!=t:
                raise ValueError(f'Official home/away WLT mismatch: {label}')
            r.update({'homeW':hw,'homeL':hl,'homeT':ht,'awayW':aw,'awayL':al,'awayT':at})
        if part in result.setdefault(year,{}):raise ValueError('Duplicate official season rows')
        result[year][part]=r
    if not result:raise ValueError('Official team history has no recognized years')
    return result

def reconcile_year(year,annual,history):
    h=history.get(year,{})
    if year in SINGLE_SEASON_YEARS:
        raise ValueError(f'{year} is a single-season year')
    if set(h).isdisjoint({'first','second'}):raise ValueError(f'No half season for year {year}')
    if 'first' not in h or 'second' not in h:raise ValueError(f'One half missing for year {year}')
    if any(h['first'][x]+h['second'][x]!=annual[x] for x in ('w','l','t')):
        raise ValueError(f'Half WLT does not reconcile to official annual WLT in {year}')
    return {k:h[k] for k in ('first','second')}

def fetch_team_year(session,team,year,allow_unreconciled=False):
    """Read one team history over many years from a cached official page."""
    if not hasattr(session,'_atlas_histories'):session._atlas_histories={}
    histories=session._atlas_histories
    errors=[]
    for url in candidate_urls(team['id']):
        try:
            if url not in histories:
                time.sleep(0.65)
                response=session.get(url,timeout=20,allow_redirects=False)
                if response.status_code!=200 or len(response.content)>5_000_000:
                    raise RuntimeError(f'HTTP {response.status_code} or oversized page')
                response.encoding='utf-8'
                histories[url]=parse_team_history(response.text)
            if allow_unreconciled:
                parts=histories[url].get(year,{})
                if 'first' not in parts or 'second' not in parts:raise ValueError('Official source has incomplete half-year records')
                return {k:parts[k] for k in ('first','second')}
            return reconcile_year(year,team,histories[url])
        except (RuntimeError,ValueError,requests.RequestException) as exc:
            errors.append(str(exc))
    raise RuntimeError(f"{team['name']} {year}: no matching official club page and reconciled record ({'; '.join(errors[:3])})")

def build_year(year,session):
    path=DATA/f'{year}.json'
    if not path.exists():raise RuntimeError('Verified annual snapshot missing')
    annual=json.loads(path.read_text('utf-8'))
    teams=annual.get('teams',[])
    if not teams:raise RuntimeError('Annual team list is empty')
    if year in SINGLE_SEASON_YEARS:
        return {'year':year,'source':'CPBL official season format','seasonStructure':'single','halves':{'first':[],'second':[]}}
    halves={'first':[],'second':[]}
    for team in teams:
        part=fetch_team_year(session,team,year)
        for k in ('first','second'):halves[k].append({**{key:team[key] for key in ('year','id','name','short') if key in team},**part[k]})
    if any(len(v)!=len(teams) for v in halves.values()):raise RuntimeError('Incomplete split-season team coverage')
    return {'year':year,'source':'https://www.cpbl.com.tw/team/teamrecord','seasonStructure':'split',
            'importedAt':dt.datetime.now(dt.timezone.utc).isoformat(timespec='seconds'),'halves':halves}

def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--year',type=int)
    parser.add_argument('--all',action='store_true')
    parser.add_argument('--refresh',action='store_true')
    options=parser.parse_args()
    years=range(1990,2027) if options.all else [options.year] if options.year else []
    if not years:parser.error('choose --year YYYY or --all')
    s=requests.Session();s.headers.update({'User-Agent':'CPBL-Atlas/0.2 (independent historical baseball archive)'})
    failed=[]
    for year in years:
        target=DATA/'halves'/f'{year}.json'
        if target.exists() and not options.refresh:continue
        try:
            result=build_year(year,s)
            atomic_json(target,result)
            print('PASS',year,result['seasonStructure'],flush=True)
        except Exception as exc:
            print('NO VALID HALF SNAPSHOT',year,str(exc),file=sys.stderr,flush=True)
            failed.append(year)
    if failed:print('Half-year source incomplete; existing annual and partial validated history remain unchanged:',failed,file=sys.stderr)
    return failed

if __name__=='__main__':main()
