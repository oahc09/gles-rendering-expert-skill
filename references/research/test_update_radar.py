"""Offline unit tests test harvesting semantics, not current-events truth."""
import datetime as dt
import importlib.util
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

spec = importlib.util.spec_from_file_location('radar', Path(__file__).with_name('update_radar.py'))
radar = importlib.util.module_from_spec(spec)
spec.loader.exec_module(radar)

class RadarTest(unittest.TestCase):
    def row(self, id='1', when='2026-10-02T00:00:00Z', **kw):
        return dict(source='fixture', id=id, event_at=when, url='https://example.invalid/'+id, **kw)
    def select(self, rows, known=set()):
        return radar.select(rows, dt.date(2026,10,2), dt.date(2026,11,1), known)
    def test_inclusive_boundaries(self):
        self.assertEqual(len(self.select([self.row(),self.row('2','2026-11-01T23:59:59Z')])),2)
    def test_outside_window(self):
        self.assertEqual(self.select([self.row(when='2026-10-01T23:59:59Z'),self.row('2','2026-11-02T00:00:00Z')]),[])
    def test_unknown_date_and_draft(self):
        self.assertEqual(self.select([self.row(when=None),self.row('2',draft=True)]),[])
    def test_dedupe_same_batch(self):
        self.assertEqual(len(self.select([self.row(),self.row()])),1)
    def test_dedupe_history(self):
        self.assertEqual(self.select([self.row()],{'fixture:1'}),[])
    def test_release_timestamp_not_created(self):
        got=radar.normalize('x','releases',dict(id=2,html_url='u',published_at='2026-10-03T00:00:00Z',created_at='2020-01-01',tag_name='v1'))
        self.assertEqual(got['event_at'],'2026-10-03T00:00:00Z')
    def test_commit_committer_timestamp(self):
        got=radar.normalize('x','commits',dict(sha='a',html_url='u',commit=dict(committer=dict(date='2026-10-03T00:00:00Z'),message='title\nbody')))
        self.assertEqual(got['title'],'title')
    def test_offline_archive_rerun_and_previous_archive(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d); inp=root/'input.json'; inp.write_text(json.dumps([self.row()]))
            cmd=[sys.executable,str(Path(radar.__file__)),'--start','2026-10-02','--end','2026-11-01','--archive',str(root),'--input',str(inp)]
            for _ in range(2):
                subprocess.run(cmd,check=True,capture_output=True)
                self.assertEqual(len(json.loads((root/'2026-11-01/radar.json').read_text())['items']),1)
            (root/'2026-10-31').mkdir(); (root/'2026-10-31/radar.json').write_text(json.dumps({'items':[self.row()]}))
            subprocess.run(cmd,check=True,capture_output=True)
            self.assertEqual(json.loads((root/'2026-11-01/radar.json').read_text())['items'],[])
    def test_reject_reversed_dates(self):
        p=subprocess.run([sys.executable,radar.__file__,'--start','2026-11-01','--end','2026-10-02'],capture_output=True)
        self.assertNotEqual(p.returncode,0)

if __name__=='__main__': unittest.main()
