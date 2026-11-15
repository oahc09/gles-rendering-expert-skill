import copy,importlib.util,json,tempfile,unittest
from pathlib import Path
from unittest.mock import patch
HERE=Path(__file__).parent
spec=importlib.util.spec_from_file_location('finite_workflow',HERE/'run.py');w=importlib.util.module_from_spec(spec);spec.loader.exec_module(w)
class Workflow(unittest.TestCase):
 def setUp(self):self.request=json.loads((HERE/'request.json').read_text())
 def test_descriptor_fingerprint_unknown_not_fabricated(self):
  fp=w.preflight(self.request);self.assertEqual(fp['labels'],['UNKNOWN']);self.assertEqual(fp['performance_improvement'],'NOT_MEASURED')
 def test_unknown_experiment(self):
  self.request['experiment_id']='python3 arbitrary.py'
  with self.assertRaises(ValueError):w.preflight(self.request)
 def test_extra_command_rejected(self):
  for key in ('command','argv','code','config'):
   r=copy.deepcopy(self.request);r[key]='arbitrary'
   with self.subTest(key=key),self.assertRaises(ValueError):w.preflight(r)
 def test_mismatched_scene(self):
  for key,value in [('resolution',[64,64]),('provenance','real-export'),('workload_id','other'),('metrics',{}),('trace_available','yes')]:
   r=copy.deepcopy(self.request);r['workload'][key]=value
   with self.subTest(key=key),self.assertRaises(ValueError):w.preflight(r)
 def test_reject_before_dispatch(self):
  with patch.dict(w.REGISTRY,{w.EXPERIMENT:lambda *args: self.fail('executed invalid request')}):
   self.request['command']='unsafe'
   with self.assertRaises(ValueError):w.run(self.request,{},'mesa-software','unused')
 def test_physical_provider_blocked(self):
  with self.assertRaises(ValueError):w.run(self.request,{},'adreno-physical','unused')
 def test_cost_derived_from_actual_graph(self):
  r=w.collector.scene.transform(w.collector.scene.baseline());a=w.cost(r['fallback']);b=w.cost(r['candidate'])
  self.assertGreater(a['logical_upper_bytes'],b['logical_upper_bytes']);self.assertIsNone(a['dram_bytes']);self.assertEqual(a['status'],'ESTIMATE_ONLY')
 def test_actual_archived_results(self):
  for driver in ('mesa','angle'):
   root=HERE/'evidence'/driver;r=json.loads((root/'workflow-result.json').read_text())
   self.assertEqual(r['status'],'HOST_WORKFLOW_PASS');self.assertFalse(r['release_acceptance'])
   self.assertEqual(r['performance_improvement'],'NOT_VERIFIED')
   self.assertEqual([x['candidate_quality'] for x in r['decisions']],['PASS','REJECTED_BY_QUALITY'])
   self.assertEqual([x['performance_state'] for x in r['decisions']],['INSUFFICIENT_EVIDENCE','REJECTED_BY_QUALITY'])
   self.assertEqual([x['production_selection'] for x in r['decisions']],['baseline','baseline'])
   self.assertEqual(w.collector.grouped([r['executed_capture']],root),r['grouped_quality'])
 def test_actual_advisor_recomputed(self):
  for driver in ('mesa','angle'):
   root=HERE/'evidence'/driver;r=json.loads((root/'workflow-result.json').read_text())
   self.assertEqual(w.advise({'workload':self.request['workload'],'candidates':r['advisor_input_candidates']},root),r['advisor_result'])
   self.assertIsNotNone(r['advisor_result']['candidates'][0]['experiment_binding'])
 def test_corrupt_archived_bytes_rejected(self):
  r=json.loads((HERE/'evidence/mesa/workflow-result.json').read_text())
  with tempfile.TemporaryDirectory() as td:
   root=Path(td);(root/r['executed_capture']['scene']['path']).write_text('{}')
   with self.assertRaises(ValueError):w.collector.grouped([r['executed_capture']],root)
if __name__=='__main__':unittest.main()
