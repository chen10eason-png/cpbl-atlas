import datetime as dt
import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import Mock

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
from sync_live_stats import (
    parse_schedule, attach_detail, create_snapshot, collect_month, publish_many,
    game_skeleton, validate, day_of, STATUS,
)

DAY = dt.date(2026, 10, 20)

def game(id='2026-C-3', date='2026-10-20T18:35:00', status='START'):
    return {
        'GameId': id, 'GameSno': int(id.split('-')[-1]), 'KindCode': id.split('-')[1],
        'PreExeDate': date, 'GameStatus': status, 'FieldAbbe': '臺北大巨蛋',
        'Visiting': {'Team': {'Code': 'DRG', 'Name': '味全龍'}, 'Score': 1,
                     'HittingCnt': 3, 'ErrorCnt': 0,
                     'InningScore': [{'Seq': 1, 'Score': 1}, {'Seq': 2, 'Score': 0}]},
        'Home': {'Team': {'Code': 'BRO', 'Name': '中信兄弟'}, 'Score': 0,
                 'HittingCnt': 2, 'ErrorCnt': 1,
                 'InningScore': [{'Seq': 1, 'Score': 0}, {'Seq': 2, 'Score': 0}]},
        'LiveLog': [{'InningSeq': 1, 'VisitingHomeType': 1, 'Content': '一壘安打',
                     'HitterName': '打者A', 'PitcherName': '投手B', 'FirstBase': '3',
                     'OutCnt': 0, 'BallCnt': 0, 'StrikeCnt': 1}],
    }


class LiveStatsTests(unittest.TestCase):
    def test_day_and_postseason_parse(self):
        g = parse_schedule({'Data': {'Games': [game(), game(date='2026-10-19T18:35:00')]}}, DAY, 'C')
        self.assertEqual(len(g), 1)
        self.assertEqual(g[0]['id'], '2026-C-3')
        self.assertEqual((g[0]['away'], g[0]['home']), ('味全龍', '中信兄弟'))
        self.assertEqual((g[0]['awayScore'], g[0]['homeScore']), (1, 0))
        self.assertEqual(g[0]['statusCode'], 4)
        self.assertEqual(g[0]['statsUrl'], 'https://stats.cpbl.com.tw/schedule/2026-C-3')
        self.assertEqual(day_of(game()), DAY)

    def test_real_state_detail_enrichment(self):
        stub = game()
        bare = game_skeleton(stub, DAY)
        full = attach_detail({'Data': {'Game': stub}}, bare)
        self.assertEqual(full['awayHits'], 3)
        self.assertEqual(full['homeErrors'], 1)
        self.assertEqual(full['innings'], [{'inning': 1, 'away': 1, 'home': 0},
                                          {'inning': 2, 'away': 0, 'home': 0}])
        self.assertTrue(full['events'][0]['first'])
        self.assertTrue(full['detailAvailable'])

    def test_mismatched_identity_cannot_merge(self):
        bare = game_skeleton(game(), DAY)
        with self.assertRaises(ValueError):
            attach_detail({'Data': {'Game': game('2026-E-3')}}, bare)

    def test_bad_listing_must_not_be_empty_day(self):
        with self.assertRaises(ValueError):
            parse_schedule({'Data': {}}, DAY, 'C')
        with self.assertRaises(ValueError):
            parse_schedule({'Data': {'Games': [dict(game(), Visiting={})]}}, DAY, 'C')

    def test_mandatory_kinds_fail_closed(self):
        class Fake:
            def get(self, *_a, **_k):
                raise RuntimeError('should not be called')
        import sync_live_stats as live
        old = live.validated_json
        try:
            def fake(_session, _url, *, params):
                if params['kindCode'] == 'C':
                    raise ValueError('simulated unreachable')
                return {'Data': {'Games': []}}
            live.validated_json = fake
            with self.assertRaises(RuntimeError):
                collect_month(Fake(), 2026, 10)
        finally:
            live.validated_json = old

    def test_publish_index_backfill_does_not_replace_newest(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            current = {'schemaVersion': 1, 'date': DAY.isoformat(),
                       'updatedAt': '2026-10-20T12:00:00+00:00', 'games': [game_skeleton(game(), DAY)]}
            publish_many({DAY: current}, root)
            past = dt.date(2026, 10, 19)
            earlier = game('2026-E-2', '2026-10-19T17:05:00', 'FINISHED')
            older = {'schemaVersion': 1, 'date': past.isoformat(),
                     'updatedAt': '2026-10-20T12:15:00+00:00',
                     'games': [game_skeleton(earlier, past)]}
            publish_many({past: older}, root)
            idx = json.loads((root/'index.json').read_text())
            self.assertEqual([d['date'] for d in idx['dates']], ['2026-10-20','2026-10-19'])
            self.assertEqual(json.loads((root/'latest.json').read_text())['date'], DAY.isoformat())
            with self.assertRaises(ValueError):
                publish_many({past: dict(older, date='2026-10-18')}, root)
            self.assertEqual(json.loads((root/'index.json').read_text())['dates'][0]['date'], DAY.isoformat())

    def test_empty_day_is_only_valid_with_verified_monthly_list(self):
        class Fake: pass
        summary = create_snapshot(Fake(), DAY, {'A': [], 'C': [], 'E': []})
        self.assertEqual(summary['games'], [])
        self.assertEqual(summary['date'], DAY.isoformat())
        self.assertIn('FINISHED', STATUS)

if __name__ == '__main__': unittest.main()
