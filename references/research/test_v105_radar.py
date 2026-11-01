import copy
import hashlib
import json
import importlib.util
from pathlib import Path
import unittest
spec=importlib.util.spec_from_file_location('radar',Path(__file__).with_name('update_radar.py'));radar=importlib.util.module_from_spec(spec);spec.loader.exec_module(radar)
class V105RadarTests(unittest.TestCase):
    def row(self):
        row={k:'declared' for k in ('source_url','author_org','hardware','driver','api_version','extension','actual_change','engineering_impact','repro_steps','decision','target_rule','test_id')}
        row.update(published_at='2026-10-27T02:09:05Z',event_at='2026-10-27T02:09:05Z',collected_at='2026-11-01T09:00:00Z',source_hash='a'*64,evidence_level='OFFICIAL_IMPLEMENTATION',window_class='in-window');return row
    def test_hash_is_stable_and_source_sensitive(self):
        r={'id':1,'html_url':'https://github.com/example','published_at':'2026-10-27T00:00:00Z','tag_name':'v1'}
        a=radar.normalize('x','releases',r);self.assertEqual(a['source_hash'],radar.normalize('x','releases',r)['source_hash'])
        r['body']='changed';self.assertNotEqual(a['source_hash'],radar.normalize('x','releases',r)['source_hash'])
    def test_historical_rejected_as_current(self):
        row=self.row();row['event_at']='2026-09-28T00:00:00Z'
        with self.assertRaises(ValueError):radar.validate_v105_evidence(row)
    def test_unknown_x_remains_unverified(self):
        row=self.row();row.update(evidence_level='UNVERIFIED',source_hash=None,source_url=None,event_at=None,published_at=None,window_class='unknown')
        self.assertEqual(radar.validate_v105_evidence(row)['evidence_level'],'UNVERIFIED')
    def test_no_automatic_must_from_release(self):
        row=self.row();row['normative_action']='MUST'
        with self.assertRaises(ValueError):radar.validate_v105_evidence(row)
    def test_missing_source_hash_blocks_verified(self):
        row=self.row();row['source_hash']=None
        with self.assertRaises(ValueError):radar.validate_v105_evidence(row)
    def test_actual_ledger_and_snapshot_hashes(self):
        root=Path(__file__).parent/'2026-11-01-v105'
        for row in json.loads((root/'source-ledger.json').read_text()):
            radar.validate_v105_evidence(row)
            if row.get('snapshot_file'):
                self.assertEqual(hashlib.sha256((root/row['snapshot_file']).read_bytes()).hexdigest(),row['snapshot_sha256'])
    def test_commit_timestamp_not_publication(self):
        row=radar.normalize('x','commits',{'sha':'a','html_url':'u','commit':{'committer':{'date':'2026-10-03T00:00:00Z'},'message':'test'}})
        self.assertIsNone(row['published_at']);self.assertEqual(row['event_time_kind'],'commit_committer_date')
if __name__=='__main__':unittest.main()
