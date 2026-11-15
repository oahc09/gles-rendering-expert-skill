import json,pathlib,hashlib,unittest
D=pathlib.Path(__file__).parent
class DiagnosisTests(unittest.TestCase):
 def test_source_bound_six_controls(self):
  r=json.loads((D/'evidence.json').read_text());self.assertEqual(r['source_sha256'],hashlib.sha256((D/'probe.py').read_bytes()).hexdigest());self.assertEqual(len(r['rows']),6);self.assertEqual(r['status'],'FAIL');self.assertFalse(r['root_cause_proven'])
  for x in r['rows']:
   p=x['report'];self.assertTrue(p['compile'] and p['link'] and p['fbo_complete']);self.assertTrue(all(z['gl_error']==0 for z in p['checkpoints']))
   if x['exit']==0:self.assertEqual(p['status'],'PASS');self.assertLessEqual(p['max_error'],1);self.assertEqual(len(p['pixels']),64)
   else:self.assertEqual(x['exit'],-11);self.assertEqual(p['checkpoints'][-1]['name'],'clear_before_draw');self.assertNotIn('pixels',p)
 def test_no_fingerprints(self):
  text=(D/'evidence.json').read_text()
  for s in ['/tmp/','/workspace/','GL_RENDERER','GL_VENDOR','libraries','os_build']:self.assertNotIn(s,text)
if __name__=='__main__':unittest.main()
