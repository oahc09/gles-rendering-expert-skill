import copy
import datetime as dt
import hashlib
import json
from pathlib import Path
import unittest
import update_radar as radar

ROOT = Path(__file__).resolve().parents[2]
DIR = ROOT / 'references/research/2026-11-02-v107'

class Radar107(unittest.TestCase):
    def setUp(self): self.rows=json.loads((DIR/'decisions.json').read_text())
    def test_real_decisions_and_sources(self):
        self.assertTrue({'accepted','deferred','rejected'} <= {r['stage'] for r in self.rows})
        for row in self.rows:
            radar.validate_v107_evidence(row)
            if row.get('source_sha256'):
                self.assertEqual(hashlib.sha256((ROOT/row['source_evidence']).read_bytes()).hexdigest(),row['source_sha256'])
    def test_90_day_inclusive_boundary(self):
        self.assertEqual((dt.date(2026,11,2)-dt.date(2026,8,5)).days+1,90)
        row=copy.deepcopy(self.rows[0]);row['event_at']='2026-08-04T23:59:59Z'
        with self.assertRaises(ValueError):radar.validate_v107_evidence(row)
        row['event_at']='2026-08-05T00:00:00Z';radar.validate_v107_evidence(row)
    def test_verified_title_is_not_reproduction(self):
        row=copy.deepcopy(self.rows[0]);row['evidence_state']='VERIFIED_SOURCE'
        with self.assertRaises(ValueError):radar.validate_v107_evidence(row)
    def test_accepted_needs_test_and_reproduction(self):
        for field in ('test_ids','reproduction_evidence','source_sha256'):
            row=copy.deepcopy(self.rows[0]);row[field]=None
            with self.assertRaises(ValueError):radar.validate_v107_evidence(row)
    def test_unknown_date_cannot_be_recent(self):
        row=copy.deepcopy(self.rows[-1]);row['window_class']='in-window'
        with self.assertRaises(ValueError):radar.validate_v107_evidence(row)
    def test_no_fabricated_performance(self):
        row=copy.deepcopy(self.rows[0]);row['performance_status']='PASS'
        with self.assertRaises(ValueError):radar.validate_v107_evidence(row)
    def test_new_sources_use_existing_collector(self):
        self.assertEqual(radar.SOURCES['filament-commits'],('google/filament','commits'))
        self.assertEqual(radar.SOURCES['spirv-tools'],('KhronosGroup/SPIRV-Tools','releases'))

if __name__ == '__main__': unittest.main()
