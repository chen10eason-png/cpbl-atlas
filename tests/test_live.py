import datetime as dt
import json
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
from sync_live import parse_listing, parse_detail, validate_snapshot, publish_snapshot

DAY = dt.date(2026, 10, 19)

def listing(games=None):
    return {'Success': True, 'GameADetailJson': json.dumps(games or [], ensure_ascii=False), 'GameDDetailJson': '[]'}

def game():
    return {'GameSno': 380, 'Year': 2026, 'KindCode': 'A', 'VisitingTeamName': '中信兄弟',
            'HomeTeamName': '味全龍', 'VisitingTotalScore': 2, 'HomeTotalScore': 0,
            'GameStatus': 4, 'GameDate': '2026/10/19'}

class LiveSnapshotTests(unittest.TestCase):
    def test_empty_day_genuinely_empty(self):
        self.assertEqual(parse_listing(listing(), DAY), [])

    def test_match_identity_official_url_and_actual_zero(self):
        data = parse_listing(listing([game()]), DAY)
        self.assertEqual(len(data), 1)
        self.assertEqual(data[0]['awayScore'], 2)
        self.assertEqual(data[0]['homeScore'], 0)
        self.assertEqual(data[0]['statusCode'], 4)
        self.assertEqual(data[0]['officialUrl'], 'https://www.cpbl.com.tw/box/live?gameSno=380&kindCode=A&year=2026')

    def test_missing_score_is_unknown_not_zero(self):
        r = game()
        r.pop('VisitingTotalScore')
        self.assertIsNone(parse_listing(listing([r]), DAY)[0]['awayScore'])

    def test_no_verification_is_not_empty_day(self):
        with self.assertRaises(RuntimeError):
            parse_listing({'Success': False, 'GameADetailJson': '[]'}, DAY)
        with self.assertRaises(RuntimeError):
            parse_listing({'Success': True}, DAY)

    def test_invalid_names_or_day_cannot_publish(self):
        g = game()
        g['HomeTeamName'] = ''
        with self.assertRaises(RuntimeError):
            parse_listing(listing([g]), DAY)
        g = game()
        g['GameDate'] = '2026/10/18'
        with self.assertRaises(RuntimeError):
            parse_listing(listing([g]), DAY)

    def test_detail_uses_correct_base_half_and_events(self):
        g = parse_listing(listing([game()]), DAY)[0]
        response = {
            'GameDetailJson': json.dumps([game()], ensure_ascii=False),
            'ScoreboardJson': json.dumps([
                {'InningSeq':1,'VisitingHomeType':1,'ScoreCnt':1},
                {'InningSeq':1,'VisitingHomeType':2,'ScoreCnt':0},
                {'InningSeq':2,'VisitingHomeType':1,'ScoreCnt':1}],ensure_ascii=False),
            'LiveLogJson': json.dumps([{'InningSeq':2,'VisitingHomeType':1,'Content':'右外野安打',
                'HitterName':'王測試','PitcherName':'陳測試','BattingActionName':'一壘安打',
                'OutCnt':1,'BallCnt':2,'StrikeCnt':1,'FirstBase':'3','SecondBase':'',
                'ThirdBase':'','VisitingScore':2,'HomeScore':0}],ensure_ascii=False)
        }
        r = parse_detail(response, g)
        self.assertTrue(r['detailAvailable'])
        self.assertEqual(r['innings'], [{'inning':1,'away':1,'home':0},{'inning':2,'away':1,'home':None}])
        self.assertEqual(r['events'][0]['hitter'], '王測試')
        self.assertTrue(r['events'][0]['first'])
        self.assertFalse(r['events'][0]['second'])

    def test_mismatched_game_id_does_not_merge(self):
        g = parse_listing(listing([game()]), DAY)[0]
        with self.assertRaises(RuntimeError):
            parse_detail({'GameDetailJson':json.dumps([{'GameSno':1}])},g)

    def test_validates_before_writing_no_clobber_on_bad(self):
        good = {'schemaVersion':1,'date':DAY.isoformat(),'updatedAt':'2026-10-19T11:00:00+00:00',
                'games':parse_listing(listing([game()]),DAY)}
        with tempfile.TemporaryDirectory() as directory:
            target = Path(directory)
            publish_snapshot(good,DAY,target)
            before = (target/'latest.json').read_bytes()
            bad = dict(good, date='2026-10-20')
            with self.assertRaises(ValueError):
                publish_snapshot(bad,DAY,target)
            self.assertEqual(before,(target/'latest.json').read_bytes())
            self.assertTrue(validate_snapshot(good,DAY))

if __name__=='__main__':
    unittest.main()

class ScoreboardExtensionTests(unittest.TestCase):
    def test_hit_and_error_totals_are_separate_and_optional(self):
        g = parse_listing(listing([game()]), DAY)[0]
        records = [
            {'InningSeq':1,'VisitingHomeType':1,'ScoreCnt':2,'HittingCnt':3,'ErrorCnt':0},
            {'InningSeq':1,'VisitingHomeType':2,'ScoreCnt':0,'HittingCnt':1,'ErrorCnt':1},
            {'InningSeq':2,'VisitingHomeType':1,'ScoreCnt':0,'HittingCnt':0,'ErrorCnt':0},
        ]
        x = parse_detail({'ScoreboardJson':json.dumps(records)},g)
        self.assertEqual((x['awayHits'],x['awayErrors'],x['homeHits'],x['homeErrors']), (3,0,1,1))
        y = parse_detail({'ScoreboardJson':json.dumps([{'InningSeq':1,'VisitingHomeType':1,'ScoreCnt':0}])},g)
        self.assertIsNone(y['awayHits'])
        self.assertIsNone(y['homeHits'])

    def test_zero_base_is_not_occupied(self):
        g = parse_listing(listing([game()]), DAY)[0]
        e = {'Content':'投球', 'FirstBase':'0','SecondBase':'1','ThirdBase':'', 'IsScoreCnt':'1'}
        x = parse_detail({'LiveLogJson':json.dumps([e])},g)
        self.assertFalse(x['events'][0]['first'])
        self.assertTrue(x['events'][0]['second'])
        self.assertTrue(x['events'][0]['scored'])
