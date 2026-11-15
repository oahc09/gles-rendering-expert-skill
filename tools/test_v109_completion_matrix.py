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
  for k in ('W2','W3','W4','W6','W10'):
   self.assertEqual(rows[k]['acceptance'],'PARTIAL_HOST_SCOPE');self.assertTrue(rows[k]['remaining_host'])
  self.assertEqual(rows['W8']['acceptance'],'BLOCKED_BY_HARDWARE');self.assertEqual(rows['W9']['acceptance'],'BLOCKED_BY_PROVIDER')
