import copy,json,struct,unittest
from pathlib import Path
from test_ktx2_container import valid
from ktx2_container import parse
from quality_gate import evaluate
HERE=Path(__file__).parent
class HostileContainers(unittest.TestCase):
 def test_budget_and_integer_ranges(self):
  with self.assertRaises(ValueError):parse(valid()+bytes(16*1024*1024))
  for offset,fmt,values in [(20,'I',[2049,0xffffffff]),(24,'I',[0,2049,0xffffffff]),(40,'I',[0,2,0xffffffff]),(44,'I',[1,2,3,0xffffffff]),(48,'I',[0,103,105,0xffffffff]),(80,'Q',[0,104,197,2**64-1]),(88,'Q',[0,3,5,2**64-1]),(96,'Q',[0,3,5,2**64-1])]:
   for value in values:
    d=valid();struct.pack_into('<'+fmt,d,offset,value)
    with self.subTest(offset=offset,value=value),self.assertRaises(ValueError):parse(d)
 def test_dfd_samples(self):
  for offset,value in [(132,255),(134,255),(135,8),(136,1),(140,1),(144,0),(115,2),(117,12)]:
   d=valid();d[offset]=value
   with self.subTest(offset=offset),self.assertRaises(ValueError):parse(d)
 def test_metadata(self):
  def container(entries):
   d=valid();payload=d[-4:];d=d[:-4];raw=b''
   for entry in entries:
    raw+=struct.pack('<I',len(entry))+entry+bytes((-len(entry))%4)
   struct.pack_into('<II',d,56,196,len(raw));struct.pack_into('<Q',d,80,196+len(raw));return d+raw+payload
  self.assertEqual(parse(container([b'KTXorientation\0rd\0']))['mode'],'rgba')
  for entries in [[b'KTXorientation\0ru\0'],[b'KTXswizzle\0bgra\0'],[b'\0v'],[b'nonul'],[b'\xff\0x'],[b'x\0a',b'x\0b'],[b'KTXunknownSemantic\0x']]:
   with self.subTest(entries=entries),self.assertRaises(ValueError):parse(container(entries))
 def test_every_short_truncation(self):
  for n in range(len(valid())):
   with self.subTest(n=n),self.assertRaises(ValueError):parse(valid()[:n])
class QualityIntegration(unittest.TestCase):
 def report(self,name):return json.loads((HERE/'evidence'/name).read_text())
 def test_real_saved_steep_never_accepted(self):
  for driver in ['mesa','angle']:
   r=self.report('ktx2-steep-'+driver+'.json');g=evaluate(r['experiments'],r['source_golden_rgba'],'steep')
   self.assertEqual(g['harness_status'],'HOST_PASS');self.assertFalse(g['verified_improvement'])
   self.assertTrue(all(d['optimization_status']=='REJECTED_BY_QUALITY' for d in g['decisions']))
 def test_real_saved_smooth_is_not_performance_proof(self):
  r=self.report('ktx2-mesa.json');g=evaluate(r['experiments'],r['source_golden_rgba'],'smooth')
  self.assertFalse(g['verified_improvement']);self.assertTrue(all(d['optimization_status']=='INSUFFICIENT_EVIDENCE' for d in g['decisions']))
 def test_missing_or_duplicate_branches(self):
  r=self.report('ktx2-mesa.json')
  for rows in [[],r['experiments'][:1],r['experiments']+[r['experiments'][0]]]:
   with self.assertRaises(ValueError):evaluate(rows,r['source_golden_rgba'],'smooth')
 def test_forged_quality_rejected(self):
  r=self.report('ktx2-steep-mesa.json')
  for field,value in [('quality','PASS'),('quality_budget',255),('cpu_oracle_max_error',0),('gl_error',1282),('compile',False),('pixels',[float('nan')]*64),('pixels',[0]*63)]:
   rows=copy.deepcopy(r['experiments']);rows[0][field]=value
   with self.subTest(field=field),self.assertRaises(ValueError):evaluate(rows,r['source_golden_rgba'],'steep')
 def test_cross_pattern_cannot_pass(self):
  r=self.report('ktx2-steep-mesa.json');self.assertEqual(evaluate(r['experiments'],r['source_golden_rgba'],'smooth')['harness_status'],'FAIL')
if __name__=='__main__':unittest.main()
