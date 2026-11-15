import importlib.util,json,sys,unittest
from pathlib import Path
HERE=Path(__file__).resolve().parent;sys.path.insert(0,str(HERE))
spec=importlib.util.spec_from_file_location('far_analysis_test',HERE/'far_analysis.py');a=importlib.util.module_from_spec(spec);spec.loader.exec_module(a)
class FarAnalysis(unittest.TestCase):
 def test_simple_channel_split(self):
  r=a.stats([5,0,0,13],[0,0,0,12],[0]);self.assertEqual(r['max_rgb'],5);self.assertEqual(r['max_alpha'],1);self.assertEqual(r['silhouette_disagree'],1)
 def test_empty_region(self):self.assertEqual(a.stats([],[],[])['pixels'],0)
 def test_saved_complete_analysis(self):
  report=json.loads((HERE/'evidence/far-analysis.json').read_text())
  for source in report['reports']:
   self.assertEqual(a.analyze(HERE/'evidence'/source['input_report']),source)
   for view in source['views']:
    regions=view['regions'];overall=view['actual_vs_original']
    for left,right in [('foreground_roi','outside_foreground'),('far_boundary_membership_changed','far_membership_same'),('inside_far_full_support','outside_far_full_support')]:
     for key in ['pixels','over_budget_pixels','silhouette_disagree']:
      self.assertEqual(regions[left]['actual'][key]+regions[right]['actual'][key],overall[key])
    self.assertEqual(sum(p['pixels'] for p in view['nearest_phase'].values()),4096)
 def test_foreground_not_dominant(self):
  r=json.loads((HERE/'evidence/far-analysis.json').read_text())
  for source in r['reports']:
   for v in source['views']:
    self.assertEqual(v['regions']['foreground_roi']['actual']['over_budget_pixels'],0)
    self.assertGreater(v['regions']['far_membership_same']['actual']['silhouette_disagree'],v['regions']['far_boundary_membership_changed']['actual']['silhouette_disagree'])
if __name__=='__main__':unittest.main()
