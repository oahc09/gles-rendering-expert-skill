import importlib.util,json,tempfile,unittest
from pathlib import Path
HERE=Path(__file__).resolve().parent
spec=importlib.util.spec_from_file_location('compressed_assets',HERE/'assets.py');m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
class Compressed(unittest.TestCase):
 def test_bad_archive_rejected_before_execution(self):
  with tempfile.TemporaryDirectory() as tmp:
   archive=Path(tmp)/'bad';archive.write_bytes(b'not official')
   with self.assertRaises(ValueError):m.verify_tools(Path(tmp),archive)
 def test_quality_boundary(self):
  self.assertEqual(m.quality([32]*64,[0]*64),32);self.assertGreater(m.quality([33]*64,[0]*64),32)
 def test_invalid_pixels(self):
  for image in [[0]*63,[float('nan')]*64,[True]*64]:
   with self.assertRaises(ValueError):m.quality(image,[0]*64)
 def test_dual_actual_chain(self):
  for driver in ['mesa','angle']:
   r=json.loads((HERE/'evidence'/f'{driver}.json').read_text());self.assertEqual(r['status'],'HOST_PASS');self.assertEqual(len(r['frames']),24);self.assertEqual(r['reloads'],17);self.assertGreater(r['cpu_cache_hits'],0)
   self.assertEqual([a['candidate_error'] for a in r['asset_preparation']],[14,8,119]);self.assertTrue(r['asset_preparation'][-1]['fallback'])
   self.assertEqual(r['asset_preparation'][-1]['optimization_status'],'REJECTED_BY_QUALITY')
   for frame in r['frames']:
    self.assertLessEqual(frame['upload_bytes'],64);self.assertLessEqual(frame['resident_bytes'],80)
    for sample in frame['samples']:
     self.assertLessEqual(sample['cpu_decode_error'],1);self.assertLessEqual(sample['authored_error'],32)
     if sample['asset']=='C':self.assertEqual(sample['route'],'rgba');self.assertEqual(sample['authored_error'],0)
 def test_no_gpu_performance_claim(self):
  for driver in ['mesa','angle']:
   r=json.loads((HERE/'evidence'/f'{driver}.json').read_text());self.assertIsNone(r['gpu_time_ms']);self.assertIsNone(r['physical_resident_bytes']);self.assertEqual(r['performance_status'],'NOT_MEASURED')
if __name__=='__main__':unittest.main()
