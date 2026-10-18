import sys,unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from sync_halves import parse_team_history, reconcile_year, SINGLE_SEASON_YEARS

HTML='''<html><table><tr><th>年度</th><th>出賽數</th><th>勝</th><th>敗</th><th>和</th><th>勝率</th></tr><tr><td>2024(上)</td><td>60</td><td>37</td><td>23</td><td>0</td><td>.617</td></tr><tr><td>2024(下)</td><td>60</td><td>29</td><td>30</td><td>1</td><td>.492</td></tr><tr><td>1999</td><td>93</td><td>56</td><td>37</td><td>0</td><td>.602</td></tr></table></html>'''

class TestHalves(unittest.TestCase):
    def test_reconciled(self):
        h=parse_team_history(HTML)
        assert reconcile_year(2024,{'w':66,'l':53,'t':1},h)=={'first':{'w':37,'l':23,'t':0},'second':{'w':29,'l':30,'t':1}}
    def test_missing_year_or_fabricated_half(self):
        h=parse_team_history(HTML)
        with self.assertRaises(ValueError):reconcile_year(2024,{'w':65,'l':54,'t':1},h)
        with self.assertRaises(ValueError):reconcile_year(2023,{'w':66,'l':53,'t':1},h)
        self.assertIn(1998,SINGLE_SEASON_YEARS)
        with self.assertRaises(ValueError):reconcile_year(1999,{'w':56,'l':37,'t':0},h)
    def test_invalid_records(self):
        with self.assertRaises(ValueError):parse_team_history(HTML.replace('<td>37</td><td>23</td>', '<td>38</td><td>23</td>'))

if __name__=='__main__':unittest.main()
