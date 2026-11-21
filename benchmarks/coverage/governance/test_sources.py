import hashlib,json,sys,tempfile,unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[3]/'tools/coverage'))
from verify_sources import verify
class Sources(unittest.TestCase):
 def setUp(self):
  self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup);self.p=Path(self.tmp.name)/'manifest.json';(self.p.parent/'s').write_bytes(b'x');self.data={'sources':[{'repository':'KhronosGroup/fixture','commit':'a'*40,'url':'https://raw.githubusercontent.com/KhronosGroup/fixture/'+('a'*40)+'/x','file':'s','bytes':1,'sha256':hashlib.sha256(b'x').hexdigest()}]};self.p.write_text(json.dumps(self.data))
 def test_offline(self):self.assertEqual(verify(self.p)['status'],'PASS')
 def test_online_fixture_is_only_fixture(self):self.assertEqual(verify(self.p,True,lambda u:b'x')['status'],'PASS')
 def test_network_failure_incomplete(self):
  def fail(url):raise OSError('private-address-redacted')
  r=verify(self.p,True,fail);self.assertEqual(r['status'],'INCOMPLETE');self.assertNotIn('private-address',str(r))
 def test_bad_digest_incomplete(self):self.assertEqual(verify(self.p,True,lambda u:b'y')['status'],'INCOMPLETE')
 def test_moving_head_rejected(self):
  self.data['sources'][0]['url']='https://raw.githubusercontent.com/KhronosGroup/fixture/main/x';self.p.write_text(json.dumps(self.data));self.assertEqual(verify(self.p)['status'],'INCOMPLETE')
if __name__=='__main__':unittest.main()
