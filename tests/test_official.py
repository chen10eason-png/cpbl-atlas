import sys
import unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from sync_official import parse_ident, season_batter, season_pitcher, player_id

class OfficialAdapterTests(unittest.TestCase):
    def test_label_with_brand_team(self):
        self.assertEqual(parse_ident('1 統一7-ELEVEn獅 陳傑憲'),('統一7-ELEVEn獅','陳傑憲'))
    def test_id_not_conflated_across_years(self):
        self.assertNotEqual(player_id('測試人','中信兄弟',{},2025),player_id('測試人','中信兄弟',{},2026))
    def test_batting_stats(self):
        r={'排名 球員':'1 中信兄弟 王測試','出賽數':5,'打席':100,'打數':90,'安打':27,'全壘打':3,'四壞':8,'死球':2,'犧飛':0,'壘打數':45}
        b=season_batter(r,{},2026)
        self.assertEqual(b['teamId'],'ACN')
        self.assertEqual(b['PA'],100)
        self.assertEqual(b['avg'],.3)
    def test_pitching_stats(self):
        r={'排名 球員':'1 味全龍 李測試','出賽數':10,'投球局數':'12.1','自責分':3,'奪三振':20}
        p=season_pitcher(r,{},2026)
        self.assertEqual(p['outs'],37)
        self.assertAlmostEqual(p['era'],81/37,places=4)

if __name__=='__main__':unittest.main()
