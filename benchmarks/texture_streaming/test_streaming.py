import importlib.util,json,unittest
from pathlib import Path
HERE=Path(__file__).resolve().parent
spec=importlib.util.spec_from_file_location('stream_planner',HERE/'planner.py');m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
class Streaming(unittest.TestCase):
 def test_lru_hot_reuse_reload(self):
  p=m.Planner(dict(A=64,B=64,C=64),128,64)
  for key in ['A','B','A']:p.commit(p.plan([key]))
  plan=p.plan(['C']);self.assertEqual(plan['evict'],['B']);p.commit(plan)
  self.assertEqual(p.plan(['B'])['upload'],['B'])
 def test_atomic_rejections(self):
  p=m.Planner(dict(A=64,B=64,C=64),128,64);p.commit(p.plan(['A']))
  for requests in [['B','C'],['A','B','C'],['missing'],[None]]:
   before=(dict(p.resident),p.generation)
   with self.assertRaises(ValueError):p.plan(requests)
   self.assertEqual((dict(p.resident),p.generation),before)
 def test_capacity_independent_of_upload(self):
  p=m.Planner(dict(A=64,B=64),64,128)
  with self.assertRaises(ValueError):p.plan(['A','B'])
 def test_stale_and_forged_plan(self):
  p=m.Planner(dict(A=64,B=64),128,64);plan=p.plan(['A']);p.commit(plan)
  with self.assertRaises(ValueError):p.commit(plan)
  plan=p.plan(['B']);plan['upload_bytes']=0
  with self.assertRaises(ValueError):p.commit(plan)
 def test_duplicate_requests_count_once(self):
  p=m.Planner(dict(A=64),64,64);self.assertEqual(p.plan(['A','A'])['upload_bytes'],64)
 def test_invalid_budgets(self):
  for size,capacity,budget in [(0,64,64),(64,False,64),(64,64,float('nan')),(64,64,-1)]:
   with self.assertRaises(ValueError):m.Planner(dict(A=size),capacity,budget)
 def test_saved_real_sequences(self):
  for driver in ['mesa','angle']:
   data=json.loads((HERE/'evidence'/f'{driver}.json').read_text());self.assertEqual(data['status'],'HOST_PASS');self.assertEqual(len(data['frames']),40);self.assertGreater(data['reloads'],0);self.assertGreater(data['cache_hits'],0)
   for frame in data['frames']:
    self.assertLessEqual(frame['upload_bytes'],128);self.assertLessEqual(frame['resident_bytes'],192)
    for sample in frame['samples']:self.assertTrue(sample['cpu_oracle_equal']);self.assertEqual(len(sample['pixels']),64)
   for row in data['negative_requests']:self.assertTrue(row['rejected'] and row['state_unchanged'])
if __name__=='__main__':unittest.main()
