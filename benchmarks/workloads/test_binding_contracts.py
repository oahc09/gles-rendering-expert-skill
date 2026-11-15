"""Synthetic contract tests only, not physical capture or performance evidence."""
import copy
import hashlib
import json
from pathlib import Path
import sys
import tempfile
import unittest
sys.path.insert(0,str(Path(__file__).resolve().parents[2]/'tools'))
from workload_fingerprint import fingerprint
from optimization_advisor import advise
from optimization_experiments import resolve

class BindingContracts(unittest.TestCase):
    def workload(self):return {'workload_id':'fixture','provenance':'synthetic','resolution':[4,4]}
    def test_optional_metadata(self):
        for key,values in {'sampling_formats':[42,'RGBA8',[1],['']], 'thermal_state':[[],42,''], 'trace_available':['yes',1,None]}.items():
            for v in values:
                with self.subTest(key=key,value=v),self.assertRaises(ValueError):fingerprint(dict(self.workload(),**{key:v}))
        fingerprint(dict(self.workload(),sampling_formats=['RGBA8'],thermal_state='UNKNOWN',trace_available=False))
    def test_synthetic_samples_compatible(self):
        self.assertEqual(fingerprint(dict(self.workload(),frame_times_ms=[1,2]))['frame_source_validation']['status'],'SYNTHETIC')
    def test_real_samples_require_source(self):
        with self.assertRaises(ValueError):fingerprint(dict(self.workload(),provenance='real-export',frame_times_ms=[1]))
    def test_real_source_bindings(self):
        with tempfile.TemporaryDirectory() as t:
            root=Path(t);d=dict(self.workload(),provenance='real-export',frame_times_ms=[1,2])
            payload={'workload_id':'fixture','unit':'ms','frame_times_ms':[1,2],'tool':'synthetic-contract','clock_domain':'monotonic'}
            p=root/'export.json';p.write_text(json.dumps(payload));d['frame_source']={'tool':payload['tool'],'clock_domain':'monotonic','raw_trace':'export.json','sha256':hashlib.sha256(p.read_bytes()).hexdigest(),'sample_count':2}
            self.assertEqual(fingerprint(d,root)['frame_source_validation']['status'],'HASH_BOUND_EXPORT')
            for key,value in [('sha256','0'*64),('sample_count',True),('sample_count',3),('raw_trace','../export.json'),('raw_trace',str(p)),('tool','different'),('clock_domain','other')]:
                bad=copy.deepcopy(d);bad['frame_source'][key]=value
                with self.subTest(key=key,value=value),self.assertRaises(ValueError):fingerprint(bad,root)
            bad=copy.deepcopy(d);bad['frame_times_ms']=[3,4]
            with self.assertRaises(ValueError):fingerprint(bad,root)
            payload['frame_times_ms']=[5,6];p.write_text(json.dumps(payload));d['frame_source']['sha256']=hashlib.sha256(p.read_bytes()).hexdigest()
            with self.assertRaises(ValueError):fingerprint(d,root)
    def data(self):
        workload=self.workload();workload['metrics']={k:{'value':v,'unit':unit,'tool':'fixture','raw_trace':'fixture','sample_count':1} for k,v,unit in [('blend_layers',8,'count'),('coverage_ratio',3,'ratio')]}
        c={'id':'a','experiment':'shader-advanced-v1','fallback':'baseline','labels':['OVERDRAW_BLEND'],'capability_supported':True,'estimated_gain_range':[.1,.4],'confidence':.9,'implementation_cost':.2,'regression_risk':.1}
        return {'workload':workload,'candidates':[c]}
    def test_registry(self):
        for k in ['shader-advanced-v1','texture-access-v1','postfx-resolution-loss-v1']:
            r=resolve(k);self.assertEqual(r['execution'],'NOT_RUN_BY_ADVISOR');self.assertEqual(len(r['source_sha256']),64)
        for v in ['../../shell.py','python3 bad.py',[],None]:self.assertIsNone(resolve(v))
    def test_unknown_not_recommended_even_relevant(self):
        d=self.data();d['candidates'][0]['experiment']='unknown';r=advise(d)['candidates'][0]
        self.assertEqual(r['status'],'INSUFFICIENT_EVIDENCE');self.assertEqual(r['priority_score'],0)
    def test_range_validation(self):
        for value in [[.5,.1],[-.1,.4],[0,2],[float('nan'),.5],[True,.5],[.1],'.1']:
            d=self.data();d['candidates'][0]['estimated_gain_range']=value
            with self.subTest(value=value),self.assertRaises(ValueError):advise(d)
    def test_completeness_and_lower_bound_ranking(self):
        d=self.data();a=d['candidates'][0];b=copy.deepcopy(a);b['id']='b';b['quality']={'golden_id':'fixture','thresholds':{'max':0}}
        d['candidates'].append(b);r=advise(d)['candidates'];self.assertEqual(r[0]['id'],'b');self.assertGreater(r[0]['priority_score'],r[1]['priority_score'])
        for x in r:self.assertEqual(x['status'],'RECOMMENDED_FOR_EXPERIMENT');self.assertFalse(x['auto_accept'])
        a['estimated_gain_range']=[.2,.4];r=advise(d)['candidates'];self.assertEqual(r[0]['id'],'a')
    def test_predictions_never_verify(self):
        d=self.data();d['candidates'][0].update(estimated_gain_range=[1,1],confidence=1)
        self.assertEqual(advise(d)['candidates'][0]['status'],'RECOMMENDED_FOR_EXPERIMENT')
    def test_quality_rejection_not_masked(self):
        d=self.data();d['candidates'][0].update(experiment='unknown',quality={'pass':False})
        self.assertEqual(advise(d)['candidates'][0]['status'],'REJECTED_BY_QUALITY')
if __name__=='__main__':unittest.main()
