import json,unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
class CompletionMatrix(unittest.TestCase):
 def test_plan_rows_and_paths(self):
  d=json.loads((ROOT/'docs/v1.0.9/completion-matrix.json').read_text())
  self.assertIs(d['release_ready'],False);self.assertTrue((ROOT/d['plan']).is_file())
  self.assertEqual([r['id'] for r in d['rows']],[f'W{i}' for i in range(11)])
  for row in d['rows']:
   self.assertTrue(row['external_requirements'])
   for p in row['evidence']:self.assertTrue((ROOT/p).is_file(),p)
 def test_no_host_gap_hidden_as_hardware(self):
  rows={r['id']:r for r in json.loads((ROOT/'docs/v1.0.9/completion-matrix.json').read_text())['rows']}
  for k in ('W4','W10'):
   self.assertEqual(rows[k]['acceptance'],'PARTIAL_HOST_SCOPE');self.assertTrue(rows[k]['remaining_host'])
  # Closed local gaps must carry executable evidence, bounded scope and separate
  # external requirements, not disappear into a generic hardware status.
  for k,acceptance,required in (
   ('W3','BOUNDED_SHADER_CONTRACT_DELIVERED',['benchmarks/shader_ab/counterexamples.py','benchmarks/shader_ab/variant_trace.py','benchmarks/interleaved_capture/run.py']),
   ('W6','BOUNDED_TEXTURE_CHAIN_DELIVERED',['benchmarks/compressed_streaming/run.py','benchmarks/texture_streaming/progressive.py'])):
   self.assertEqual(rows[k]['acceptance'],acceptance)
   self.assertEqual(rows[k]['host_delivery'],'MET_BOUNDED')
   self.assertTrue(rows[k]['scope_exclusions']);self.assertTrue(rows[k]['external_requirements'])
   for evidence in required:self.assertIn(evidence,rows[k]['evidence']);self.assertTrue((ROOT/evidence).is_file())
  self.assertEqual(rows['W8']['acceptance'],'BLOCKED_BY_HARDWARE');self.assertEqual(rows['W9']['acceptance'],'BLOCKED_BY_PROVIDER')

 def test_bounded_models_not_general_proof(self):
  rows={r['id']:r for r in json.loads((ROOT/'docs/v1.0.9/completion-matrix.json').read_text())['rows']}
  self.assertEqual(rows['W2']['acceptance'],'BOUNDED_LIFECYCLE_MODEL')
  self.assertEqual(rows['W5']['acceptance'],'BOUNDED_REPLAY_AND_SYNC_CHECK')
