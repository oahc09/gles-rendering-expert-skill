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

if __name__=='__main__':unittest.main()
