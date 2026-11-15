import copy
import hashlib
import json
import sys
import tempfile
import unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[2]/'tools'))
from workload_fingerprint import fingerprint, RULES, UNITS
from estimate_gpu_cost import estimate, compare_calibration
from optimization_advisor import advise, decide
HERE=Path(__file__).parent

class Workloads(unittest.TestCase):
    def test_samples(self):
        for sample in json.loads((HERE/'samples.json').read_text()):
            with self.subTest(sample['workload_id']):
                self.assertEqual(fingerprint(sample['input'])['labels'],sample['expected_labels'])
                self.assertEqual(fingerprint(sample['input']),fingerprint(sample['input']))
    def test_invalid_metrics(self):
        d={'workload_id':'x','provenance':'synthetic','resolution':[10,10],'metrics':{}}
        for value in [float('nan'),float('inf'),True,-1]:
            d['metrics']={'gpu_ms':{'value':value,'unit':'ms','sample_count':1,'tool':'fixture','raw_trace':'fixture'}}
            with self.subTest(value=value),self.assertRaises(ValueError):fingerprint(d)
    def test_overlap(self):
        d={'workload_id':'x','provenance':'synthetic','resolution':[10,10],'metrics':{},'intervals':[{'stage':'cpu','clock':'mono','start_ms':0,'end_ms':10},{'stage':'gpu','clock':'mono','start_ms':5,'end_ms':15},{'stage':'gpu','clock':'mono','start_ms':6,'end_ms':12}]}
        self.assertEqual(fingerprint(d)['cpu_gpu_overlap_ms'],5)
        d['intervals'][1]['clock']='gpu';self.assertIsNone(fingerprint(d)['cpu_gpu_overlap_ms'])
    def test_unit_and_count(self):
        d=json.loads((HERE/'samples.json').read_text())[0]['input']
        m=next(iter(d['metrics'].values()))
        m['unit']='seconds'
        with self.assertRaises(ValueError):fingerprint(d)

class Cost(unittest.TestCase):
    def test_cases(self):
        for c in json.loads((HERE.parent/'gpu_cost/cases.json').read_text()):
            with self.subTest(c['id']):
                if c.get('invalid'):
                    with self.assertRaises(ValueError):estimate(c['input'])
                else:
                    r=estimate(c['input']); self.assertEqual(r['logical_upper_bytes'],c['expected_upper']);self.assertIsNone(r['dram_bytes'])
    def test_calibration_scope(self):
        with self.assertRaises(ValueError):compare_calibration(estimate({'attachments':[]}),{'logical_bytes':1})

class Advisor(unittest.TestCase):
    def test_cases(self):
        cases=json.loads((HERE.parent/'optimization_advisor/cases.json').read_text())
        with tempfile.TemporaryDirectory() as folder:
            p=Path(folder)/'trace.json'
            for case in cases:
                c=case['candidate']; m=c.get('measurement')
                if m and m.get('artifacts'):
                    p.write_text(json.dumps({k:v for k,v in m.items() if k!='artifacts'}))
                    if m['artifacts'][0].get('sha256')=='FIXTURE_HASH':m['artifacts'][0]['sha256']=hashlib.sha256(p.read_bytes()).hexdigest()
                with self.subTest(case['id']):self.assertEqual(decide(c,Path(folder))['status'],case['expected'])
    def test_detached_raw_pairs_rejected(self):
        c=json.loads((HERE.parent/'optimization_advisor/cases.json').read_text())[0]['candidate']
        with tempfile.TemporaryDirectory() as folder:
            p=Path(folder)/'trace.json';p.write_text('{}')
            c['measurement']['artifacts'][0]['sha256']=hashlib.sha256(p.read_bytes()).hexdigest()
            self.assertEqual(decide(c,folder)['status'],'INSUFFICIENT_EVIDENCE')
    def test_path_escape_rejected(self):
        c=json.loads((HERE.parent/'optimization_advisor/cases.json').read_text())[0]['candidate']
        c['measurement']['artifacts'][0]['path']='../outside.json'
        with tempfile.TemporaryDirectory() as folder:
            self.assertEqual(decide(c,folder)['status'],'INSUFFICIENT_EVIDENCE')
    def test_fixture_never_physical(self):
        c=json.loads((HERE.parent/'optimization_advisor/cases.json').read_text())[0]['candidate']
        c['measurement']['provenance']='synthetic'
        self.assertEqual(decide(c,'.')['status'],'INSUFFICIENT_EVIDENCE')
    def test_reviewed_contract_states(self):
        # Synthetic independent-review CONTRACT test, never a physical result.
        for candidate_ms, expected in [(8,'VERIFIED_IMPROVEMENT'),(10,'NO_GAIN'),(12,'REGRESSION'),(0,'INVALID')]:
            with self.subTest(candidate_ms=candidate_ms),tempfile.TemporaryDirectory() as folder:
                root=Path(folder)
                c=json.loads((HERE.parent/'optimization_advisor/cases.json').read_text())[0]['candidate']
                c['workload_id']='synthetic-contract';m=c['measurement'];m['collector_id']='fixture-collector'
                for pair in m['pairs']:pair['candidate_ms']=candidate_ms
                (root/'trace.json').write_text(json.dumps({k:v for k,v in m.items() if k!='artifacts'}))
                m['artifacts'][0]['sha256']=hashlib.sha256((root/'trace.json').read_bytes()).hexdigest()
                (root/'quality.json').write_text('synthetic oracle fixture')
                review={'reviewer_id':'fixture-reviewer','decision':'ACCEPT_MEASUREMENT_AND_QUALITY','bindings':{k:m[k] for k in ('device','gpu','driver','backend','build_sha','baseline_sha')},'quality_artifact':{'path':'quality.json','sha256':hashlib.sha256((root/'quality.json').read_bytes()).hexdigest()}}
                review['bindings'].update(workload_id=c['workload_id'],golden_id=c['quality']['golden_id'],quality_thresholds=c['quality']['thresholds'],trace_artifacts=m['artifacts'])
                (root/'review.json').write_text(json.dumps(review))
                review['artifact']={'path':'review.json','sha256':hashlib.sha256((root/'review.json').read_bytes()).hexdigest()};c['independent_review']=review
                if expected=='INVALID':
                    with self.assertRaises(ValueError):decide(c,root)
                else:self.assertEqual(decide(c,root)['status'],expected)
                review['reviewer_id']=m['collector_id']
                self.assertEqual(decide(c,root)['status'],'INSUFFICIENT_EVIDENCE')
    def test_gain_range(self):
        c={'experiment':'a','fallback':'b','capability_supported':True,'minimum_gain':1.1}
        with self.assertRaises(ValueError):decide(c,'.')
    def test_nan(self):
        d={'workload':{'workload_id':'x','provenance':'synthetic','resolution':[1,1]},'candidates':[{'estimated_gain':float('nan')}]}
        with self.assertRaises(ValueError):advise(d)
    def test_unknown_not_recommended(self):
        d={'workload':{'workload_id':'x','provenance':'synthetic','resolution':[1,1]},'candidates':[{'id':'x','experiment':'ab','fallback':'base','capability_supported':True,'labels':['BANDWIDTH']}]}
        self.assertEqual(advise(d)['candidates'][0]['status'],'INSUFFICIENT_EVIDENCE')
if __name__=='__main__':unittest.main()
