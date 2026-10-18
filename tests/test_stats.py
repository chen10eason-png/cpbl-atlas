import sys
import unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from sync import batter, pitcher, innings_outs, read_csv, sync_year

class TransformTests(unittest.TestCase):
    def test_ip_not_decimal(self):
        self.assertEqual(innings_outs('12.1'),37)
        self.assertEqual(innings_outs('12.2'),38)
        with self.assertRaises(ValueError): innings_outs('12.3')
    def test_batter_metrics(self):
        x=batter({'ID':'00001','Name':'測試','Team ID':'A','Team Name':'球隊','G':'1','PA':'10','AB':'8','H':'4','1B':'2','2B':'1','3B':'0','HR':'1','TB':'8','BB':'1','HBP':'1','SO':'2','SF':'0'})
        self.assertEqual(x['id'],'00001')
        self.assertAlmostEqual(x['avg'],.5)
        self.assertAlmostEqual(x['obp'],.6)
        self.assertAlmostEqual(x['slg'],1.0)
        self.assertAlmostEqual(x['iso'],.5)
    def test_pitcher_metrics(self):
        x=pitcher({'ID':'00001','Name':'測試','Team ID':'A','IP':'9.0','ER':'2','H':'5','BB':'1','SO':'9'})
        self.assertAlmostEqual(x['era'],2.0)
        self.assertAlmostEqual(x['whip'],.66667,places=4)
    def test_csv_malformed_blocks_publish(self):
        with self.assertRaises(ValueError):
            read_csv('ID,Name\n01,John',expected=['H'],min_rows=1)

if __name__=='__main__': unittest.main()
