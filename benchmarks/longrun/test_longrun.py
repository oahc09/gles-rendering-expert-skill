import copy,json,math,unittest,hashlib,tempfile
from pathlib import Path
from analyze import analyze,validate,percentile,bind_power_artifact
ROOT=Path(__file__).parent
class LongRunTests(unittest.TestCase):
 def fixture(self,name='thermal'):return json.loads((ROOT/'fixtures'/f'{name}.json').read_text())
 def device_fixture(self):
  d=self.fixture();d.update(provenance='device_capture',status='COMPLETE',actual_wall_duration_s=600,raw_trace_sha256='a'*64)
  d['device'].update(device='synthetic test only',soc='test',gpu='test',driver='test',os='test',api='GLES3',power_mode='test battery')
  return d
 def test_three_hypotheses_and_negative_controls(self):
  for p in (ROOT/'fixtures').glob('*.json'):
   d=json.loads(p.read_text());self.assertEqual(analyze(d)['hypotheses'],d['expected_hypotheses'])
 def test_synthetic_not_wall_time(self):
  d=self.fixture('bandwidth');r=analyze(d);self.assertEqual(r['observed_duration_s'],1800);self.assertIsNone(r['actual_wall_duration_s']);self.assertEqual(r['evidence_level'],'synthetic_fixture')
 def test_no_power_inferred(self):
  r=analyze(self.fixture());self.assertIsNone(r['power_mw']);self.assertIsNone(r['energy_saving_percent'])
 def test_percentile_interpolates(self):self.assertEqual(percentile([0,10],.9),9)
 def test_empty_fails(self):
  d=self.fixture();d['samples']=[]
  with self.assertRaises(ValueError):analyze(d)
 def test_nan_fails(self):
  d=self.fixture();d['samples'][0]['frame_ms']=math.nan
  with self.assertRaises(ValueError):analyze(d)
 def test_duplicate_timestamp_fails(self):
  d=self.fixture();d['samples'][1]['t_s']=0
  with self.assertRaises(ValueError):analyze(d)
 def test_negative_duration_fails(self):
  d=self.fixture();d['samples'][0]['frame_ms']=-1
  with self.assertRaises(ValueError):analyze(d)
 def test_unknown_backend_fails(self):
  d=self.fixture();d['device']['backend']='native_vulkan_gles'
  with self.assertRaises(ValueError):analyze(d)
 def test_clock_missing_fails(self):
  d=self.fixture();del d['clock']
  with self.assertRaises(ValueError):analyze(d)
 def test_budget_required(self):
  d=self.fixture();d['samples'][0]['budget_ms']=0
  with self.assertRaises(ValueError):analyze(d)
 def test_background_excluded(self):
  d=self.fixture('unknown');d['samples'][0].update(foreground=False,frame_ms=1000);self.assertLess(analyze(d)['frame_ms_distribution']['p99'],20)
 def test_configuration_segmentation(self):
  r=analyze(self.fixture('configuration_change'));self.assertEqual(r['hypotheses'],[]);self.assertGreaterEqual(len(r['segments']),4)
 def test_incomplete_does_not_guess(self):
  r=analyze(self.fixture('unknown'));self.assertEqual(r['status'],'INSUFFICIENT_EVIDENCE');self.assertIn('gpu_hz',r['missing'])
 def test_iteration_not_frames(self):
  d=self.fixture('unknown')
  for s in d['samples']:s.update(iteration_ms=s.pop('frame_ms'),budget_ms=None)
  r=analyze(d);self.assertIsNone(r['frame_ms_distribution']);self.assertIsNone(r['sampled_jank_ratio']);self.assertIsNotNone(r['iteration_ms_distribution'])
 def test_correlation_not_causal(self):self.assertEqual(analyze(self.fixture())['status'],'INFERRED_HYPOTHESES_NOT_CAUSAL_PROOF')
 def test_false_thermal_without_frequency(self):
  d=self.fixture()
  for s in d['samples']:s['gpu_hz']=None
  self.assertEqual(analyze(d)['hypotheses'],[])
 def test_bandwidth_no_counter_no_diagnosis(self):
  d=self.fixture('bandwidth')
  for s in d['samples']:s['bandwidth_utilization']=None
  self.assertEqual(analyze(d)['hypotheses'],[])
 def test_power_metadata_without_raw_is_not_measurement(self):
  d=self.device_fixture();d['power_source']={'kind':'calibrated_instrument','units':'mW','raw_sha256':'a'*64}
  for r in d['samples']:r['power_mw']=500
  self.assertIsNone(analyze(d)['power_mw'])
 def test_power_raw_binding_and_mismatch(self):
  d=self.device_fixture()
  for r in d['samples']:r['power_mw']=500
  raw=json.dumps({'units':'mW','instrument_id':'synthetic test only','calibration_reference':'test-record','samples':[{'t_s':r['t_s'],'power_mw':500} for r in d['samples']]}).encode()
  d['power_source']={'kind':'calibrated_instrument','units':'mW','raw_sha256':hashlib.sha256(raw).hexdigest()}
  with tempfile.TemporaryDirectory() as folder:
   p=Path(folder)/'power.json';p.write_bytes(raw);e=bind_power_artifact(d,p);self.assertEqual(analyze(d,e)['power_mw']['mean'],500)
   d['samples'][0]['power_mw']=501
   with self.assertRaises(ValueError):bind_power_artifact(d,p)
 def test_synthetic_power_never_device(self):
  d=self.fixture();d['power_source']={'kind':'calibrated_instrument','units':'mW','raw_sha256':'a'*64}
  for r in d['samples']:r['power_mw']=500
  self.assertIsNone(analyze(d,{'validated_raw_sha256':'a'*64})['power_mw'])
 def test_configuration_global_slope_unknown(self):self.assertIsNone(analyze(self.fixture('configuration_change'))['frame_slope_ms_per_min'])
 def test_device_missing_identity_rejected(self):
  d=self.device_fixture();d['device']['gpu']=None
  with self.assertRaises(ValueError):analyze(d)
 def test_failed_device_rejected(self):
  d=self.device_fixture();d['status']='FAILED'
  with self.assertRaises(ValueError):analyze(d)
 def test_incomplete_device_rejected(self):
  d=self.device_fixture();d['actual_wall_duration_s']=30
  with self.assertRaises(ValueError):analyze(d)
 def test_running_cannot_infer(self):
  d=self.fixture();d['status']='RUNNING';r=analyze(d);self.assertEqual(r['status'],'INCOMPLETE_CAPTURE');self.assertEqual(r['hypotheses'],[])
if __name__=='__main__':unittest.main()
