import datetime as d,unittest
from v109_radar_window import window
class Windows(unittest.TestCase):
 def test_week(self):self.assertEqual(window('weekly',d.date(2026,11,15))['start'],'2026-11-09')
 def test_month(self):self.assertEqual(window('monthly',d.date(2026,11,15))['start'],'2026-08-18')
 def test_leap(self):self.assertEqual(window('weekly',d.date(2024,3,1))['start'],'2024-02-24')
 def test_invalid(self):
  with self.assertRaises(ValueError):window('hourly',d.date.today())
