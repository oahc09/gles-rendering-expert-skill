import importlib.util, json, tempfile, unittest
from pathlib import Path
from unittest.mock import patch
import reduce as reducer
class ReducerTests(unittest.TestCase):
 def test_preserves_failure_and_one_minimal(self):
  oracle=lambda s:{'matches':'BAD' in s,'exit_code':1}
  r=reducer.minimize('a\nBAD\nb\n',oracle)
  self.assertTrue(r['one_minimal']);self.assertEqual(r['source'],'BAD\n')
 def test_nonrepro_is_not_minimal(self):
  r=reducer.minimize('ok',lambda s:{'matches':False,'exit_code':0});self.assertEqual(r['status'],'NOT_REPRODUCED');self.assertFalse(r['one_minimal'])
 def test_budget_not_false_minimal(self):
  r=reducer.minimize('a\nBAD\nb\n',lambda s:{'matches':'BAD' in s,'exit_code':1},1);self.assertFalse(r['one_minimal'])
 def test_compiler_crash_not_expected_failure(self):
  import subprocess
  with patch('reduce.subprocess.run',return_value=subprocess.CompletedProcess([], -11,'needle','')):
   r=reducer.compile_source('x','compiler','frag','needle');self.assertFalse(r['matches']);self.assertTrue(r['compiler_crash'])
 def test_success_diagnostic_not_failure(self):
  import subprocess
  with patch('reduce.subprocess.run',return_value=subprocess.CompletedProcess([], 0,'needle','')):
   self.assertFalse(reducer.compile_source('x','compiler','frag','needle')['matches'])
 def test_timeout_not_reproduced(self):
  import subprocess
  with patch('reduce.subprocess.run',side_effect=subprocess.TimeoutExpired('compiler',5)):
   self.assertFalse(reducer.compile_source('x','compiler','frag','needle')['matches'])
 def test_unknown_deletion_not_one_minimal(self):
  def oracle(s):
   if s=='BAD\n':return {'matches':True,'exit_code':1}
   return {'matches':False,'exit_code':None,'error_type':'TimeoutExpired'}
  self.assertFalse(reducer.minimize('BAD\n',oracle)['one_minimal'])
 def test_crashing_deletion_not_one_minimal(self):
  def oracle(s):return {'matches':s=='BAD\n','exit_code':1 if s else -11,'compiler_crash':not bool(s)}
  self.assertFalse(reducer.minimize('BAD\n',oracle)['one_minimal'])
 def test_initial_unknown_is_inconclusive(self):
  r=reducer.minimize('x',lambda s:{'matches':False,'error_type':'OSError'})
  self.assertEqual(r['status'],'INCONCLUSIVE')
 def test_source_path_escape_rejected(self):
  for name in ('../secret.frag','/tmp/secret.frag','valid.vert'):
   with self.assertRaises(ValueError):reducer.fixture_source(Path('.'),name,'frag')
 def test_source_symlink_escape_rejected(self):
  with tempfile.TemporaryDirectory() as d:
   root=Path(d);folder=root/'fixtures';folder.mkdir();secret=root/'outside.frag';secret.write_text('secret')
   (folder/'linked.frag').symlink_to(secret)
   with self.assertRaises(ValueError):reducer.fixture_source(folder,'linked.frag','frag')
 def test_ten_fixture_inventory(self):
  fs=sorted((Path(__file__).parent/'fixtures').glob('*.json'));self.assertEqual(len(fs),10)
  for f in fs:
   x=json.loads(f.read_text());self.assertTrue((f.parent/x['patch']).exists());self.assertIn('authored',x['origin']);self.assertIsNone(x['device_evidence'])
 def test_actual_compiler_uses_no_shell(self):
  import subprocess
  with patch('reduce.subprocess.run',return_value=subprocess.CompletedProcess([],1,'needle','')) as p:
   reducer.compile_source('x','compiler','frag','needle');self.assertNotIn('shell',p.call_args.kwargs);self.assertEqual(p.call_args.args[0][:3],['compiler','-S','frag'])
if __name__=='__main__':unittest.main()
