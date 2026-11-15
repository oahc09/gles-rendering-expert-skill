import importlib.util,pathlib,unittest,subprocess,tempfile
from unittest.mock import patch
ROOT=pathlib.Path(__file__).resolve().parents[3]
class BuildGuardTests(unittest.TestCase):
 def test_dirty_rejected(self):
  spec=importlib.util.spec_from_file_location('cb',ROOT/'tools/coverage/cts_build.py');m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
  with tempfile.TemporaryDirectory() as t,patch('sys.argv',['cts_build','--source',t,'--build',t,'--receipt',t+'/r.json']),patch.object(m.subprocess,'check_output',side_effect=[m.REVISION+'\n',' M CMakeLists.txt\n']),patch.object(m.subprocess,'run') as run:
   with self.assertRaisesRegex(SystemExit,'dirty tracked'):m.main()
   run.assert_not_called()
 def test_wrong_revision_rejected(self):
  with tempfile.TemporaryDirectory() as t:
   s=pathlib.Path(t)/'src';s.mkdir();subprocess.run(['git','init',str(s)],capture_output=True,check=True)
   (s/'x').write_text('x');subprocess.run(['git','-C',str(s),'add','x'],check=True)
   subprocess.run(['git','-C',str(s),'-c','user.name=Test','-c','user.email=test@example.invalid','commit','-m','test'],capture_output=True,check=True)
   r=subprocess.run(['python3',str(ROOT/'tools/coverage/cts_build.py'),'--source',str(s),'--build',str(pathlib.Path(t)/'build'),'--receipt',t+'/r.json'],capture_output=True,text=True)
   self.assertNotEqual(r.returncode,0);self.assertIn('revision mismatch',r.stderr)
if __name__=='__main__':unittest.main()
