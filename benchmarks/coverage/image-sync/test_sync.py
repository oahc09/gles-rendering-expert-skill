import unittest,json,hashlib,importlib.util
from pathlib import Path
P=Path(__file__).parent
s=importlib.util.spec_from_file_location('image_sync',P/'run.py');m=importlib.util.module_from_spec(s);s.loader.exec_module(m)
class Tests(unittest.TestCase):
 def reports(self):return [json.loads((P/(x+'.json')).read_text()) for x in ['mesa','angle']]
 def test_real_routes(self):
  for r in self.reports():
   self.assertEqual(r['status'],'HOST_PASS');self.assertEqual([(x['route'],x['frame']) for x in r['frames']],[('server',0),('server',1),('client',0),('client',1)])
 def test_cpu_oracle(self):
  for r in self.reports():
   for x in r['frames']:self.assertEqual(x['pixels'],m.golden(x['frame']));self.assertEqual(x['max_byte_error'],0);self.assertTrue(x['wait_accepted'])
 def test_frames_distinct(self):self.assertNotEqual(m.golden(0),m.golden(1))
 def test_no_unsynced_policy(self):
  for fence,wait in [(False,True),(True,False),(None,True),(True,None)]:self.assertFalse(m.admit(fence,wait))
  self.assertTrue(m.admit(True,True))
 def test_real_cost_lifetime(self):
  for r in self.reports():self.assertEqual(r['draws'],8);self.assertEqual(r['readbacks'],4);self.assertTrue(r['owned_resources_released']);self.assertEqual(r['glFinish_calls'],0)
 def test_partial_cleanup_idempotent_mock(self):
  calls=[];record={'image':123,'tex':456}
  releasers={k:lambda v,k=k:calls.append((k,v)) for k in ['image','tex','sync','fb','ext']}
  m.release_owned(record,releasers);m.release_owned(record,releasers)
  self.assertEqual(calls,[('image',123),('tex',456)]);self.assertTrue(all(v is None for v in record.values()))
 def test_cleanup_failure_retry_mock(self):
  calls=[];record={'image':123,'sync':456};fail={'once':True}
  def image(v):
   calls.append('image')
   if fail['once']:fail['once']=False;return False
   return True
  releasers={'image':image,'sync':lambda v:calls.append('sync')}
  with self.assertRaises(RuntimeError):m.release_owned(record,releasers)
  self.assertEqual(record,{'image':123,'sync':None})
  m.release_owned(record,releasers);self.assertEqual(calls,['image','sync','image'])
 def test_teardown_failure_continues_mock(self):
  calls=[]
  def failed():calls.append('failed');raise RuntimeError('mock')
  result=m.best_effort([failed,lambda:calls.append('after-exception'),lambda:False,lambda:calls.append('after-false')])
  self.assertEqual(result,[False,True,False,True]);self.assertEqual(calls,['failed','after-exception','after-false'])
 def test_context_teardown_checked(self):
  for r in self.reports():self.assertTrue(r['context_teardown_checked'])
 def test_safe_bindings(self):
  for r in self.reports():self.assertEqual(r['source_sha256'],hashlib.sha256((P/'run.py').read_bytes()).hexdigest());self.assertNotIn('/tmp/',json.dumps(r));self.assertNotIn('renderer',r);self.assertEqual(r['physical_device'],'NOT_RUN')
if __name__=='__main__':unittest.main()
