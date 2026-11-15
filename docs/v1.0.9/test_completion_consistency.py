"""Documentation/evidence consistency, not a replacement for measurement or release review."""
import json,re,unittest
from pathlib import Path
HERE=Path(__file__).parent;ROOT=HERE.parents[1]
class CompletionConsistency(unittest.TestCase):
 def setUp(self):self.data=json.loads((HERE/'completion-matrix.json').read_text());self.md=(HERE/'completion-matrix.md').read_text()
 def test_all_original_packages(self):self.assertEqual([r['id'] for r in self.data['rows']],['W'+str(i) for i in range(11)])
 def test_table_matches_json(self):
  actual=[l for l in self.md.splitlines() if re.match(r'\| W\d+ \|',l)]
  expected=[]
  for r in self.data['rows']:
   remaining=r['remaining_host']+r.get('scope_exclusions',[])+r['external_requirements']
   expected.append('| '+r['id']+' | **'+r['host_delivery']+'** | '+r['verified_summary']+' | '+' '.join(remaining or ['No local gap identified.'])+' |')
  self.assertEqual(actual,expected)
 def test_evidence_paths_exist(self):
  for r in self.data['rows']:
   for path in r['evidence']:
    with self.subTest(package=r['id'],path=path):self.assertTrue((ROOT/path).is_file())
 def test_release_gates_match(self):
  gates=json.loads((HERE/'release-gates.json').read_text())
  self.assertFalse(gates['release_ready']);self.assertFalse(gates['release_authorized'])
  self.assertEqual(gates['merge_assessment'],self.data['merge_assessment'])
  for row in self.data['rows']:
   gate=gates['work_packages'][row['id']]
   for key in ('host_delivery','acceptance'):self.assertEqual(gate[key],row[key])
   self.assertEqual(gate['remaining'],' '.join(row['remaining_host']+row.get('scope_exclusions',[])+row['external_requirements']))
   self.assertTrue(set(row['evidence']).issubset(gate['implementation']))
 def test_scene_inventory_and_s03_limit(self):
  coverage=json.loads((HERE/'scene-coverage.json').read_text())
  self.assertEqual([s['id'] for s in coverage['scenes']],['S%02d'%i for i in range(1,9)])
  for scene in coverage['scenes']:
   for dimension in ('correctness','quality','performance'):self.assertTrue(scene[dimension]['status'])
  s03=coverage['scenes'][2]
  self.assertEqual(s03['correctness']['status'],'PARTIAL');self.assertEqual(s03['quality']['status'],'PARTIAL')
  self.assertIn('Finite integrated UI+3D+PostFX',s03['scope'])
  self.assertIn('benchmarks/system_scenes/v109_s03/run.py',s03['implementation'])
  self.assertEqual(s03['performance']['status'],'BLOCKED_BY_HARDWARE')
 def test_release_stays_blocked(self):
  self.assertFalse(self.data['release_ready']);self.assertFalse(self.data['merge_assessment']['automatic_merge_ready']);self.assertGreaterEqual(len(self.data['merge_assessment']['release_blockers']),4)
 def test_w8_actual_collection_not_claimed_physical(self):
  r=next(r for r in self.data['rows'] if r['id']=='W8');self.assertEqual(r['remaining_host'],[]);self.assertEqual(r['acceptance'],'BLOCKED_BY_HARDWARE')
  e=json.loads((ROOT/'benchmarks/device_portability/evidence/grouped.json').read_text());self.assertEqual(e['status'],'SOFTWARE_QUALITY_ONLY');self.assertFalse(e['release_acceptance'])
 def test_end_to_end_shared_advisor_stays_blocked(self):
  for backend in ['mesa','angle']:
   e=json.loads((ROOT/f'benchmarks/workflow/evidence/{backend}/workflow-result.json').read_text())
   self.assertEqual({r['status'] for r in e['advisor_result']['candidates']},{'INSUFFICIENT_EVIDENCE','REJECTED_BY_QUALITY'});self.assertFalse(e['release_acceptance'])
if __name__=='__main__':unittest.main()
