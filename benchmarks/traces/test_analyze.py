import copy
import hashlib
import json
from pathlib import Path
import tempfile
import unittest
from analyze import analyze

HERE=Path(__file__).parent
class TraceTests(unittest.TestCase):
    def test_twelve_labeled_synthetic_fixtures(self):
        index=json.loads((HERE/'fixtures/index.json').read_text())
        self.assertEqual(len(index),12)
        for row in index:
            with self.subTest(row['id']):
                p=HERE/'fixtures'/row['manifest']; result=analyze(json.loads(p.read_text()),p.parent)
                self.assertEqual([h['category'] for h in result['hypotheses']],row['expected_hypotheses'])
                self.assertEqual(result['performance_improvement'],'NOT_MEASURED')
    def probe(self,change=None,raw=None):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d);m=json.loads((HERE/'fixtures/T01/trace-manifest.json').read_text());b=(HERE/'fixtures/T01/metrics.json').read_bytes()
            if raw is not None:b=json.dumps(raw).encode()
            (root/'metrics.json').write_bytes(b);m['raw_artifacts'][0]['sha256']=hashlib.sha256(b).hexdigest()
            if change:change(m)
            return analyze(m,root)
    def test_hash_mismatch(self):
        with self.assertRaises(ValueError):self.probe(lambda m:m['raw_artifacts'][0].update(sha256='0'*64))
    def test_path_escape(self):
        with self.assertRaises(ValueError):self.probe(lambda m:m['raw_artifacts'][0].update(path='../outside.json'))
    def test_units_mismatch(self):
        with self.assertRaises(ValueError):self.probe(lambda m:m['metrics']['gpu_ms'].update(unit='seconds'))
    def test_nan_rejected(self):
        with self.assertRaises(ValueError):self.probe(raw=[{'timestamp_ms':0,'metric':'gpu_ms','value':float('nan'),'unit':'ms'}])
    def test_out_of_range_time(self):
        with self.assertRaises(ValueError):self.probe(raw=[{'timestamp_ms':33,'metric':'gpu_ms','value':2,'unit':'ms'}])
    def test_proprietary_capture_unsupported(self):
        with self.assertRaises(ValueError):self.probe(lambda m:m['raw_artifacts'][0].update(format='rdc'))
    def test_no_license(self):
        with self.assertRaises(ValueError):self.probe(lambda m:m.update(license=''))
    def test_synthetic_not_real(self):
        with self.assertRaises(ValueError):self.probe(lambda m:m.update(provenance='real-export'))
    def test_csv_export(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d); m=json.loads((HERE/'fixtures/T01/trace-manifest.json').read_text());p=root/'metrics.csv';p.write_text('timestamp_ms,metric,value,unit\n0,cpu_submit_ms,12,ms\n0,gpu_ms,3,ms\n');m['raw_artifacts']=[{'path':p.name,'format':'csv','sha256':hashlib.sha256(p.read_bytes()).hexdigest()}]
            self.assertEqual(analyze(m,root)['hypotheses'][0]['category'],'cpu_submit_bound')
if __name__=='__main__':unittest.main()
