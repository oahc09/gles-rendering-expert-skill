import copy, hashlib, json, unittest
from pathlib import Path
import repair as r

class RepairTests(unittest.TestCase):
    def setUp(self):self.corpus=r.build()
    def test_inventory_and_frozen_corpus(self):
        self.assertEqual(self.corpus,json.loads(Path(__file__).with_name('cases.json').read_text()))
        self.assertEqual(len(self.corpus['cases']),36)
        self.assertEqual(len({c['case_id'] for c in self.corpus['cases']}),36)
        self.assertEqual(len({r.digest(c['input']) for c in self.corpus['cases']}),36)
        self.assertEqual({c['domain'] for c in self.corpus['cases']},{'graph','abi','shader','resource','lifecycle','differential'})
    def test_nonshader_fixed_controls(self):
        for c in self.corpus['cases']:
            if c['domain']=='shader':continue
            with self.subTest(c['case_id']):self.assertEqual(r.evaluate(c,c['oracle']['expected'])['status'],'FIXTURE_PASS')
    def test_negative_controls(self):
        for c in self.corpus['cases']:
            with self.subTest(c['case_id']):self.assertEqual(r.evaluate(c,{'accept_everything':True})['status'],'FAIL')
    def test_oracle_not_leaked(self):
        for c in self.corpus['cases']:
            self.assertNotIn('oracle',r.request(c));self.assertNotIn('expected',r.request(c))
    def test_patch_bounded(self):
        with self.assertRaises(ValueError):r.evaluate(self.corpus['cases'][0],{'x':'y'*20000})
    def test_input_immutable(self):
        c=self.corpus['cases'][0];before=copy.deepcopy(c);r.evaluate(c,c['oracle']['expected']);self.assertEqual(c,before)
    def test_unmodified_shader_never_passes(self):
        for c in self.corpus['cases']:
            if c['domain']=='shader':self.assertEqual(r.evaluate(c,{'sources':c['input']['sources']})['status'],'FAIL')
    def test_shader_requires_actual_compiler(self):
        c=next(c for c in self.corpus['cases'] if c['domain']=='shader');sources={k:'#version 300 es\nvoid main(){}\n' for k in c['input']['sources']}
        result=r.evaluate(c,{'sources':sources},'/missing-compiler')
        self.assertEqual(result['status'],'BLOCKED_BY_TOOLCHAIN')
    def test_no_provider_claim(self):
        self.assertEqual(self.corpus['provider_status'],'BLOCKED_BY_PROVIDER');self.assertEqual(self.corpus['model_quality'],'NOT_EVALUATED')
        with self.assertRaises(ValueError):r.score_provider(self.corpus,{},[])
        with self.assertRaises(ValueError):r.score_provider(self.corpus,{'provider':'fixture','synthetic_infrastructure_test':True},[])
    def test_unpaired_rejected(self):
        with self.assertRaises(ValueError):r.score_provider(self.corpus,{'provider':'not-run','results':[]},[])
    def test_response_hash_bound(self):
        rows=[dict(case_id=c['case_id'],condition=mode,status='RESPONSE_CAPTURED',response='test',response_sha256='bad') for c in self.corpus['cases'] for mode in ('no_skill','with_skill')]
        with self.assertRaisesRegex(ValueError,'hash'):r.score_provider(self.corpus,{'provider':'unit-only','results':rows},[])
    def test_fixture_cannot_claim_driver_bug(self):
        for c in self.corpus['cases']:
            if c['domain']=='differential':self.assertEqual(r.evaluate(c,{'classification':'FAIL','driver_bug_proven':True})['status'],'FAIL')

class ScoreV3Tests(unittest.TestCase):
    """Synthetic in-memory validation only; no model-quality report is emitted."""
    def setUp(self):
        self.corpus={'cases':[r.build()['cases'][0]]};self.artifacts={}
        def artifact(s):
            h=hashlib.sha256(s.encode()).hexdigest();self.artifacts[h]=s;return h
        self.h=artifact('unit artifact');self.log=artifact('unit log');self.suite=artifact('unit suite')
        self.original=artifact(json.dumps(self.corpus['cases'][0]['input'],sort_keys=True))
        self.response='unit response';rh=hashlib.sha256(self.response.encode()).hexdigest();case=self.corpus['cases'][0]
        self.manifest={'schema_version':3,'provider':'unit-only-validation-not-a-real-run','synthetic_infrastructure_test':False,'corpus_sha256':r.digest(self.corpus),'results':[]}
        self.reviews=[]
        for condition in ('no_skill','with_skill'):
            self.manifest['results'].append(dict(case_id=case['case_id'],condition=condition,status='RESPONSE_CAPTURED',response=self.response,response_sha256=rh))
            e=dict(status='PASS',artifact_sha256=self.h,log_sha256=self.log,suite_sha256=self.suite,environment='unit',command='not executed')
            self.reviews.append(dict(case_id=case['case_id'],condition=condition,response_sha256=rh,reviewer='unit reviewer',rationale='synthetic interface test only',
                correct_fix=True,introduced_regression=False,repair_attempted=True,baseline=copy.deepcopy(e),patched=copy.deepcopy(e),
                diagnosis=dict(true_positive_ids=[case['oracle']['failure']],unsupported_findings=[],rejected_legal_controls=[],rationale='unit',evidence_sha256=[self.log]),
                minimization=dict(status='PASS',original_failure_id=case['oracle']['failure'],reduced_failure_id=case['oracle']['failure'],original_sha256=self.original,reduced_sha256=self.h,replay_log_sha256=self.log,rationale='unit'),
                stage_evidence={s:dict(status='PASS',artifact_sha256=[self.log],rationale='unit') for s in r.V3_STAGES}))
    def score(self):return r.score_v3(self.corpus,self.manifest,self.reviews,self.artifacts)
    def test_complete_paired_metric_math(self):
        m=self.score();self.assertEqual(m['metrics']['with_skill']['diagnosis_accuracy'],1)
        self.assertEqual(m['metrics']['with_skill']['evidence_completeness'],1)
        self.assertEqual(m['metrics']['no_skill']['false_repair_rate'],0)
        self.assertTrue(all(x==0 for x in m['paired_delta_with_minus_without'].values()))
    def test_false_metrics_explicit_denominators(self):
        a=self.reviews[0];a['correct_fix']=False;a['diagnosis']['true_positive_ids']=[]
        a['diagnosis']['unsupported_findings']=['invented-fault'];a['diagnosis']['rejected_legal_controls']=[r.V3_CONTROLS[0]]
        m=self.score()['metrics']['no_skill'];self.assertEqual(m['diagnosis_accuracy'],0);self.assertEqual(m['false_repair_rate'],1)
        self.assertEqual(m['false_positive_control_rate'],1/3);self.assertEqual(m['false_discovery_rate'],1)
    def test_missing_field_rejected(self):
        for key in ('diagnosis','minimization','stage_evidence','repair_attempted'):
            saved=self.reviews[0].pop(key)
            with self.assertRaises(ValueError):self.score()
            self.reviews[0][key]=saved
    def test_unknown_diagnosis_id_rejected(self):
        self.reviews[0]['diagnosis']['true_positive_ids']=['invented']
        with self.assertRaises(ValueError):self.score()
    def test_unsupported_findings_cannot_duplicate_true_id(self):
        self.reviews[0]['diagnosis']['unsupported_findings']=self.reviews[0]['diagnosis']['true_positive_ids']
        with self.assertRaises(ValueError):self.score()
    def test_unknown_or_duplicate_control_rejected(self):
        for ids in (['made-up'],[r.V3_CONTROLS[0]]*2):
            self.reviews[0]['diagnosis']['rejected_legal_controls']=ids
            with self.assertRaises(ValueError):self.score()
    def test_boolean_coercion_rejected(self):
        self.reviews[0]['repair_attempted']=1
        with self.assertRaises(ValueError):self.score()
    def test_fake_hash_rejected(self):
        self.reviews[0]['baseline']['log_sha256']='a'*64
        with self.assertRaises(ValueError):self.score()
    def test_tampered_bytes_rejected(self):
        self.artifacts[self.h]='tampered'
        with self.assertRaisesRegex(ValueError,'content hash'):self.score()
    def test_frozen_corpus_binding_rejected(self):
        self.manifest['corpus_sha256']='a'*64
        with self.assertRaises(ValueError):self.score()
    def test_synthetic_run_rejected(self):
        for flag in (True,None,'false'):
            self.manifest['synthetic_infrastructure_test']=flag
            with self.assertRaises(ValueError):self.score()
    def test_missing_stage_never_complete(self):
        del self.reviews[0]['stage_evidence']['differential']
        with self.assertRaises(ValueError):self.score()
    def test_not_run_does_not_become_zero_or_pass(self):
        a=self.reviews[0];a['correct_fix']=False;a['repair_attempted']=False
        a['stage_evidence']['differential']=dict(status='NOT_RUN',artifact_sha256=[],rationale='driver unavailable')
        m=self.score()['metrics']['no_skill'];self.assertEqual(m['evidence_completeness'],6/7)
        self.assertIsNone(m['false_repair_rate']);self.assertEqual(m['unmeasured_stages'],1)
    def test_correct_fix_requires_execution(self):
        self.reviews[0]['stage_evidence']['differential']=dict(status='NOT_RUN',artifact_sha256=[],rationale='driver unavailable')
        with self.assertRaises(ValueError):self.score()
    def test_wrong_minimized_failure_cannot_pass(self):
        self.reviews[0]['minimization']['reduced_failure_id']='different error'
        with self.assertRaises(ValueError):self.score()
    def test_failed_minimization_counted_not_dropped(self):
        a=self.reviews[0];a['minimization']['status']='FAIL';a['minimization']['reduced_failure_id']='different error';a['stage_evidence']['minimize']['status']='FAIL'
        m=self.score()['metrics']['no_skill'];self.assertEqual(m['minimization_fidelity'],0);self.assertEqual(m['minimization_coverage'],1)
    def test_no_minimization_yields_null_fidelity(self):
        a=self.reviews[0];a['minimization']={k:None for k in a['minimization']};a['minimization'].update(status='NOT_RUN',rationale='not run')
        a['stage_evidence']['minimize']=dict(status='NOT_RUN',artifact_sha256=[],rationale='not run')
        m=self.score()['metrics']['no_skill'];self.assertIsNone(m['minimization_fidelity']);self.assertEqual(m['minimization_coverage'],0)
    def test_minimization_original_bound_to_case(self):
        self.reviews[0]['minimization']['original_sha256']=self.h
        with self.assertRaises(ValueError):self.score()
    def test_fake_extra_stage_fields_rejected(self):
        self.reviews[0]['stage_evidence']['compile_run']['measured']=True
        with self.assertRaises(ValueError):self.score()
    def test_empty_corpus_rejected(self):
        self.corpus={'cases':[]};self.manifest['corpus_sha256']=r.digest(self.corpus)
        with self.assertRaises(ValueError):self.score()
    def test_duplicate_pair_rejected(self):
        self.manifest['results'].append(self.manifest['results'][0])
        with self.assertRaises(ValueError):self.score()

if __name__=='__main__':unittest.main()
