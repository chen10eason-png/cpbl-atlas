import sys,unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from sync_official import season_batter,season_pitcher,optional_decimal
from sync_halves import parse_team_history

class ExtendedOfficialTests(unittest.TestCase):
    def test_carries_original_official_ops_plus(self):
        row={'排名 球員':'1 台鋼雄鷹 吳念庭','打席':369,'打數':326,'安打':108,
             '全壘打':2,'二安':20,'三安':0,'壘打數':134,'OPS+':'139','BIP%':'76.567',
             '四壞':39,'（故四）':'（0）'}
        d=season_batter(row,{},2025)
        self.assertEqual(d['opsPlusOfficial'],139)
        self.assertAlmostEqual(d['bipPctOfficial'],76.567)
        self.assertEqual(d['IBB'],0)
        self.assertIsNone(d['GO'])
    def test_pitcher_retains_era_plus_fip(self):
        row={'排名 球員':'1 味全龍 蔣銲','投球局數':'113.1','自責分':17,
             '失分':23,'ERA+':'236.29','FIP':'2.280'}
        p=season_pitcher(row,{},2026)
        self.assertEqual(p['outs'],340)
        self.assertAlmostEqual(p['eraPlusOfficial'],236.29)
        self.assertAlmostEqual(p['fipOfficial'],2.28)
    def test_optional_means_missing_not_zero(self):
        self.assertEqual(optional_decimal({'OPS+':0},'OPS+'),0.0)
        self.assertIsNone(optional_decimal({'OPS+':'-'},'OPS+'))
        self.assertIsNone(optional_decimal({},'OPS+'))
    def test_home_away_reconciles(self):
        html='<table><tr><th>年度</th><th>出賽數</th><th>勝</th><th>敗</th><th>和</th><th>勝率</th><th>主場勝</th><th>主場敗</th><th>主場和</th><th>客場勝</th><th>客場敗</th><th>客場和</th></tr><tr><td>2025(上)</td><td>60</td><td>36</td><td>24</td><td>0</td><td>.60</td><td>19</td><td>11</td><td>0</td><td>17</td><td>13</td><td>0</td></tr></table>'
        self.assertEqual(parse_team_history(html)[2025]['first']['homeW'],19)
        with self.assertRaises(ValueError):parse_team_history(html.replace('<td>19</td>','<td>18</td>'))

if __name__=='__main__':unittest.main()
