import unittest
from update_radar import day,event_utc_day,select,validate_decision
class RadarV104Tests(unittest.TestCase):
    def test_utc_offset_boundary(self):self.assertEqual(str(event_utc_day('2026-11-01T23:30:00-02:00')),'2026-11-02')
    def test_unknown_timezone_not_verified(self):self.assertIsNone(event_utc_day('2026-11-01T23:30:00'))
    def test_date_only_unknown(self):self.assertIsNone(event_utc_day('2026-11-01'))
    def test_unknown_date_deferred(self):self.assertEqual(select([{'source':'x','id':'1','event_at':'unknown'}],day('2026-10-02'),day('2026-11-01'),set()),[])
    def test_offset_outside_window(self):self.assertEqual(select([{'source':'x','id':'1','event_at':'2026-11-01T23:30:00-02:00'}],day('2026-10-02'),day('2026-11-01'),set()),[])
    def test_incomplete_no_verified(self):
        with self.assertRaises(ValueError):validate_decision({'stage':'source_verified','original_url':'https://example.org','event_at':'2026-11-01T00:00:00Z','source_evidence':'hash','retrieval_complete':False})
    def test_accepted_requires_mappings(self):
        with self.assertRaises(ValueError):validate_decision({'stage':'accepted','original_url':'https://example.org','event_at':'2026-11-01T00:00:00Z','source_evidence':'hash','retrieval_complete':True,'reproduction_evidence':'capture'})
    def test_deferred_can_be_unknown(self):self.assertEqual(validate_decision({'stage':'deferred'})['stage'],'deferred')
if __name__=='__main__':unittest.main()
