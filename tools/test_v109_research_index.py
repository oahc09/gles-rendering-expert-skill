import copy,gzip,json,tempfile,unittest
from pathlib import Path
import v109_research_index as m
ROOT=Path(__file__).resolve().parents[1]
SOURCE=ROOT/'docs/v1.0.9/research/rolling/2026-11-15/radar.json.gz'
RECEIPT=SOURCE.parent/'receipt.json'
class ResearchIndex(unittest.TestCase):
 def setUp(self):self.tmp=tempfile.TemporaryDirectory();self.out=Path(self.tmp.name)/'index.json.gz';m.generate(SOURCE,RECEIPT,self.out);self.receipt=self.out.with_suffix('.receipt.json')
 def tearDown(self):self.tmp.cleanup()
 def test_complete_contract(self):
  self.assertEqual(m.validate(SOURCE,RECEIPT,self.out,self.receipt)['candidate_count'],1319)
  d=json.loads(gzip.decompress(self.out.read_bytes()))
  for row in d['rows']:
   self.assertTrue(set(m.FIELDS).issubset(row));self.assertEqual(row['discovered_at'],'2026-11-15T02:37:58.234611+00:00');self.assertEqual(row['evidence_class'],'UNVERIFIED');self.assertIsNone(row['gpu'])
 def test_deterministic(self):
  before=self.out.read_bytes();note=self.receipt.read_bytes();m.generate(SOURCE,RECEIPT,self.out);self.assertEqual(before,self.out.read_bytes());self.assertEqual(note,self.receipt.read_bytes())
 def rewrite(self,mutation):
  d=json.loads(gzip.decompress(self.out.read_bytes()));mutation(d);decoded=m.canonical(d);raw=gzip.compress(decoded,mtime=0);self.out.write_bytes(raw)
  r=json.loads(self.receipt.read_text());r['archive_sha256']=m.sha(raw);r['decoded_sha256']=m.sha(decoded);self.receipt.write_bytes(m.canonical(r))
 def test_missing_field_rejected_even_rehashed(self):
  self.rewrite(lambda d:d['rows'][0].pop('repro'))
  with self.assertRaises(ValueError):m.validate(SOURCE,RECEIPT,self.out,self.receipt)
 def test_unverified_cannot_be_measured(self):
  self.rewrite(lambda d:d['rows'][0].update(evidence_class='MEASURED_ON_DEVICE',gpu='invented'))
  with self.assertRaises(ValueError):m.validate(SOURCE,RECEIPT,self.out,self.receipt)
 def test_stale_source_rejected(self):
  r=json.loads(RECEIPT.read_text());r['decoded_sha256']='0'*64
  with self.assertRaises(ValueError):m.normalized(SOURCE,r)
 def test_stale_mapping_rejected(self):
  self.rewrite(lambda d:d['rows'][0]['source_binding'].update(revision='different'))
  with self.assertRaises(ValueError):m.validate(SOURCE,RECEIPT,self.out,self.receipt)
 def test_receipt_cannot_promote(self):
  r=json.loads(self.receipt.read_text());r['performance_claim']='faster';self.receipt.write_bytes(m.canonical(r))
  with self.assertRaises(ValueError):m.validate(SOURCE,RECEIPT,self.out,self.receipt)
 def test_missing_source_field(self):
  corpus=json.loads(gzip.decompress(SOURCE.read_bytes()));corpus['items'][0].pop('event_at')
  decoded=m.canonical(corpus);raw=gzip.compress(decoded,mtime=0);p=Path(self.tmp.name)/'source.gz';p.write_bytes(raw)
  r=json.loads(RECEIPT.read_text());r.update(archive_sha256=m.sha(raw),decoded_sha256=m.sha(decoded))
  with self.assertRaises(ValueError):m.normalized(p,r)
 def test_receipt_time_not_invented(self):
  r=json.loads(self.receipt.read_text());r['discovered_at']='2026-11-01T00:00:00Z';self.receipt.write_bytes(m.canonical(r))
  with self.assertRaises(ValueError):m.validate(SOURCE,RECEIPT,self.out,self.receipt)
 def test_no_retrieval_time_invention(self):
  for value in (None,'now','2026-11-15'):
   with self.assertRaises(ValueError):m.timestamp(value)
if __name__=='__main__':unittest.main()
