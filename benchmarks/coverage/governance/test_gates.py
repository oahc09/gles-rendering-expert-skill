import copy,hashlib,json,sys,tempfile,unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[3]/'tools/coverage'))
from check_gates import check
class Gates(unittest.TestCase):
 def setUp(self):
  self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup);self.root=Path(self.tmp.name);d=self.root/'docs/v1.1.0';d.mkdir(parents=True);prior=self.root/'docs/v1.0.9/release-gates.json';prior.parent.mkdir();prior.write_text('{"release_ready":false}')
  (d/'debt-ledger.json').write_text(json.dumps({'debts':[{'path':'docs/v1.0.9/release-gates.json','sha256':hashlib.sha256(prior.read_bytes()).hexdigest(),'gate':json.loads(prior.read_text())}]}));self.g={'target_version':'1.1.0','release_ready':False,'release_authorized':False,'accepted_limitations':[],'prior_release_gate':'docs/v1.0.9/release-gates.json','work_packages':{f'W{i}':{'status':'NOT_RUN','evidence':[],'remaining':'unverified'} for i in range(13)}};self.write()
 def write(self):(self.root/'docs/v1.1.0/release-gates.json').write_text(json.dumps(self.g))
 def test_explicit_blockers_allowed(self):self.assertFalse(check(self.root)['release_ready'])
 def test_ready_override_rejected(self):
  self.g['release_ready']=True;self.write()
  with self.assertRaises(ValueError):check(self.root)
 def test_waiver_rejected(self):
  self.g['accepted_limitations']=['skip devices'];self.write()
  with self.assertRaises(ValueError):check(self.root)
 def test_missing_package_rejected(self):
  del self.g['work_packages']['W9'];self.write()
  with self.assertRaises(ValueError):check(self.root)
 def test_prior_change_rejected(self):
  (self.root/'docs/v1.0.9/release-gates.json').write_text('{"release_ready":true}')
  with self.assertRaises(ValueError):check(self.root)
 def test_missing_artifact_rejected(self):
  self.g['work_packages']['W0']['evidence']=['absent'];self.write()
  with self.assertRaises(ValueError):check(self.root)
if __name__=='__main__':unittest.main()
