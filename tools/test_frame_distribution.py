import unittest
from workload_fingerprint import frame_distribution,fingerprint
class DistributionTests(unittest.TestCase):
 def test_empty_unknown(self):
  row=frame_distribution([])
  self.assertEqual(row['sample_count'],0)
  self.assertIsNone(row['p95'])
  self.assertIsNone(row['mean'])
 def test_nearest_rank(self):
  row=frame_distribution(list(reversed(range(1,101))))
  self.assertEqual([row[x] for x in ('p50','p95','p99','min','max','mean')],[50,95,99,1,100,50.5])
 def test_single(self): self.assertEqual(frame_distribution([7])['p99'],7)
 def test_finite_mean_large(self): self.assertEqual(frame_distribution([1e308,1e308])['mean'],1e308)
 def test_invalid(self):
  for x in (float('nan'),float('inf'),-1,True,'2'):
   with self.assertRaises(ValueError): frame_distribution([x])
 def test_no_gpu_inference(self):
  row=fingerprint(dict(workload_id='example',provenance='synthetic',resolution=[1,1],frame_times_ms=[100]))
  self.assertEqual(row['labels'],['UNKNOWN'])
  self.assertEqual(row['performance_improvement'],'NOT_MEASURED')
