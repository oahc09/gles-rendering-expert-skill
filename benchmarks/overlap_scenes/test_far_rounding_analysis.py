import importlib.util,json,sys,unittest
from pathlib import Path
HERE=Path(__file__).resolve().parent;sys.path.insert(0,str(HERE))
spec=importlib.util.spec_from_file_location('rounding_analysis',HERE/'far_rounding_analysis.py');m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
class RoundingAnalysis(unittest.TestCase):
 def test_saved_analysis_recomputes(self):
  self.assertEqual(m.analyze(HERE/'evidence'),json.loads((HERE/'evidence/far-rounding-analysis.json').read_text()))
 def test_extra_pixel_and_threshold_unchanged(self):
  r=m.analyze(HERE/'evidence');self.assertEqual(r['mismatch_counts'],{'mesa':3,'angle':2});self.assertEqual(r['silhouette_budget_unchanged'],2)
  extra=[p for p in r['points'] if p['mesa_extra']];self.assertEqual(len(extra),1);p=extra[0];self.assertEqual((p['x'],p['y']),(29,24));self.assertEqual(p['cpu_weighted_rgba'][3],12.375);self.assertEqual(p['actual']['mesa'][3],13);self.assertEqual(p['actual']['angle'][3],12)
 def test_weights_and_cpu_oracle(self):
  for p in m.analyze(HERE/'evidence')['points']:
   self.assertEqual(sum(s['weight'] for s in p['cpu_low32_samples']),1)
   self.assertEqual(p['cpu_round_half_up'],p['cpu_bilinear_own']);self.assertFalse(p['foreground_coverage'])
if __name__=='__main__':unittest.main()
