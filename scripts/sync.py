#!/usr/bin/env python3
"""Build source-attributed CPBL 1990–2024 static snapshots.

Source: https://github.com/ldkrsi/cpbl-opendata (MIT).
Never overwrites an existing snapshot before every download and validation succeeds.
No fake or synthetic seasons are written.
"""
import argparse
import csv
import datetime as dt
import hashlib
import io
import json
import os
from pathlib import Path
import sys
import tempfile
import time
from urllib.error import URLError, HTTPError
from urllib.request import Request, urlopen

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / 'data'
BASE = 'https://raw.githubusercontent.com/ldkrsi/cpbl-opendata/master/'
YEARS = list(range(1990, 2025))  # Upstream currently contains 1990–2024 only.
MIN_ROWS = {'battings': 15, 'pitchings': 12, 'fieldings': 15}
FIELDS = {
    'battings': ['ID','Name','Team ID','G','PA','AB','H','HR','BB','SO'],
    'pitchings': ['ID','Name','Team ID','G','IP','H','ER','BB','SO'],
    'fieldings': ['ID','Name','Team ID','POS','G','PO','A','E'],
}
INT = lambda val: int(float(val or 0))

def get_text(path):
    req = Request(BASE + path, headers={'User-Agent': 'CPBL-Atlas-Data-Sync/0.1 (educational archive; GitHub actions)', 'Accept': 'text/csv'})
    error = None
    for i in range(3):
        try:
            with urlopen(req, timeout=25) as response:
                body = response.read(4_000_000)
                return body.decode('utf-8-sig')
        except (HTTPError, URLError, TimeoutError, UnicodeError) as exc:
            error = exc
            if i < 2:
                time.sleep((i + 1) * 2)
    raise RuntimeError(f'Failed to download {path}: {error}')

def read_csv(raw, expected=(), min_rows=1):
    rows = list(csv.DictReader(io.StringIO(raw)))
    if not rows or len(rows) < min_rows:
        raise ValueError(f'Too few source rows ({len(rows)})')
    for key in expected:
        if key not in rows[0]:
            raise ValueError(f'Missing required column {key}')
    return rows

def number(r, key):
    return INT(r.get(key, 0))

def ratio(a, b):
    return round(a / b, 5) if b else None

def innings_outs(ip):
    raw = str(ip).strip()
    whole, _, frac = raw.partition('.')
    if frac not in ('', '0', '1', '2'):
        raise ValueError(f'Invalid baseball innings value: {ip}')
    return int(whole) * 3 + int(frac or '0')

def batter(r):
    keys = ('G','PA','AB','RBI','R','H','1B','2B','3B','HR','TB','SO','SB','GIDP','SH','SF','BB','IBB','HBP','CS','GO','FO')
    o = {'id': r['ID'], 'name': r['Name'], 'teamId': r['Team ID'], 'team': r.get('Team Name', '')}
    o.update({k: number(r,k) for k in keys})
    o['avg'] = ratio(o['H'],o['AB'])
    o['obp'] = ratio(o['H']+o['BB']+o['HBP'],o['AB']+o['BB']+o['HBP']+o['SF'])
    o['slg'] = ratio(o['TB'],o['AB'])
    o['ops'] = round(o['obp']+o['slg'],5) if o['obp'] is not None and o['slg'] is not None else None
    o['iso'] = round(o['slg']-o['avg'],5) if o['slg'] is not None and o['avg'] is not None else None
    o['babip'] = ratio(o['H']-o['HR'],o['AB']-o['SO']-o['HR']+o['SF'])
    o['kpct'] = ratio(o['SO']*100,o['PA'])
    o['bbpct'] = ratio(o['BB']*100,o['PA'])
    return o

def pitcher(r):
    keys = ('G','GS','GR','CG','SHO','NBB','W','L','SV','HLD','BF','NP','H','HR','BB','IBB','HBP','SO','WP','BK','R','ER','GO','FO')
    o = {'id':r['ID'], 'name':r['Name'], 'teamId':r['Team ID'], 'team':r.get('Team Name', ''), 'IP':str(r.get('IP','0'))}
    o.update({k:number(r,k) for k in keys})
    outs = innings_outs(o['IP'])
    o['outs'] = outs
    o['era'] = ratio(o['ER']*27,outs)
    o['whip'] = ratio((o['BB']+o['H'])*3,outs)
    o['k9'] = ratio(o['SO']*27,outs)
    o['bb9'] = ratio(o['BB']*27,outs)
    return o

def fielder(r):
    keys=('G','TC','PO','A','E','DP','TP','PB','CS','SB')
    o={'id':r['ID'],'name':r['Name'],'teamId':r['Team ID'],'team':r.get('Team Name',''),'pos':r['POS']}
    o.update({k:number(r,k) for k in keys})
    o['fpct']=ratio(o['PO']+o['A'],o['TC'])
    return o

def standing(r):
    return {'year':number(r,'Year'),'id':r['Team ID'],'name':r['Team'], 'short':r.get('Team Nickname',''), 'w':number(r,'Win'),'l':number(r,'Lose'),'t':number(r,'Tie')}

def atomic_json(path,obj):
    path.parent.mkdir(parents=True,exist_ok=True)
    buf = json.dumps(obj, ensure_ascii=False, separators=(',',':'), allow_nan=False) + '\n'
    with tempfile.NamedTemporaryFile(mode='w',encoding='utf-8',dir=path.parent,prefix='._',delete=False) as file:
        file.write(buf)
        temp=Path(file.name)
    temp.replace(path)

def sync_year(year, rows_by_kind, standings):
    return {'year':year, 'source':'ldkrsi/cpbl-opendata', 'sourceLicense':'MIT',
            'batting':[batter(r) for r in rows_by_kind['battings']],
            'pitching':[pitcher(r) for r in rows_by_kind['pitchings']],
            'fielding':[fielder(r) for r in rows_by_kind['fieldings']],
            'teams':[standing(r) for r in standings if number(r,'Year')==year]}

def _valid_snapshot(path):
    try:
        payload=json.loads(path.read_text('utf-8'))
        return payload.get('year')==int(path.stem) and len(payload.get('batting',[]))>=15 and len(payload.get('pitching',[]))>=12 and len(payload.get('teams',[]))>=2
    except (OSError,ValueError,TypeError):
        return False

def build(years, allow_partial=False):
    standings = read_csv(get_text('CPBL/standings.csv'),['Year','Team ID','Win','Lose','Tie'],60)
    results = []
    failed = []
    for year in years:
        try:
            raw = {kind:read_csv(get_text(f'CPBL/{kind}/{year}.csv'),FIELDS[kind],MIN_ROWS[kind]) for kind in FIELDS}
            data = sync_year(year,raw,standings)
            if len(data['batting'])<15 or len(data['pitching'])<12 or not data['teams']:
                raise ValueError('Season incomplete: no team standing or too few players')
            # A duplicate id is legitimate after an intra-season trade; id+team must be unique.
            for kind in ('batting','pitching'):
                pairs=[(r['id'],r['teamId']) for r in data[kind]]
                if len(pairs)!=len(set(pairs)):
                    raise ValueError(f'Duplicate {kind} identity + team')
            atomic_json(DATA/f'{year}.json',data)
            results.append(year)
            print(f'OK {year}: {len(data["batting"])} batters / {len(data["pitching"])} pitchers / {len(data["teams"])} teams', flush=True)
        except Exception as exc:
            failed.append((year,str(exc)))
            print(f'FAILED {year}: {exc}', file=sys.stderr,flush=True)
    if failed and not allow_partial:
        raise RuntimeError(f'{len(failed)} season(s) failed; earlier valid snapshots retained')
    available = sorted(int(f.stem) for f in DATA.glob('*.json') if f.stem.isdecimal() and (int(f.stem) in YEARS or int(f.stem) in (2025,2026)) and _valid_snapshot(f))
    if not available:
        raise RuntimeError('No valid snapshots: refusing to publish an empty manifest')
    manifest = {'generatedAt':dt.datetime.now(dt.timezone.utc).isoformat(timespec='seconds'),
                'years':available,'minYear':min(available),'maxYear':max(available),
                'source':BASE,'sourceLicense':'MIT', 'coverage':'CPBL first-team seasons '+str(min(available))+'–'+str(max(available)),
                'freshness':'historical + verified official seasons' if max(available)>2024 else 'historical-only','incompleteYears':[y for y,_ in failed]}
    atomic_json(DATA/'manifest.json',manifest)
    if failed:
        print('Partial update preserved previous snapshot. Missing:',failed,file=sys.stderr)
    return manifest

if __name__=='__main__':
    p=argparse.ArgumentParser()
    p.add_argument('--full',action='store_true',help='Verify/download all 35 historical seasons (run on first setup).')
    p.add_argument('--allow-partial',action='store_true',help='For local debugging; do not use for production.')
    a=p.parse_args()
    DATA.mkdir(parents=True,exist_ok=True)
    todo=YEARS if a.full else [y for y in YEARS if not (DATA/f'{y}.json').exists()]
    if not todo:
        print('Historical dataset already cached (1990–2024). No 2025+ feed is connected.')
    else:
        build(todo,allow_partial=a.allow_partial)
