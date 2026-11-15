import json,shutil,tempfile,unittest
from pathlib import Path
import sys
sys.path.insert(0,str(Path(__file__).resolve().parent))
from build_cases import corpus
from counterexamples import WRONG,golden,wrong
from variant_trace import variant,connect,ROOT
class VariantTraceTests(unittest.TestCase):
 def setUp(self):
  self.rows=[dict(id=c['id'],variants=[variant(src,a) for a,src in dict(c['sources'],negative=wrong(c['id'])[0]).items()]) for c in corpus()]
 def test_each_independent(self):self.assertEqual({x[0] for x in WRONG},{c['id'] for c in corpus()});self.assertEqual(len({x[1] for x in WRONG}),16)
 def test_goldens(self):self.assertTrue(all(len(golden(c['id']))==64 and all(type(x)is int and 0<=x<=255 for x in golden(c['id'])) for c in corpus()))
 def test_scalar_reference(self):self.assertEqual(golden('premultiply')[:4],[16,16,64,128])
 def test_variants(self):self.assertTrue(all(not v['errors'] for r in self.rows for v in r['variants']))
 def test_missing_trace(self):self.assertEqual(connect(self.rows)['status'],'NOT_MEASURED')
 def bundle(self,d,change=None):
  shutil.copytree(ROOT/'benchmarks/traces/fixtures/T01',Path(d)/'capture')
  b=dict(case=self.rows[0]['id'],arm='a',source_sha256=self.rows[0]['variants'][0]['source_sha256'],manifest='capture/trace-manifest.json')
  if change:b.update(change)
  p=Path(d)/'bundle.json';p.write_text(json.dumps(dict(bindings=[b])));return p
 def test_existing_trace_analyzer(self):
  with tempfile.TemporaryDirectory() as d:
   result=connect(self.rows,self.bundle(d));self.assertEqual(result['bindings'][0]['hypothesis_categories'],['cpu_submit_bound']);self.assertEqual(result['bindings'][0]['provenance'],'synthetic');self.assertNotIn('manifest_device',json.dumps(result));self.assertEqual(result['bindings'][0]['performance_improvement'],'NOT_MEASURED')
 def test_stale_hash(self):
  with tempfile.TemporaryDirectory() as d:
   p=self.bundle(d,dict(source_sha256='0'*64))
   with self.assertRaises(ValueError):connect(self.rows,p)
 def test_unknown_arm(self):
  with tempfile.TemporaryDirectory() as d:
   p=self.bundle(d,dict(arm='unknown'))
   with self.assertRaises(ValueError):connect(self.rows,p)
 def test_corrupt_trace(self):
  with tempfile.TemporaryDirectory() as d:
   p=self.bundle(d);(Path(d)/'capture/metrics.json').write_text('[]')
   with self.assertRaises(ValueError):connect(self.rows,p)
 def test_duplicate(self):
  with tempfile.TemporaryDirectory() as d:
   p=self.bundle(d);x=json.loads(p.read_text());x['bindings']*=2;p.write_text(json.dumps(x))
   with self.assertRaises(ValueError):connect(self.rows,p)
if __name__=='__main__':unittest.main()
