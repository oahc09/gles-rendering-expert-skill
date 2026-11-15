import copy,importlib.util,json,unittest
from pathlib import Path
HERE=Path(__file__).resolve().parent
spec=importlib.util.spec_from_file_location('interleaved',HERE/'run.py');m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
class Capture(unittest.TestCase):
 def load(self):return json.loads((HERE/'evidence/mesa.json').read_text())['tracks'][0]
 def test_real_dual_driver_tracks(self):
  for driver in ('mesa','angle'):
   report=json.loads((HERE/'evidence'/f'{driver}.json').read_text());self.assertEqual(len(report['tracks']),4)
   for track in report['tracks']:
    decision=m.judge(track);self.assertEqual(decision,track['decision']);self.assertEqual(decision['harness_status'],'HOST_PASS');self.assertFalse(decision['performance_acceptance']);self.assertFalse(decision['physical_protocol_eligible'])
    if track['candidate']=='negative':self.assertEqual(decision['optimization_status'],'REJECTED_BY_QUALITY')
 def test_bad_order_source_and_timing(self):
  for field,value in [('variant','B'),('order',99),('source_hashes',{}),('gpu_ms',[1.0]),('clock_domain','cpu')]:
   row=self.load();row['runs'][0][field]=value
   with self.assertRaises(ValueError):m.judge(row)
 def test_forged_quality(self):
  t=self.load();t['runs'][1]['samples'][0]['pixels']=[0]*256
  with self.assertRaises(ValueError):m.judge(t)
 def test_invalid_pixel(self):
  for bad in ([0]*255,[float('nan')]*256):
   t=self.load();t['runs'][1]['samples'][0]['pixels']=bad
   with self.assertRaises(ValueError):m.judge(t)
 def test_unknown_task_and_golden(self):
  for field,value in [('family','shell-command'),('candidate','custom'),('cpu_golden',[0]*256),('input','other')]:
   t=self.load();t[field]=value
   with self.assertRaises(ValueError):m.judge(t)
 def test_baseline_failure(self):
  t=self.load();s=t['runs'][0]['samples'][0];s['pixels']=[0]*256;s['cpu_quality']=m.pairs.compare(s['pixels'],m.golden('sampling'))
  with self.assertRaises(ValueError):m.judge(t)
if __name__=='__main__':unittest.main()
