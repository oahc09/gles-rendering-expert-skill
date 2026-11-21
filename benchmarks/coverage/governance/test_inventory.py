import json,unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[3]
class Inventory(unittest.TestCase):
 def test_scenario_paths_and_limits(self):
  data=json.loads((ROOT/'references/coverage/scenario-matrix.json').read_text());self.assertEqual(len(data['scenes']),15)
  for row in data['scenes']:
   for key in ('knowledge_route','implementation'):
    if row.get(key):self.assertTrue((ROOT/row[key]).is_file())
   self.assertTrue(row['es30_fallback']);self.assertIsNone(row['performance'])
 def test_vendor_adapters_not_performance(self):
  data=json.loads((ROOT/'references/coverage/vendor-coverage.json').read_text())
  self.assertEqual(set(data['classification']),{'MUST','SHOULD','CONDITIONAL','EXPERIMENTAL'})
  for row in data['cards']:self.assertTrue((ROOT/row['reuse']).is_file());self.assertIsNone(row['measured_gain']);self.assertTrue(row['workaround_policy']['expires_at_required'])
 def test_debt_gates_unchanged(self):
  import hashlib
  data=json.loads((ROOT/'docs/v1.1.0/debt-ledger.json').read_text());self.assertGreaterEqual(len(data['debts']),7)
  for row in data['debts']:
   p=ROOT/row['path'];self.assertEqual(hashlib.sha256(p.read_bytes()).hexdigest(),row['sha256']);self.assertEqual(json.loads(p.read_text()),row['gate']);self.assertEqual(row['disposition'],'PRESERVE_NO_WAIVER')
if __name__=='__main__':unittest.main()
