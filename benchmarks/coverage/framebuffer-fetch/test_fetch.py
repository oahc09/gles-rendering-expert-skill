import hashlib,json,sys,unittest
from pathlib import Path
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[2];sys.path.insert(0,str(ROOT/'tools/coverage'))
from framebuffer_fetch import decide
class Fetch(unittest.TestCase):
 def test_policy_requires_evidence(self):
  ex=['GL_EXT_shader_framebuffer_fetch','GL_EXT_shader_framebuffer_fetch_non_coherent']
  self.assertEqual(decide(ex),'PING_PONG');self.assertEqual(decide(ex,probe_pass=True),'FETCH_COHERENT')
  self.assertEqual(decide([],probe_pass=True),'PING_PONG')
  for entry,ordered in [(False,False),(True,False),(False,True)]:self.assertEqual(decide(ex,True,entry,ordered,True),'REJECT_MISSING_ORDERING')
  self.assertEqual(decide(ex,True,True,True,False),'PING_PONG');self.assertEqual(decide(ex,True,True,True,True),'FETCH_NONCOHERENT')
 def test_actual_archives_and_failure_retained(self):
  for name in ['mesa','angle']:
   r=json.loads((HERE/'evidence'/(name+'.json')).read_text());self.assertEqual(r['suite_sha256'],hashlib.sha256((HERE/'suite.py').read_bytes()).hexdigest());self.assertEqual(r['probe_sha256'],hashlib.sha256((HERE/'run.py').read_bytes()).hexdigest());self.assertEqual(r['fallback_status'],'PASS')
   rows={x['mode']:x for x in r['rows']};self.assertEqual(set(rows),{'coherent','noncoherent','fallback'})
   self.assertEqual(r['status'],'FAIL' if name=='mesa' else 'HOST_PASS')
   for mode,row in rows.items():
    if name=='mesa' and mode!='fallback':self.assertEqual(row['process_exit_code'],-11);self.assertEqual(row['status'],'FAIL');continue
    self.assertEqual(row['process_exit_code'],0);e=row['evidence'];self.assertEqual(e['source_sha256'],r['probe_sha256']);self.assertEqual(e['policy_sha256'],hashlib.sha256((ROOT/'tools/coverage/framebuffer_fetch.py').read_bytes()).hexdigest())
    actual=next(x for x in e['rows'] if x['mode']==mode);self.assertEqual(actual['status'],'PASS');self.assertEqual(len(actual['pixels']),64);self.assertLessEqual(max(abs(a-b) for a,b in zip(actual['pixels'],[128,191,64,255]*16)),1)
    self.assertTrue(next(x for x in e['rows'] if x['mode']=='missing_noncoherent_qualifier')['compile_rejected']);self.assertEqual(e['missing_barrier_policy'],'REJECT_MISSING_ORDERING')
