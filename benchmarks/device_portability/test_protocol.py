import copy, hashlib, json, tempfile, unittest
from pathlib import Path
from protocol import summarize, IDENTITY
class ProtocolTests(unittest.TestCase):
 def setUp(self):
  self.tmp=tempfile.TemporaryDirectory();self.root=Path(self.tmp.name);(self.root/'trace').write_bytes(b'synthetic fixture, not GPU data')
  self.r={'schema_version':1,'device':{k:'fixture' for k in IDENTITY},'hardware_kind':'physical','warmup_frames':60,'quality_pass':True,'workload_id':'fixture','baseline_sha':'a','candidate_sha':'b','trace':{'path':'trace','sha256':hashlib.sha256((self.root/'trace').read_bytes()).hexdigest()},'runs':[{'variant':'AB'[i%2],'gpu_ms':[10+i%2]*30,'timer_disjoint':False,'clock_domain':'gpu_elapsed','thermal_state':'stable','frequency_state':'locked','temperature_c':35} for i in range(8)]}
 def tearDown(self):self.tmp.cleanup()
 def test_fixture_never_accepts_hardware(self):
  x=summarize(self.r,self.root);self.assertFalse(x['release_acceptance']);self.assertEqual(x['paired_delta_ms'],[-1]*4)
 def test_reject_mutations(self):
  for field,value in [('hardware_kind','software'),('quality_pass',False),('warmup_frames',0),('runs',[])]:
   with self.subTest(field=field):
    r=copy.deepcopy(self.r);r[field]=value
    with self.assertRaises(ValueError):summarize(r,self.root)
 def test_run_failures(self):
  for field,value in [('gpu_ms',[float('nan')]*30),('gpu_ms',[0]*30),('timer_disjoint',True),('clock_domain','cpu'),('thermal_state','hot'),('temperature_c',float('inf')),('variant','B')]:
   with self.subTest(field=field,value=value):
    r=copy.deepcopy(self.r);r['runs'][0][field]=value
    with self.assertRaises(ValueError):summarize(r,self.root)
 def test_hash(self):
  self.r['trace']['sha256']='0'*64
  with self.assertRaises(ValueError):summarize(self.r,self.root)
 def test_path_escape(self):
  self.r['trace']['path']='../other'
  with self.assertRaises(ValueError):summarize(self.r,self.root)
 def test_thermal_drift(self):
  self.r['runs'][0]['temperature_c']=38
  with self.assertRaises(ValueError):summarize(self.r,self.root)
