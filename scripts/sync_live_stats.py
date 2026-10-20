"""CPBL Atlas: live and past game snapshots from official advanced stats API.

The legacy www.cpbl.com.tw endpoint returns HTTP 404/anti-bot to GitHub Actions.
Source: https://stats.cpbl.com.tw/api/proxy/v1/games/schedule and /games/{id}.
Never represent a failed fetch as an empty game day. Only publish validated responses.
"""
from __future__ import annotations

import argparse
import datetime as dt
import json
import os
import re
import sys
from collections import defaultdict
from pathlib import Path
from urllib.parse import urlencode
from zoneinfo import ZoneInfo

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = ROOT / 'data' / 'live'
SOURCE = 'https://stats.cpbl.com.tw/api/proxy/v1'
KINDS = ('A', 'C', 'E', 'D', 'F')
TAIPEI = ZoneInfo('Asia/Taipei')
GAME_ID = re.compile(r'^(20\d\d)-([ACEDF])-(\d{1,5})$')
DAY_RE = re.compile(r'^20\d\d-\d\d-\d\d$')
MAX_RESPONSE_BYTES = 5_000_000
STATUS = {
    'SCHEDULED': 1, 'NOT_STARTED': 1,
    'START': 4, 'LIVE': 4, 'IN_PROGRESS': 4,
    'FINISHED': 3, 'FINAL': 3, 'END': 3,
    'POSTPONED': 6, 'RESERVED': 7,
    'CANCELLED': 5, 'CANCELED': 5,
}


def today():
    return dt.datetime.now(TAIPEI).date()


def number(value):
    if value is None or value == '' or isinstance(value, bool):
        return None
    try:
        n = int(value)
        return n if n >= 0 and n <= 100000 else None
    except (ValueError, TypeError):
        return None


def name(value):
    return re.sub(r'\s+', ' ', str(value or '')).strip()[:85]


def identity(raw):
    if not isinstance(raw, dict):
        raise ValueError('game record is not an object')
    ident = str(raw.get('GameId') or '').strip()
    match = GAME_ID.fullmatch(ident)
    if not match:
        year, kind, no = raw.get('Year'), raw.get('KindCode'), raw.get('GameSno')
        ident = f'{year}-{kind}-{no}'
        match = GAME_ID.fullmatch(ident)
    if not match:
        raise ValueError('CPBL game has no valid full identity')
    return ident, int(match.group(1)), match.group(2), int(match.group(3))


def day_of(raw):
    for field in ('PreExeDate', 'GameDate', 'GameDateTimeS'):
        value = str(raw.get(field) or '')[:10].replace('/', '-')
        if DAY_RE.fullmatch(value):
            try:
                return dt.date.fromisoformat(value)
            except ValueError:
                pass
    return None


def team_obj(raw, key):
    value = raw.get(key)
    return value if isinstance(value, dict) else {}


def team_name(raw, side):
    team = team_obj(raw, side)
    identity = team.get('Team') if isinstance(team.get('Team'), dict) else {}
    return name(identity.get('Name') or team.get('Name') or raw.get(side + 'TeamName'))


def status_code(value):
    if isinstance(value, str):
        return STATUS.get(value.upper(), number(value))
    return number(value)


def source_url(year, kind, no):
    params = urlencode({'gameSno': no, 'kindCode': kind, 'year': year})
    return 'https://www.cpbl.com.tw/box/live?' + params


def game_skeleton(raw, expected_day):
    ident, year, kind, no = identity(raw)
    actual = day_of(raw)
    if actual != expected_day:
        raise ValueError(f'{ident} date mismatch: {actual} vs {expected_day}')
    away, home = team_name(raw, 'Visiting'), team_name(raw, 'Home')
    if not away or not home:
        raise ValueError(f'{ident} missing verified team names')
    visiting, hosting = team_obj(raw, 'Visiting'), team_obj(raw, 'Home')
    start = str(raw.get('PreExeDate') or '')[:35]
    field = raw.get('Field') or raw.get('FieldAbbe') or raw.get('FieldName')
    if isinstance(field, dict):
        field = field.get('Name') or field.get('Abbr')
    return {
        'id': ident, 'year': year, 'kindCode': kind, 'gameSno': no,
        'away': away, 'home': home,
        'awayScore': number(visiting.get('Score')),
        'homeScore': number(hosting.get('Score')),
        'statusCode': status_code(raw.get('GameStatus')),
        'rawStatus': name(raw.get('GameStatus')),
        'startAt': start,
        'stadium': name(field),
        'officialUrl': source_url(year, kind, no),
        'statsUrl': f'https://stats.cpbl.com.tw/schedule/{ident}',
        'innings': [], 'events': [], 'awayHits': number(visiting.get('HittingCnt')),
        'homeHits': number(hosting.get('HittingCnt')),
        'awayErrors': number(visiting.get('ErrorCnt')), 'homeErrors': number(hosting.get('ErrorCnt')),
        'detailAvailable': False,
    }


def parse_schedule(payload, day, kind):
    if not isinstance(payload, dict) or payload.get('success') is False:
        raise ValueError(f'{kind} schedule API returned an error')
    data = payload.get('Data') or payload.get('data')
    if not isinstance(data, dict) or not isinstance(data.get('Games'), list):
        raise ValueError(f'{kind} schedule schema has no Games list')
    games = []
    for row in data['Games']:
        if not isinstance(row, dict):
            raise ValueError(f'{kind} schedule has an invalid row')
        game_day = day_of(row)
        if game_day == day:
            ident, y, k, _ = identity(row)
            if y != day.year or k != kind:
                raise ValueError(f'{ident} wrong year or kind for {day}')
            games.append(game_skeleton(row, day))
    return games


def attach_detail(payload, game):
    if not isinstance(payload, dict) or payload.get('success') is False:
        raise ValueError('game API returned an error')
    data = payload.get('Data') or payload.get('data')
    if not isinstance(data, dict) or not isinstance(data.get('Game'), dict):
        raise ValueError('game API missing Data.Game')
    raw = data['Game']
    ident, _, _, _ = identity(raw)
    if ident != game['id']:
        raise ValueError('game detail identity mismatch')
    enriched = dict(game)
    away, home = team_obj(raw, 'Visiting'), team_obj(raw, 'Home')
    for key, raw_team in (('away', away), ('home', home)):
        if team_name(raw, 'Visiting' if key == 'away' else 'Home') and team_name(raw, 'Visiting' if key == 'away' else 'Home') != game[key]:
            # Schedule may have abbreviation; do not assume a different team is identical.
            if name(raw_team.get('Team', {}).get('Name') if isinstance(raw_team.get('Team'), dict) else '') != game[key]:
                # A verified identity (GameId) makes the detail the authoritative display name.
                enriched[key] = team_name(raw, 'Visiting' if key == 'away' else 'Home')
        for suffix, field in [('Score', 'Score'), ('Hits', 'HittingCnt'), ('Errors', 'ErrorCnt')]:
            n = number(raw_team.get(field))
            if n is not None:
                enriched[key + suffix] = n
    enriched['statusCode'] = status_code(raw.get('GameStatus')) or game['statusCode']
    enriched['rawStatus'] = name(raw.get('GameStatus') or game.get('rawStatus'))
    if raw.get('FieldAbbe'):
        enriched['stadium'] = name(raw.get('FieldAbbe'))
    by_inning = {}
    for side, team in [('away', away), ('home', home)]:
        entries = team.get('InningScore')
        if isinstance(entries, list):
            for row in entries:
                if not isinstance(row, dict):
                    continue
                seq = number(row.get('Seq'))
                if seq is not None and 1 <= seq <= 25:
                    by_inning.setdefault(seq, {'inning': seq, 'away': None, 'home': None})[side] = number(row.get('Score'))
    enriched['innings'] = [by_inning[n] for n in sorted(by_inning)]
    logs = raw.get('LiveLog')
    if isinstance(logs, list):
        events = []
        for row in logs[-160:]:
            if not isinstance(row, dict):
                continue
            content = re.sub(r'\s+', ' ', str(row.get('Content') or '')).strip()[:500]
            action = name(row.get('BattingActionName') or row.get('ActionName'))
            if not content and not action:
                continue
            def occupied(base):
                return str(row.get(base) or '').strip() not in ('', '0', 'None', 'null')
            events.append({
                'inning': number(row.get('InningSeq')), 'side': number(row.get('VisitingHomeType')),
                'hitter': name(row.get('HitterName')), 'pitcher': name(row.get('PitcherName')),
                'content': content, 'action': action,
                'outs': number(row.get('OutCnt')), 'balls': number(row.get('BallCnt')),
                'strikes': number(row.get('StrikeCnt')),
                'first': occupied('FirstBase'), 'second': occupied('SecondBase'), 'third': occupied('ThirdBase'),
                'scored': str(row.get('IsScoreCnt') or '').lower() in ('1', 'true'),
                'awayScore': number(row.get('VisitingScore')), 'homeScore': number(row.get('HomeScore')),
            })
        enriched['events'] = events[-80:]
    enriched['detailAvailable'] = bool(enriched['innings'] or enriched['events'])
    return enriched


def validated_json(session, url, *, params=None):
    response = session.get(url, params=params, timeout=(8, 20), stream=True,
                           headers={'Accept': 'application/json', 'Referer': 'https://stats.cpbl.com.tw/'})
    try:
        response.raise_for_status()
        length = response.headers.get('Content-Length')
        if length and int(length) > MAX_RESPONSE_BYTES:
            raise ValueError('API response too large')
        chunks = bytearray()
        for part in response.iter_content(32768):
            chunks.extend(part)
            if len(chunks) > MAX_RESPONSE_BYTES:
                raise ValueError('API response too large')
        result = json.loads(bytes(chunks).decode('utf-8-sig'))
        if not isinstance(result, dict):
            raise ValueError('API response was not an object')
        return result
    finally:
        response.close()


def collect_month(session, year, month, kinds=KINDS):
    all_rows, failures = {}, {}
    any_success = False
    for kind in kinds:
        try:
            payload = validated_json(session, SOURCE + '/games/schedule',
                                     params={'kindCode': kind, 'year': year, 'month': month})
            data = payload.get('Data') or payload.get('data')
            if not isinstance(data, dict) or not isinstance(data.get('Games'), list) or payload.get('success') is False:
                raise ValueError('no valid Data.Games')
            any_success = True
            all_rows[kind] = data['Games']
        except (ValueError, TypeError, requests.RequestException) as exc:
            failures[kind] = f'{type(exc).__name__}: {exc}'[:220]
            print(f'WARN: schedule {year}-{month:02d} kind={kind}: {failures[kind]}', file=sys.stderr)
    # A/C/E are all mandatory for first-team results; D/F optional but flagged.
    if not all(k in all_rows for k in ('A', 'C', 'E')):
        raise RuntimeError(f'CPBL mandatory A/C/E schedule unavailable for {year}-{month:02d}: {failures}')
    if not any_success:
        raise RuntimeError('CPBL schedule service unavailable')
    return all_rows, failures


def create_snapshot(session, day, month_rows, category_failures=None):
    games = []
    for kind, rows in month_rows.items():
        for raw in rows:
            if not isinstance(raw, dict):
                raise ValueError(f'invalid {kind} raw schedule row')
            if day_of(raw) != day:
                continue
            # Parser performs both identity and date checks.
            games.append(parse_schedule({'Data': {'Games': [raw]}}, day, kind)[0])
    seen = set()
    cleaned = []
    for game in games:
        if game['id'] in seen:
            # Some rescheduled games have multiple rows; the most recent day record wins.
            continue
        seen.add(game['id'])
        cleaned.append(game)
    if len(cleaned) > 32:
        raise ValueError('more than 32 games in one day')
    details_failed = 0
    for i, game in enumerate(cleaned):
        try:
            payload = validated_json(session, SOURCE + '/games/' + game['id'])
            cleaned[i] = attach_detail(payload, game)
        except (ValueError, TypeError, requests.RequestException) as exc:
            details_failed += 1
            print(f'WARN: {game["id"]} details: {type(exc).__name__}: {exc}', file=sys.stderr)
    return {
        'schemaVersion': 1, 'date': day.isoformat(),
        'updatedAt': dt.datetime.now(dt.timezone.utc).isoformat(timespec='seconds'),
        'source': 'CPBL official advanced stats public API (unofficial integration)',
        'intervalHintMinutes': 5, 'detailFailures': details_failed,
        'missingKinds': sorted(category_failures or {}),
        'games': sorted(cleaned, key=lambda x: (x.get('startAt') or '', x['id'])),
    }


def validate(blob, day):
    if blob.get('schemaVersion') != 1 or blob.get('date') != day.isoformat() or not isinstance(blob.get('games'), list):
        raise ValueError('invalid snapshot metadata')
    ids = set()
    for g in blob['games']:
        if g['id'] in ids or not GAME_ID.fullmatch(g.get('id', '')):
            raise ValueError('duplicate/malformed game identity')
        if not g.get('away') or not g.get('home') or not g.get('officialUrl', '').startswith('https://www.cpbl.com.tw/box/live?'):
            raise ValueError('missing real team names or official link')
        ids.add(g['id'])
    return blob


def atomic_write(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_name(path.name + '.tmp')
    temp.write_text(json.dumps(data, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    os.replace(temp, path)


def publish_many(snapshots, directory=DATA_DIR):
    # Validate all in memory first, avoiding partial updates for an invalid snapshot.
    snapshots = {day: validate(blob, day) for day, blob in snapshots.items()}
    directory.mkdir(parents=True, exist_ok=True)
    for day, blob in sorted(snapshots.items()):
        atomic_write(directory / f'{day}.json', blob)
    # Index is derived from all previously validated files; backfills do not erase history.
    catalog = {}
    for path in directory.glob('20??-??-??.json'):
        try:
            blob = json.loads(path.read_text(encoding='utf-8'))
            date = dt.date.fromisoformat(blob['date'])
            validate(blob, date)
        except (KeyError, ValueError, TypeError, json.JSONDecodeError):
            continue
        catalog[blob['date']] = {'date': blob['date'], 'games': len(blob['games']), 'updatedAt': blob['updatedAt']}
    dates = sorted(catalog, reverse=True)
    atomic_write(directory / 'index.json', {'schemaVersion': 1, 'dates': [catalog[x] for x in dates[:365]],
                                             'generatedAt': dt.datetime.now(dt.timezone.utc).isoformat(timespec='seconds')})
    # Latest means most recent calendar day, NOT the last backfilled game.
    if dates:
        recent_day = dates[0]
        snapshot = json.loads((directory / f'{recent_day}.json').read_text(encoding='utf-8'))
        atomic_write(directory / 'latest.json', snapshot)
    return dates


def make_session():
    session = requests.Session()
    retry = Retry(total=2, backoff_factor=0.8, status_forcelist=[429, 500, 502, 503, 504],
                  allowed_methods=['GET'])
    session.mount('https://', HTTPAdapter(max_retries=retry))
    session.headers.update({'User-Agent': 'CPBL-Atlas/0.4.1 (public scores; GitHub Pages)',
                            'Accept-Language': 'zh-TW,zh;q=0.9,en;q=0.7'})
    return session


def main(argv=None):
    parser = argparse.ArgumentParser(description='CPBL official advanced stats scoreboard snapshots')
    parser.add_argument('--date', help='Taiwan calendar day YYYY-MM-DD; default today')
    parser.add_argument('--backfill-days', type=int, default=1, help='Number of calendar days ending on --date (max 31)')
    args = parser.parse_args(argv)
    if not 1 <= args.backfill_days <= 31:
        parser.error('backfill-days must be between 1 and 31')
    end = dt.date.fromisoformat(args.date) if args.date else today()
    if end > today() or end.year < 2020:
        parser.error('date must not be in the future or before 2020')
    days = [end - dt.timedelta(days=i) for i in range(args.backfill_days)]
    groups = defaultdict(list)
    for day in days:
        groups[day.year, day.month].append(day)
    snapshots = {}
    with make_session() as session:
        for (year, month), dlist in groups.items():
            rows, failures = collect_month(session, year, month)
            for day in sorted(dlist):
                blob = create_snapshot(session, day, rows, failures)
                snapshots[day] = blob
                print(f'READY {day} games={len(blob["games"])} details_missing={blob["detailFailures"]} source=stats.cpbl.com.tw')
    dates = publish_many(snapshots)
    print(f'PASS snapshots={len(snapshots)} retained_dates={len(dates)} latest={dates[0] if dates else "none"}')


if __name__ == '__main__':
    main()
