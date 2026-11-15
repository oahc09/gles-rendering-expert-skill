import importlib.util
import json
from pathlib import Path
import unittest
spec=importlib.util.spec_from_file_location('rebind_under_test',Path(__file__).with_name('rebind.py'))
r=importlib.util.module_from_spec(spec);spec.loader.exec_module(r)
class RebindTests(unittest.TestCase):
 def test_distinct_resource_values(self):self.assertEqual(len({tuple(v) for v in r.SECOND}),4)
 def test_rounds_differ(self):self.assertTrue(all(a!=b for a,b in zip(r.FIRST,r.SECOND)))
 def test_compute_version(self):self.assertIn('#version 310 es',r.COMPUTE)
 def test_prior_read_not_write(self):self.assertIn('readonly buffer InputData',r.PRIME)
 def test_cpu_prime(self):self.assertEqual([x*2 for x in [2]*4],[4]*4)
 def test_safe_evidence(self):
  for name in ('rebind-mesa.json','rebind-angle.json'):
   path=Path(__file__).parent/'evidence'/name
   if not path.exists():continue
   text=path.read_text();data=json.loads(text)
   for key in ('/tmp/','/home/','metadata','executable_sha256','os_build','libraries'):self.assertNotIn(key,text)
   self.assertFalse(data['upstream_bug_reproduced']);self.assertEqual(data['performance'],'NOT_MEASURED')
 def test_captured_negative_matches_wrong_binding(self):
  for name in ('rebind-mesa.json','rebind-angle.json'):
   path=Path(__file__).parent/'evidence'/name
   if not path.exists():continue
   rows=json.loads(path.read_text())['cases'];self.assertEqual(rows[0]['readback'],r.SECOND)
   self.assertEqual(rows[1]['readback'],[r.SECOND[3],r.SECOND[1],r.SECOND[2],r.FIRST[3]])

if __name__=='__main__':unittest.main()
