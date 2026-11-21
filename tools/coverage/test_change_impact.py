import copy,json,tempfile,unittest
from pathlib import Path
import change_impact as m
class Tests(unittest.TestCase):
 def setUp(self):
  self.root=m.ROOT;self.index=json.loads((self.root/'references/coverage/impact-index.json').read_text())
 def run_index(self):return m.analyze(self.root,self.index,'2026-11-15')
 def test_real(self):
  r=self.run_index();self.assertEqual(r['status'],'SNAPSHOT_UNCHANGED');self.assertEqual(r['subject_count'],12);self.assertEqual(len(r['unlinked_targets']),4);self.assertTrue(r['review_required']);self.assertFalse(r['adoption_allowed'])
 def test_missing_subject(self):self.index['subjects'].pop();self.assertEqual(self.run_index()['status'],'INCOMPLETE')
 def test_missing_node(self):self.index['nodes'].pop();self.assertEqual(self.run_index()['status'],'INCOMPLETE')
 def test_missing_edge(self):self.index['edges'].pop();self.assertEqual(self.run_index()['status'],'INCOMPLETE')
 def test_cycle(self):
  e=self.index['edges'][0];self.index['edges'].append({'from':e['to'],'to':e['from']});self.assertIn('cycle',self.run_index()['reason'])
 def test_path_escape(self):self.index['nodes'][0]['path']='../escape';self.assertEqual(self.run_index()['status'],'INCOMPLETE')
 def test_bad_hash(self):self.index['nodes'][0]['base_sha256']='bad';self.assertEqual(self.run_index()['status'],'INCOMPLETE')
 def changed_file(self,nodeid,rebaseline=False):
  td=tempfile.TemporaryDirectory();self.addCleanup(td.cleanup);root=Path(td.name)
  for path in {n['path'] for n in self.index['nodes'] if n['path']}|{m.LEDGER,m.RECEIPTS}|set(m.TEST_PATHS.values()):
   p=root/path;p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes((self.root/path).read_bytes())
  node=next(n for n in self.index['nodes'] if n['id']==nodeid);p=root/node['path'];p.write_text(p.read_text()+'\n')
  index=m.inventory(root) if rebaseline else self.index
  return m.analyze(root,index,'2026-11-15')
 def test_changed_input_propagates(self):
  r=self.changed_file('candidate:ANGLE_STORAGE_REBINDS:evidence:0');self.assertEqual(r['status'],'CHANGE_REVIEW_REQUIRED');self.assertIn('candidate:ANGLE_STORAGE_REBINDS:test',r['affected_targets']);self.assertFalse(r['command_execution'])
 def test_runtime_regression_selected(self):
  r=self.changed_file('runtime:timer-query-mesa:collector');self.assertIn('probe-timer',r['closed_test_ids_to_validate']);self.assertNotIn('probe-debug',r['closed_test_ids_to_validate']);self.assertNotIn('ledger-lifecycle',r['closed_test_ids_to_validate'])
 def test_test_node_change_selects_test(self):
  r=self.changed_file('candidate:ANGLE_STORAGE_REBINDS:test');self.assertIn('candidate-advanced',r['closed_test_ids_to_validate'])
 def test_non_test_target_unresolved(self):
  r=self.changed_file('candidate:ANGLE_BLEND_ATTACHMENT_TRANSITIONS:test');self.assertEqual(r['unresolved_regression_links'][0]['status'],'UNRESOLVED_NOT_A_REGISTERED_TEST')
 def test_catalog_drift_all_runtime(self):
  r=self.changed_file('registry:gles');self.assertEqual(r['status'],'CHANGE_REVIEW_REQUIRED');self.assertTrue(all('probe-'+p in r['closed_test_ids_to_validate'] for p in ['debug','timer','robust','external']))
 def test_unreviewed_rebaseline_rejected(self):
  r=self.changed_file('runtime:timer-query-mesa:collector',True);self.assertEqual(r['status'],'INCOMPLETE');self.assertIn('baseline',r['reason'])
 def test_no_command_injection(self):self.index['test_ids'].append('shell:rm');self.assertEqual(self.run_index()['status'],'INCOMPLETE')
 def test_orphan(self):self.index['edges'][0]['from']='ghost';self.assertEqual(self.run_index()['status'],'INCOMPLETE')
 def test_extra_field(self):self.index['nodes'][0]['adopt']=True;self.assertEqual(self.run_index()['status'],'INCOMPLETE')
 def fixture(self,mutate):
  td=tempfile.TemporaryDirectory();self.addCleanup(td.cleanup);root=Path(td.name)
  for path in {n['path'] for n in self.index['nodes'] if n['path']}|{m.LEDGER,m.RECEIPTS}|set(m.TEST_PATHS.values()):
   p=root/path;p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes((self.root/path).read_bytes())
  p=root/m.LEDGER;ledger=json.loads(p.read_text());mutate(ledger['rules']);p.write_text(json.dumps(ledger));return m.analyze(root,self.index,'2026-11-15')
 def test_expiry_reuses_governance(self):
  def mutate(rows):rows[0].update(workaround=True,driver_range='exact-fixed',fallback='disable',expires_at='2026-11-14')
  r=self.fixture(mutate);self.assertEqual(r['governance']['records'][0]['effective_state'],'blocked');self.assertTrue(r['review_required'])
 def test_conflict_reuses_governance(self):
  def mutate(rows):
   for i in [0,1]:rows[i].update(state='verified',reviewer='AI fixture only',reviewed_at='2026-11-14',topic='same',conditions={'same':'scope'},recommendation=str(i))
  r=self.fixture(mutate);self.assertEqual(len(r['governance']['conflicts']),1);self.assertFalse(r['adoption_allowed'])
if __name__=='__main__':unittest.main()
