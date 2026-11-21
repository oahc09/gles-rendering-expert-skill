import copy,hashlib,sys,tempfile,unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[3]/'tools/coverage'))
from lifecycle import validate,transition
class Governance(unittest.TestCase):
 def setUp(self):
  self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup);self.root=Path(self.tmp.name);(self.root/'e').write_text('evidence');self.r={'id':'r','state':'new','level':'CONDITIONAL','source_url':'https://example.org/spec','claim':'conditional','conditions':{'driver':'exact'},'topic':'blend','recommendation':'off','evidence':[]}
 def check(self,r=None):return validate([r or self.r],self.root,'2026-11-15')
 def verified(self):return {**self.r,'state':'verified','reviewer':'independent','reviewed_at':'2026-11-14','evidence':[{'path':'e','sha256':hashlib.sha256(b'evidence').hexdigest()}]}
 def test_new_not_accepted(self):self.assertFalse(self.check()['release_acceptance'])
 def test_schedule_never_started(self):self.assertFalse(self.check()['schedule_activated'])
 def test_must_not_vendor(self):
  with self.assertRaises(ValueError):self.check({**self.r,'level':'MUST'})
 def test_missing_review(self):
  with self.assertRaises(ValueError):self.check({**self.r,'state':'verified'})
 def test_real_file_binding(self):self.assertEqual(self.check(self.verified())['status'],'CONSISTENT')
 def test_stale_binding(self):
  r=self.verified();(self.root/'e').write_text('changed')
  with self.assertRaises(ValueError):self.check(r)
 def test_expiry_forces_fallback(self):
  r={**self.verified(),'workaround':True,'driver_range':'exact-1.2','expires_at':'2026-11-14','fallback':'disable'}
  self.assertEqual(self.check(r)['records'][0]['effective_state'],'blocked')
 def test_workaround_cannot_be_broad(self):
  with self.assertRaises(ValueError):self.check({**self.r,'workaround':True})
 def test_no_software_gain(self):
  with self.assertRaises(ValueError):self.check({**self.r,'measured_gain':0.1,'evidence_class':'SOFTWARE'})
 def test_adopted_needs_chain(self):
  with self.assertRaises(ValueError):self.check({**self.verified(),'state':'adopted'})
 def test_conflict_no_auto_winner(self):
  a=self.verified();b={**a,'id':'b','recommendation':'on'};self.assertEqual(len(validate([a,b],self.root,'2026-11-15')['conflicts']),1)
 def test_transition_requires_review(self):
  with self.assertRaises(ValueError):transition(self.r,'verified',{})
 def test_no_new_to_adopted(self):
  with self.assertRaises(ValueError):transition(self.r,'adopted',{'reviewer':'x','reason':'y','reviewed_at':'2026-11-15'})
 def test_future_review_rejected(self):
  with self.assertRaises(ValueError):self.check({**self.verified(),'reviewed_at':'2026-12-01'})
 def test_superseded_target_exists(self):
  with self.assertRaises(ValueError):self.check({**self.r,'state':'superseded','superseded_by':'absent'})
 def test_supersession_cycle_rejected(self):
  a={**self.r,'state':'superseded','superseded_by':'b'};b={**a,'id':'b','superseded_by':'r'}
  with self.assertRaises(ValueError):validate([a,b],self.root,'2026-11-15')
 def test_physical_label_not_gain_certification(self):
  with self.assertRaises(ValueError):self.check({**self.r,'measured_gain':0.1,'evidence_class':'PHYSICAL_DEVICE'})
if __name__=='__main__':unittest.main()
