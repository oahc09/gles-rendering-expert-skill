import hashlib,json,unittest
from pathlib import Path
from corpus import cases
import importlib.util
spec=importlib.util.spec_from_file_location('verify',Path(__file__).resolve().parents[3]/'tools/coverage/verify_glsl.py');verify=importlib.util.module_from_spec(spec);spec.loader.exec_module(verify)
HERE=Path(__file__).parent
class GLSLFixtures(unittest.TestCase):
 def test_contract_true_partial(self):
  r=json.loads((HERE/'evidence/angle.json').read_text());self.assertTrue(verify.contract_valid(r))
 def test_unexpected_failure_not_suppressed(self):
  r=json.loads((HERE/'evidence/angle.json').read_text());r['rows'][0]['compiler_accept']=False;self.assertFalse(verify.contract_valid(r))
 def test_fake_unsupported_denied(self):
  r=json.loads((HERE/'evidence/angle.json').read_text());r['rows'][0]['status']='NOT_SUPPORTED';r['rows'][0]['runtime_status']='NOT_SUPPORTED_GLES32';self.assertFalse(verify.contract_valid(r))
 def test_gles32_cannot_skip(self):
  r=json.loads((HERE/'evidence/angle.json').read_text());r['supports_gles32']=True;self.assertFalse(verify.contract_valid(r))
 def test_family_pairs(self):
  rows=cases();families={x['family'] for x in rows};self.assertEqual(len(families),16)
  for f in families:self.assertEqual({x['expected'] for x in rows if x['family']==f},{True,False})
 def test_ids(self):self.assertEqual(len({x['id'] for x in cases()}),32)
 def test_fixtures_match(self):
  for r in cases():
   for name,src in r['sources'].items():self.assertEqual((HERE/'fixtures'/r['id']/name).read_text(),src+'\n')
 def test_actual_mesa_evidence(self):
  r=json.loads((HERE/'evidence/mesa.json').read_text());self.assertEqual(r['status'],'HOST_PASS');self.assertEqual(len(r['rows']),32)
 def test_angle_unsupported_not_pass(self):
  r=json.loads((HERE/'evidence/angle.json').read_text());self.assertEqual(r['status'],'PARTIAL');self.assertEqual(sum(x['status']=='NOT_SUPPORTED' for x in r['rows']),4)
 def test_source_hashes(self):
  for driver in ('mesa','angle'):
   rows={x['id']:x for x in json.loads((HERE/'evidence'/f'{driver}.json').read_text())['rows']}
   for c in cases():self.assertEqual(rows[c['id']]['source_sha256'],{k:hashlib.sha256(v.encode()).hexdigest() for k,v in c['sources'].items()})
 def test_negative_link_control(self):
  r=json.loads((HERE/'evidence/mesa.json').read_text());x=next(x for x in r['rows'] if x['id']=='varying-interface-negative');self.assertTrue(x['runtime_compile']);self.assertFalse(x['runtime_link'])
if __name__=='__main__':unittest.main()
