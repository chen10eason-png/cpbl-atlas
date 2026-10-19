"""Publish auditable, non-fabricated CPBL live scoreboard snapshots.

This script runs on a scheduler (GitHub Actions); GitHub Pages itself cannot
POST to CPBL's same-origin endpoints. CPBL has not endorsed this integration.
On invalid responses it raises and leaves all existing snapshots untouched.
"""
from __future__ import annotations

import argparse
import datetime as dt
import json
import os
import re
import sys
from pathlib import Path
from zoneinfo import ZoneInfo
from urllib.parse import urlencode

import requests
from bs4 import BeautifulSoup

ROOT = Path(__file__).resolve().parent.parent
LIVE_DIR = ROOT / "data" / "live"
BASE = "https://www.cpbl.com.tw"
TAIPEI = ZoneInfo("Asia/Taipei")
MAX_BYTES = 2_500_000
HEADERS = {"User-Agent": "CPBL-Atlas/0.4 (+https://github.com/chen10eason-png/cpbl-atlas)",
           "Accept-Language": "zh-TW,zh;q=0.9", "Accept": "application/json, text/html, */*"}
KIND_RE = re.compile(r"^[A-Z]$")


def today_taipei() -> dt.date:
    return dt.datetime.now(TAIPEI).date()


def _get_number(value):
    if value is None or str(value).strip() in {"", "-", "None", "null"}:
        return None
    try:
        n = int(value)
        if n < 0 or n > 10000:
            return None
        return n
    except (ValueError, TypeError):
        return None


def _s(value, limit=180) -> str:
    return re.sub(r"\s+", " ", str(value or "")).strip()[:limit]


def _unpack(value):
    if isinstance(value, str):
        return json.loads(value) if value.strip() else []
    return value


def _request(session, verb: str, url: str, **kw):
    response = session.request(verb, url, timeout=(8, 20), allow_redirects=False, stream=True, **kw)
    try:
        if response.status_code != 200:
            raise RuntimeError(f"CPBL HTTP {response.status_code} for {url.split('?')[0]}")
        buf = bytearray()
        for chunk in response.iter_content(32768):
            buf.extend(chunk)
            if len(buf) > MAX_BYTES:
                raise RuntimeError("CPBL response exceeded 2.5 MB limit")
        data = bytes(buf)
        encoding = response.encoding or "utf-8-sig"
        if encoding.lower() in ("iso-8859-1", "latin-1"):
            encoding = "utf-8-sig"  # CPBL pages are UTF-8, even without a charset header.
        return data.decode(encoding, errors="replace")
    finally:
        response.close()


def _token(html: str) -> str:
    soup = BeautifulSoup(html, "html.parser")
    field = soup.select_one('input[name="__RequestVerificationToken"]')
    if field is None or not field.get("value"):
        raise RuntimeError("CPBL page missing verification token (possibly blocked)")
    return str(field["value"])


def parse_listing(response, day: dt.date):
    payload = _unpack(response)
    if not isinstance(payload, dict) or str(payload.get("Success", "")).lower() not in {"true", "1"}:
        raise RuntimeError("CPBL schedule response is not successful")
    keys = [key for key in payload if re.fullmatch(r"Game[A-Z]DetailJson", key)]
    if not keys:
        raise RuntimeError("CPBL daily listing has no Game*DetailJson fields; schema may have changed")
    results = []
    seen = set()
    for field in sorted(keys):
        kind = field[4:5]
        data = _unpack(payload.get(field))
        if data in (None, ""):
            continue
        if not isinstance(data, list):
            raise RuntimeError(f"CPBL {field} is not an array")
        for raw in data:
            if not isinstance(raw, dict):
                raise RuntimeError(f"CPBL {field} contains invalid game")
            number = _get_number(raw.get("GameSno"))
            year = _get_number(raw.get("Year")) or day.year
            game_kind = _s(raw.get("KindCode") or kind)
            away = _s(raw.get("VisitingTeamName") or raw.get("VisitingTeamAbbr"))
            home = _s(raw.get("HomeTeamName") or raw.get("HomeTeamAbbr"))
            if number is None or number < 1 or not KIND_RE.fullmatch(game_kind) or not away or not home or not (1990 <= year <= 2035):
                raise RuntimeError(f"CPBL invalid game identity in {field}")
            key = (year, game_kind, number)
            if key in seen:
                continue
            seen.add(key)
            game_date = _s(raw.get("GameDate") or raw.get("GameDateTimeS") or "")
            # CPBL may provide one day before/after when games run past midnight;
            # only reject a clear mismatch from the queried date.
            found = re.search(r"(\d{4})[-/](\d\d)[-/](\d\d)", game_date)
            if found and tuple(map(int, found.groups())) != (day.year, day.month, day.day):
                raise RuntimeError(f"CPBL returned game outside requested date: {game_date}")
            qs = urlencode({"gameSno": number, "kindCode": game_kind, "year": year})
            results.append({
                "id": f"{year}-{game_kind}-{number}", "year": year, "kindCode": game_kind,
                "gameSno": number, "away": away, "home": home,
                "awayScore": _get_number(raw.get("VisitingTotalScore")),
                "homeScore": _get_number(raw.get("HomeTotalScore")),
                "statusCode": _get_number(raw.get("GameStatus")),
                "startAt": _s(raw.get("GameDateTimeS") or raw.get("GameDate") or "", 40),
                "stadium": _s(raw.get("FieldAbbe") or "", 55),
                "officialUrl": f"{BASE}/box/live?{qs}",
                "innings": [], "events": [], "awayHits": None, "homeHits": None,
                "awayErrors": None, "homeErrors": None, "detailAvailable": False,
            })
    if len(results) > 32:
        raise RuntimeError("CPBL returned >32 matches for one date")
    return results


def parse_detail(response, game):
    """Attach *optional* verified scoreboard & event fields; no fake counts."""
    payload = _unpack(response)
    if not isinstance(payload, dict) or str(payload.get("Success", "true")).lower() not in {"true", "1"}:
        raise RuntimeError("CPBL game detail was not successful")
    if not any(k in payload for k in ("ScoreboardJson", "GameDetailJson", "CurtGameDetailJson", "LiveLogJson")):
        raise RuntimeError("CPBL box/getlive returned no recognized fields")
    game = dict(game)
    detail = _unpack(payload.get("GameDetailJson"))
    if not isinstance(detail, list) or not detail:
        detail = _unpack(payload.get("CurtGameDetailJson"))
    if isinstance(detail, list) and detail and isinstance(detail[0], dict):
        g = detail[0]
    elif isinstance(detail, dict):
        g = detail
    else:
        g = {}
    if g:
        if _get_number(g.get("GameSno")) not in (None, game["gameSno"]):
            raise RuntimeError("game detail ID mismatch")
        for src, dest in (("VisitingTotalScore", "awayScore"), ("HomeTotalScore", "homeScore"),
                          ("GameStatus", "statusCode")):
            v = _get_number(g.get(src))
            if v is not None:
                game[dest] = v
        game["stadium"] = _s(g.get("FieldAbbe") or game["stadium"], 55)

    boards = _unpack(payload.get("ScoreboardJson"))
    if isinstance(boards, list):
        by_inning = {}
        totals = {1: {"hits": 0, "errors": 0, "found": False}, 2: {"hits": 0, "errors": 0, "found": False}}
        for r in boards:
            if not isinstance(r, dict):
                continue
            inning = _get_number(r.get("InningSeq"))
            side = _get_number(r.get("VisitingHomeType"))
            if inning is None or not 1 <= inning <= 25 or side not in (1, 2):
                continue
            out = by_inning.setdefault(inning, {"inning": inning, "away": None, "home": None})
            out["away" if side == 1 else "home"] = _get_number(r.get("ScoreCnt"))
            hits = _get_number(r.get("HittingCnt"))
            errors = _get_number(r.get("ErrorCnt"))
            if hits is not None and errors is not None:
                totals[side]["hits"] += hits
                totals[side]["errors"] += errors
                totals[side]["found"] = True
        if totals[1]["found"]:
            game["awayHits"], game["awayErrors"] = totals[1]["hits"], totals[1]["errors"]
        if totals[2]["found"]:
            game["homeHits"], game["homeErrors"] = totals[2]["hits"], totals[2]["errors"]
        game["innings"] = [by_inning[i] for i in sorted(by_inning)]

    logs = _unpack(payload.get("LiveLogJson"))
    if isinstance(logs, list):
        events = []
        if any(isinstance(r, dict) and r.get("CreateTime") for r in logs):
            logs = sorted(logs, key=lambda r: str(r.get("CreateTime") or "") if isinstance(r, dict) else "")
        for r in logs[-120:]:
            if not isinstance(r, dict):
                continue
            content = _s(r.get("Content"), 500)
            action = _s(r.get("BattingActionName") or r.get("ActionName"), 90)
            if not content and not action:
                continue
            events.append({
                "inning": _get_number(r.get("InningSeq")),
                "side": _get_number(r.get("VisitingHomeType")),
                "hitter": _s(r.get("HitterName"), 70),
                "pitcher": _s(r.get("PitcherName"), 70),
                "content": content, "action": action,
                "outs": _get_number(r.get("OutCnt")),
                "balls": _get_number(r.get("BallCnt")),
                "strikes": _get_number(r.get("StrikeCnt")),
                "first": str(r.get("FirstBase") or "").strip() not in ("", "0", "None", "null"),
                "second": str(r.get("SecondBase") or "").strip() not in ("", "0", "None", "null"),
                "third": str(r.get("ThirdBase") or "").strip() not in ("", "0", "None", "null"),
                "scored": str(r.get("IsScoreCnt") or "").strip().lower() in ("1", "true"),
                "awayScore": _get_number(r.get("VisitingScore")),
                "homeScore": _get_number(r.get("HomeScore")),
            })
        game["events"] = events[-80:]
    game["detailAvailable"] = bool(g or game["innings"] or game["events"])
    return game


def fetch_today(session, day: dt.date):
    schedule_html = _request(session, "GET", f"{BASE}/schedule")
    token = _token(schedule_html)
    raw = _request(session, "POST", f"{BASE}/home/getdetaillist", data={
        "__RequestVerificationToken": token,
        "GameSno": "", "KindCode": "", "GameDate": day.strftime("%Y/%m/%d"),
    }, headers={"Referer": f"{BASE}/schedule"})
    games = parse_listing(json.loads(raw), day)
    detail_failures = 0
    for idx, game in enumerate(games):
        try:
            html = _request(session, "GET", game["officialUrl"])
            live_token = _token(html)
            text = _request(session, "POST", f"{BASE}/box/getlive", data={
                "__RequestVerificationToken": live_token,
                "GameSno": str(game["gameSno"]),
                "KindCode": game["kindCode"],
                "Year": str(game["year"]),
            }, headers={"Referer": game["officialUrl"]})
            games[idx] = parse_detail(json.loads(text), game)
        except (ValueError, requests.RequestException, RuntimeError) as exc:
            detail_failures += 1
            # The official match link is still shown, even if a box score is inaccessible.
            print(f"WARN: {game['id']} box detail unavailable ({type(exc).__name__}: {exc})", file=sys.stderr)
    result = {
        "schemaVersion": 1,
        "date": day.isoformat(),
        "updatedAt": dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds"),
        "source": "CPBL official public pages (unofficial integration)",
        "intervalHintMinutes": 5,
        "detailFailures": detail_failures,
        "games": games,
    }
    return result


def validate_snapshot(blob, day):
    if not isinstance(blob, dict) or blob.get("schemaVersion") != 1 or blob.get("date") != day.isoformat():
        raise ValueError("invalid live snapshot metadata")
    if not isinstance(blob.get("games"), list) or len(blob["games"]) > 32:
        raise ValueError("invalid live game list")
    ids = set()
    for g in blob["games"]:
        if not all(isinstance(g.get(k), str) and g[k] for k in ("id", "away", "home", "officialUrl")):
            raise ValueError("invalid game names or URL")
        if g["id"] in ids or not g["officialUrl"].startswith(BASE + "/box/live?"):
            raise ValueError("duplicate game or unsafe official link")
        ids.add(g["id"])
    return True


def publish_snapshot(blob, day, directory=LIVE_DIR):
    validate_snapshot(blob, day)
    directory.mkdir(parents=True, exist_ok=True)
    raw = (json.dumps(blob, ensure_ascii=False, indent=2) + "\n").encode("utf-8")
    # Write the dated snapshot before 'latest' so latest always points to a dated file.
    for file in (directory / f"{day.isoformat()}.json", directory / "latest.json"):
        temp = file.with_suffix(".tmp")
        temp.write_bytes(raw)
        os.replace(temp, file)


def main(argv=None):
    parser = argparse.ArgumentParser()
    parser.add_argument("--date", help="Taipei calendar day YYYY-MM-DD (default today)")
    args = parser.parse_args(argv)
    day = dt.date.fromisoformat(args.date) if args.date else today_taipei()
    with requests.Session() as session:
        session.headers.update(HEADERS)
        blob = fetch_today(session, day)
    publish_snapshot(blob, day)
    print(f"PASS {day} matches={len(blob['games'])} box-details-failed={blob['detailFailures']} ")
    if blob["detailFailures"]:
        print("Warning: partial box details, official links remain available")


if __name__ == "__main__":
    main()
