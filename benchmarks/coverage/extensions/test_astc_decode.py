import hashlib,importlib.util,json,unittest
from pathlib import Path
P=Path(__file__).with_name('astc_decode.py');s=importlib.util.spec_from_file_location('astc_decode_test',P);m=importlib.util.module_from_spec(s);s.loader.exec_module(m)
class Decode(unittest.TestCase):
 def test_dual_archived_readback(self):
  for driver in ('mesa','angle'):
   r=json.loads((P.parent/'evidence'/('astc-decode-'+driver+'.json')).read_text())
   self.assertEqual(r['status'],'HOST_PASS');self.assertTrue(m.verdict(r['result']));self.assertTrue(r['wrong_color_rejected'])
   self.assertEqual(r['source_sha256'],hashlib.sha256(P.read_bytes()).hexdigest());self.assertEqual(r['mechanism_sha256'],hashlib.sha256(m.MECHANISM.read_bytes()).hexdigest())
 def test_each_failure_is_rejected(self):
  r={'pixels':[255,0,0,255]*16,'gl_error':0,'compile':True,'link':True,'quality':'PASS'}
  self.assertTrue(m.verdict(r))
  for key,value in [('pixels',[]),('pixels',[0,255,0,255]*16),('pixels',[255,0,0,254]*16),('gl_error',1280),('compile',False),('link',False),('quality','FAIL')]:
   self.assertFalse(m.verdict(dict(r,**{key:value})))
