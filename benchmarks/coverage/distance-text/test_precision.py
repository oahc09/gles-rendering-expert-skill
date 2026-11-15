import gzip,importlib.util,json,struct,unittest
from pathlib import Path
HERE=Path(__file__).resolve().parent
spec=importlib.util.spec_from_file_location('precision_test',HERE/'precision_probe.py');p=importlib.util.module_from_spec(spec);spec.loader.exec_module(p)
class PrecisionTests(unittest.TestCase):
 def test_packing(self):
  values=[0.,.5,1.,.5042892694473267];self.assertEqual(p.decode(list(struct.pack('<4f',*values))),values)
  with self.assertRaises(ValueError):p.decode([1])
  with self.assertRaises(ValueError):p.decode(list(struct.pack('<f',float('nan'))))
 def test_sources(self):
  source=p.base.fragment(32,'sdf','correct')
  self.assertEqual(p.transform(source,'original'),source)
  high=p.transform(source,'highp_hardware');self.assertIn('uniform highp sampler2D',high);self.assertIn('texture(',high);self.assertNotIn('texelFetch',high)
  manual=p.transform(source,'highp_four_tap');self.assertEqual(manual.count('texelFetch('),4);self.assertNotIn('texture(',manual)
  self.assertIn('precision highp int;',p.transform(source,'original',3))
 def test_archived_pixels(self):
  for driver in ('mesa','angle'):
   report=json.loads(gzip.decompress((HERE/'evidence'/('precision-'+driver+'.json.gz')).read_bytes()))
   self.assertEqual(report['status'],'HOST_PASS');self.assertEqual(report['draws'],102);self.assertEqual(len(report['rows']),54);self.assertEqual(len(report['probes']),12)
   for row in report['rows']:
    gold=p.base.golden(row['size'],row['kind']);self.assertEqual(len(row['pixels']),len(gold));error=max(abs(a-b) for a,b in zip(gold,row['pixels']));self.assertEqual(error,row['max_error'])
    if row['mode']=='highp_four_tap':self.assertEqual(row['quality'],'FAIL' if row['arm'].startswith('wrong_') else 'PASS')
   for probe in report['probes']:
    n=probe['size'];self.assertEqual(len(probe['packed_float_captures']),4)
    for capture in probe['packed_float_captures']:self.assertEqual(len(capture['pixels']),n*n*4);self.assertEqual(len(p.decode(capture['pixels'])),n*n)
    self.assertLessEqual(probe['instrumentation_byte_max_error'],1)
    if probe['mode']=='highp_four_tap':self.assertLess(probe['sample_max_abs_error'],1e-6);self.assertLess(probe['coverage_max_abs_error'],2e-6)
 def test_routing_budget(self):
  report=json.loads(gzip.decompress((HERE/'evidence/precision-mesa.json.gz').read_bytes()));rows=report['rows']
  for budget,route in ((1,'alpha_fallback'),(3,'alpha_fallback'),(4,'highp_four_tap'),(0,'UNAVAILABLE')):
   selected=next(x for x in p.select(rows,budget) if x['size']==32 and x['kind']=='sdf');self.assertEqual(selected['selected'],route)
  self.assertEqual(p.select(rows),p.select(rows,1))
  for bad in (-1,5,True,1.5):
   with self.assertRaises(ValueError):p.select(rows,bad)
  with self.assertRaises(ValueError):p.select(rows+[next(x for x in rows if x['mode']=='highp_hardware' and x['arm']=='correct')])
  self.assertEqual(report['decisions'],p.select(rows,4))
 def test_evidence_source_hashes(self):
  import hashlib
  for driver in ('mesa','angle'):
   r=json.loads(gzip.decompress((HERE/'evidence'/('precision-'+driver+'.json.gz')).read_bytes()));self.assertEqual(r['source_sha256'],hashlib.sha256((HERE/'precision_probe.py').read_bytes()).hexdigest());self.assertEqual(r['original_source_sha256'],hashlib.sha256((HERE/'run.py').read_bytes()).hexdigest())
 def test_original_failure_retained(self):
  r=json.loads(gzip.decompress((HERE/'evidence/precision-mesa.json.gz').read_bytes()))
  for mode in ('original','highp_hardware'):
   row=next(x for x in r['rows'] if x['mode']==mode and x['size']==32 and x['kind']=='sdf' and x['arm']=='correct');self.assertEqual(row['max_error'],9);self.assertEqual(row['quality'],'FAIL')
if __name__=='__main__':unittest.main()
