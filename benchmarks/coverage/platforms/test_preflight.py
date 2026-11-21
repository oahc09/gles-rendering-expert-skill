import sys,unittest
from unittest.mock import patch
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[3]/'tools/coverage'))
from platform_preflight import inspect
class Preflight(unittest.TestCase):
 def test_missing_tools_not_pass(self):
  with patch('shutil.which',return_value=None),patch.object(Path,'is_file',return_value=False):self.assertEqual(inspect()['android_build'],'BLOCKED_BY_TOOLCHAIN')
 def test_ready_not_run(self):
  with patch('shutil.which',return_value='fixture'),patch.object(Path,'is_file',return_value=True):
   r=inspect();self.assertEqual(r['android_build'],'READY_NOT_RUN');self.assertFalse(r['device_acceptance']);self.assertEqual(r['android_install'],'NOT_RUN')
 def test_artifact_not_fabricated(self):self.assertIsNone(inspect()['apk_artifact'])
if __name__=='__main__':unittest.main()
