import importlib.util,json,unittest
from pathlib import Path
HERE=Path(__file__).parent
spec=importlib.util.spec_from_file_location('s03_test_runtime',HERE/'run.py');s=importlib.util.module_from_spec(spec);spec.loader.exec_module(s)
class S03(unittest.TestCase):
 def test_oracle_depth(self):
  good=s.oracle(0)['scene'];bad=s.oracle(0,'bad_depth')['scene'];i=(3*8+3)*4
  self.assertEqual(good[i:i+4],[0,255,0,255]);self.assertEqual(bad[i:i+4],[255,0,0,255])
 def test_ui_alpha(self):
  i=(6*8+3)*4
  self.assertEqual(s.oracle(0)['scene'][i:i+4],[128,0,128,255])
  self.assertEqual(s.oracle(0,'bad_ui')['scene'][i:i+4],[0,0,255,255])
 def test_postfx_not_copy(self):
  r=s.oracle(0);i=(1*8+1)*4;self.assertEqual(r['scene'][i:i+4],[255,0,0,255]);self.assertEqual(r['screen'][i:i+4],[0,0,255,255])
 def test_equivalent(self):
  for camera in [-1,0,1]:self.assertEqual(s.oracle(camera),s.oracle(camera,'equivalent'))
 def test_camera_changes_geometry_not_ui(self):
  self.assertNotEqual(s.oracle(-1)['scene'],s.oracle(1)['scene'])
  self.assertEqual(s.oracle(-1)['scene'][-32:],s.oracle(1)['scene'][-32:])
 def test_half_rejects_all_cameras(self):
  for camera in [-1,0,1]:self.assertGreater(s.error(s.oracle(camera,'half')['screen'],s.oracle(camera)['screen']),1)
 def test_bad_input_refused(self):
  h=object.__new__(s.Host)
  for camera,variant in [(3,'baseline'),(0,'unknown')]:
   with self.assertRaises(ValueError):h.render(camera,variant)
 def test_actual_reports(self):
  for driver in ('mesa','angle'):
   r=json.loads((HERE/'evidence'/f'{driver}.json').read_text());self.assertEqual(r['status'],'HOST_PASS');self.assertFalse(r['release_acceptance']);self.assertEqual(len(r['rows']),15);self.assertTrue(r['global_baseline_valid'])
   self.assertEqual([d['quality_selection'] for d in r['global_decisions']],['baseline','equivalent','baseline','baseline','baseline']);self.assertEqual({d['production_selection'] for d in r['global_decisions']},{'baseline'})
   self.assertEqual(sum(x['capture']['draws'] for x in r['rows']),75);self.assertEqual(sum(x['capture']['readbacks'] for x in r['rows']),45)
   for row in r['rows']:
    c=row['capture'];own=s.oracle(c['camera'],c['variant']);self.assertEqual(set(c['pixels']),{'scene','postfx','screen'})
    self.assertEqual(row['cpu_max_errors'],{k:s.error(c['pixels'][k],own[k]) for k in own});self.assertLessEqual(max(row['cpu_max_errors'].values()),1)
    self.assertEqual(c['gl_error'],0);self.assertEqual(c['render_target_sequence'],['scene','postfx','screen']);self.assertEqual(len(c['attachment_events']),6)
    expected='PASS' if c['variant'] in ('baseline','equivalent') else 'REJECTED_BY_QUALITY'
    self.assertEqual(row['quality'],expected);self.assertEqual(row['target_max_error'],s.error(c['pixels']['screen'],s.oracle(c['camera'])['screen']))
 def test_bad_pixels(self):
  for p in ([True],[-1],[256]):
   with self.assertRaises(ValueError):s.error(p,[0])
if __name__=='__main__':unittest.main()
