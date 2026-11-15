import unittest
import api_pipeline as p
class ApiTests(unittest.TestCase):
 def setUp(self):self.c=p.corpus()['viewport-negative']
 def test_seven_cases(self):self.assertEqual(len(p.corpus()),7)
 def test_good_parse(self):self.assertEqual(p.parse(self.c,'glViewport(0,0,4,4);'),[0,0,4,4])
 def test_reject_injected_source(self):
  for raw in ('glViewport(0,0,4,4);other();','glClear(0);','glViewport(0,0,x,4);','glViewport(0,0,65536,4);','glViewport(0,0,4);','x'*257):
   with self.subTest(raw=raw),self.assertRaises(ValueError):p.parse(self.c,raw)
 def test_error_free_noop_not_repair(self):self.assertEqual(p.run('viewport-negative','glViewport(0,0,0,0);',[])['status'],'FAIL')
 def test_missing_drivers_closed(self):self.assertEqual(p.run('viewport-negative','glViewport(0,0,4,4);',[])['status'],'BLOCKED_BY_DRIVER')
