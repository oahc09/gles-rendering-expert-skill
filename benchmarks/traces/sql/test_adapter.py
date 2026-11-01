import importlib.util
import json
from pathlib import Path
import tempfile
import unittest
HERE=Path(__file__).parent

def module(name,path):
    spec=importlib.util.spec_from_file_location(name,path);m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m);return m
adapter=module('sql_adapter',HERE/'adapter.py');builder=module('fixture_builder',HERE/'fixtures/build.py')
class AdapterTests(unittest.TestCase):
    def test_labeled_fixtures(self):
        with tempfile.TemporaryDirectory() as temp:
            for case in builder.CASES['cases']:
                with self.subTest(case=case['id']):
                    root=Path(temp)/case['id'];raw,meta=builder.materialize(case,root)
                    report=adapter.run(raw,meta,root/'out')
                    self.assertEqual(report['status'],case['expected_status'])
                    self.assertEqual(sorted(h['category'] for h in report.get('inferred',[])),sorted(case['expected_hypotheses']))
                    self.assertEqual(report['execution'],'NORMALIZED_SQLITE_FIXTURE')
    def test_healthy_overlap_cannot_validate_unrelated_global_mean(self):
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp);raw,meta=builder.materialize(builder.CASES['cases'][-1],root)
            report=adapter.run(raw,meta,root/'out')
            self.assertEqual(report['inferred'],[])
            self.assertEqual(report['legacy_analysis']['hypotheses'],[])
            check=report['temporal_checks']['cpu_submit_bound']
            self.assertEqual(check['complete_windows_checked'],1)
            self.assertIsNone(check['matched_window'])
    def test_positive_evidence_uses_only_matched_rows(self):
        case={'events':[['gles.cpu_submit',0,2000000],['gles.cpu_submit',150000000,12000000]],'gpu':[[150000000,3000000]]}
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp);raw,meta=builder.materialize(case,root)
            report=adapter.run(raw,meta,root/'out')
            matched=report['inferred'][0]['matched_window']
            self.assertEqual(matched['means'],{'cpu_submit_ms':12.0,'gpu_ms':3.0})
            self.assertEqual({r['timestamp_ms'] for r in matched['evidence']},{150.0})
            self.assertEqual(report['legacy_analysis']['hypotheses'][0]['evidence'],matched['evidence'])
    def test_real_provenance_rejected_for_sqlite(self):
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp);raw,meta=builder.materialize(builder.CASES['cases'][1],root);meta['provenance']='real-export'
            self.assertEqual(adapter.run(raw,meta,root/'out')['status'],'UNKNOWN')
    def test_missing_fields_never_execute_query(self):
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp);raw,meta=builder.materialize(builder.CASES['cases'][5],root)
            report=adapter.run(raw,meta,root/'out');query=report['queries']['gpu_work']
            self.assertEqual(query['status'],'UNKNOWN');self.assertEqual(query['rows'],[]);self.assertTrue(query['missing'])
    def test_sql_evidence_and_original_hash(self):
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp);raw,meta=builder.materialize(builder.CASES['cases'][1],root)
            report=adapter.run(raw,meta,root/'out');self.assertEqual(report['raw_trace_sha256'],meta['raw_sha256'])
            self.assertIn('sql_sha256',report['queries']['cpu_submit']);self.assertEqual(report['queries']['cpu_submit']['rows'][0]['id'],1)
if __name__=='__main__':unittest.main()
