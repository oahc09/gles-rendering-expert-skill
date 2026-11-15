import copy,json,unittest
from pathlib import Path
from scene_collector import quality_gate,grouped,collect
HERE=Path(__file__).parent/'evidence'
class SceneCollector(unittest.TestCase):
 def setUp(self):
  self.scene=json.loads((HERE/'mesa-software-scene.json').read_text())
  self.records=[json.loads((HERE/(b+'-record.json')).read_text()) for b in ('mesa-software','angle-software')]
 def test_archived_real_controls(self):
  q=quality_gate(self.scene);self.assertEqual([c['candidate_quality'] for c in q['cases']],['PASS','REJECTED_BY_QUALITY']);self.assertFalse(q['physical_quality_evidence'])
 def test_group_separation(self):
  r=grouped(self.records,HERE);self.assertEqual(len(r['groups']),2);self.assertFalse(r['release_acceptance']);self.assertEqual(r['performance'],'NOT_MEASURED')
 def test_same_group(self):self.assertEqual(grouped([self.records[0]]*2,HERE)['groups'][0]['capture_count'],2)
 def test_pixels_not_flags(self):
  self.scene['cases'][0]['candidate']['pixels'][0]=255
  with self.assertRaises(ValueError):quality_gate(self.scene)
 def test_negative_not_accepted(self):
  self.scene['cases'][1]['candidate']['pixels']=self.scene['cases'][1]['baseline']['pixels']
  with self.assertRaises(ValueError):quality_gate(self.scene)
 def test_shader_bindings(self):
  self.scene['cases'][0]['candidate']['passes'][0]['source_sha256']['shader.frag']='0'*64
  with self.assertRaises(ValueError):quality_gate(self.scene)
 def test_gl_error(self):
  self.scene['cases'][0]['baseline']['gl_error']=1282
  with self.assertRaises(ValueError):quality_gate(self.scene)
 def test_detached_quality(self):
  self.records[0]['quality']['status']='PASS'
  with self.assertRaises(ValueError):grouped(self.records,HERE)
 def test_detached_graph(self):
  self.records[0]['baseline_graph_sha256']='0'*64
  with self.assertRaises(ValueError):grouped(self.records,HERE)
 def test_invalid_artifacts(self):
  for key,value in [('path','../escape'),('path',str((HERE/'mesa-software-scene.json').resolve())),('sha256','0'*64)]:
   with self.subTest(key=key):
    r=copy.deepcopy(self.records);r[0]['scene'][key]=value
    with self.assertRaises(ValueError):grouped(r,HERE)
 def test_software_cannot_be_physical(self):
  self.records[0]['hardware_kind']='physical'
  with self.assertRaises(ValueError):grouped(self.records,HERE)
 def test_unknown_provider_no_execution(self):
  with self.assertRaises(ValueError):collect({},'adreno-physical','unused')
 def test_wrong_config_no_execution(self):
  with self.assertRaises(ValueError):collect({'kind':'angle'},'mesa-software','unused')
if __name__=='__main__':unittest.main()
