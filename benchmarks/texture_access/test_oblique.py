import importlib.util,json,sys,unittest
from pathlib import Path
HERE=Path(__file__).resolve().parent;sys.path.insert(0,str(HERE))
spec=importlib.util.spec_from_file_location('oblique',HERE/'oblique.py');m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
class Oblique(unittest.TestCase):
 def test_locality_same_set_different_order(self):
  a,b,_=m.controls();groups=lambda c:[tuple(c['golden'][i:i+4]) for i in range(0,64,4)]
  self.assertNotEqual(groups(a),groups(b));self.assertEqual(sorted(groups(a)),sorted(groups(b)));self.assertIn('texelFetch',a['source'])
 def test_affine_nonconstant_oblique(self):
  c=m.controls()[2];self.assertIn('textureGrad',c['source']);self.assertEqual(c['tolerance'],3);self.assertGreater(len(set(c['golden'][::4])),4)
 def test_saved_dual_driver(self):
  for driver in ['mesa','angle']:
   report=json.loads((HERE/'evidence'/f'oblique-{driver}.json').read_text());self.assertEqual(report['status'],'HOST_PASS');self.assertEqual(len(report['experiments']),4)
   for r in report['experiments']:self.assertEqual(r['quality'],'PASS');self.assertEqual(r['gl_error'],0);self.assertEqual(r['performance_status'],'NOT_MEASURED')
if __name__=='__main__':unittest.main()
