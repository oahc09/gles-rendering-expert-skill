"""Review bookkeeping must not promote release metadata into a reproduced GPU claim."""
import json,unittest,gzip,hashlib,datetime
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
class ReviewTests(unittest.TestCase):
 def test_selected_release_contract(self):
  data=json.loads((ROOT/'docs/v1.0.9/research/release-review.json').read_text());self.assertEqual(len(data['rows']),6)
  for r in data['rows']:
   self.assertTrue(r['source_url'].startswith('https://github.com/'))
   self.assertEqual(len(r['source_body_sha256']),64)
   self.assertEqual(r['reviewer_type'],'AI_SOURCE_REVIEW')
   self.assertEqual(r['independent_human_review'],'NOT_RUN')
   self.assertEqual(r['performance_status'],'NOT_MEASURED')
   self.assertEqual(r['rule_promotion'],'NONE')
   self.assertEqual(r['reproduction'],'NOT_RUN_FOR_UPSTREAM_CHANGE')
   self.assertTrue((ROOT/r['experiment']).is_file());self.assertTrue((ROOT/r['test']).is_file())
 def test_empty_notes_deferred(self):
  data=json.loads((ROOT/'docs/v1.0.9/research/release-review.json').read_text())
  rows=[r for r in data['rows'] if not r['source_body_present']];self.assertEqual(len(rows),1)
  self.assertEqual(rows[0]['evidence_class'],'UNVERIFIED');self.assertTrue(rows[0]['decision'].startswith('DEFER'))

 def test_radar_archive_hashes_and_counts(self):
  root=ROOT/'docs/v1.0.9/research/rolling/2026-11-15'
  receipt=json.loads((root/'receipt.json').read_text());raw=(root/receipt['archive']).read_bytes();decoded=gzip.decompress(raw)
  self.assertEqual(hashlib.sha256(raw).hexdigest(),receipt['archive_sha256'])
  self.assertEqual(hashlib.sha256(decoded).hexdigest(),receipt['decoded_sha256'])
  data=json.loads(decoded);self.assertEqual(len(data['items']),receipt['candidate_count'])
  self.assertEqual(len({(r['source'],r['id']) for r in data['items']}),len(data['items']))
  self.assertEqual(data['status'],'REVIEW_REQUIRED');self.assertEqual(data['review_decisions'],[])
  start=datetime.date.fromisoformat(data['start']);end=datetime.date.fromisoformat(data['end'])
  self.assertEqual((end-start).days+1,90)
  for row in data['items']:
   day=datetime.datetime.fromisoformat(row['event_at'].replace('Z','+00:00')).astimezone(datetime.timezone.utc).date()
   self.assertTrue(start<=day<=end)
