import hashlib,importlib.util,json,sys,unittest,zipfile
from pathlib import Path
HERE=Path(__file__).resolve().parent;sys.path.insert(0,str(HERE))
spec=importlib.util.spec_from_file_location('stage_probe_test',HERE/'far_stage_probe.py');m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
class StageProbe(unittest.TestCase):
 def test_constant_resolve(self):self.assertEqual(m.resolve([4,8,12,255]*1024),[4,8,12,255]*4096)
 def test_saved_stages(self):
  for driver in ('mesa','angle'):
   r=json.loads((HERE/'evidence'/f'far-stage-probe-{driver}.json').read_text());archive=HERE/'evidence'/r['archive']['file'];self.assertEqual(hashlib.sha256(archive.read_bytes()).hexdigest(),r['archive']['sha256'])
   with zipfile.ZipFile(archive) as z:
    low=list(z.read('actual-far32.rgba'));resolved=list(z.read('actual-resolve64.rgba'));final=list(z.read('actual-foreground64.rgba'))
    self.assertEqual(len(low),4096);self.assertEqual(len(resolved),16384);self.assertEqual(len(final),16384)
    self.assertEqual(max(abs(a-b) for a,b in zip(resolved,m.resolve(low))),r['actual_low_to_resolve_cpu_max_error'])
    for stage in ['far32','resolve64','foreground64']:
     actual=z.read('actual-'+stage+'.rgba');cpu=z.read('cpu-'+stage+'.rgba');self.assertEqual(max(abs(a-b) for a,b in zip(actual,cpu)),r['cpu_max_errors'][stage])
   self.assertEqual(r['status'],'HOST_PASS');self.assertTrue(r['diagnostic_only']);self.assertEqual(r['diagnostic_readbacks'],3)
   with zipfile.ZipFile(HERE/'evidence'/f'far-reconstruction-{driver}.zip') as z:self.assertEqual(final,list(z.read('cam0-far_bilinear.rgba')))
 def test_extra_low_tap_explains_threshold(self):
  r=json.loads((HERE/'evidence/far-stage-probe-mesa.json').read_text());p=r['point'];self.assertEqual(p['taps'][3]['actual'][3],14);self.assertEqual(p['taps'][3]['cpu'][3],13);self.assertEqual(p['actual_low32_weighted_rgba'][3],12.5625);self.assertEqual(p['cpu_weighted_rgba'][3],12.375);self.assertEqual(p['stages']['resolve64']['actual'][3],13)
if __name__=='__main__':unittest.main()
