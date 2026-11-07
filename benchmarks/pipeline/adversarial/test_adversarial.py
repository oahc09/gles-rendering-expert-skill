import copy
import json
from pathlib import Path
import tempfile
import unittest
from check import graph_check,graph_cases,abi_cases,abi_check,reduce_graph,run,synchronization_proof,base_graph,hazard_cases

class AdversarialTests(unittest.TestCase):
    def test_graph_inventory(self):
        cases=graph_cases();self.assertEqual(len(cases),24)
        self.assertEqual(len({json.dumps(c['graph'],sort_keys=True)+str(c['aliases']) for c in cases}),24)
        for c in cases:
            with self.subTest(c['id']):
                r=graph_check(c['graph'],c['aliases'])
                if c['expected_rule'] is None:self.assertTrue(r['valid'],r)
                else:self.assertIn(c['expected_rule'],[e['rule'] for e in r['errors']])

    def test_abi_inventory(self):
        cases=abi_cases();self.assertEqual(len(cases),24)
        for c in cases:
            with self.subTest(c['id']):
                errors=abi_check(c['manifest'],reflection=c['reflection'],capability=c['capability'],active_uniforms=c['active_uniforms'],required_uniforms=c['required_uniforms'])
                if c['expected_rule'] is None:self.assertFalse(errors)
                else:self.assertTrue(any(c['expected_rule'] in e for e in errors))

    def test_no_alias_from_arbitrary_topological_listing(self):
        g=base_graph();g['passes'][2]['depends_on']=[]
        r=graph_check(g,[['a','b']]);self.assertFalse(r['valid']);self.assertFalse(r['alias_proofs'])

    def test_alias_transitivity(self):
        resource=dict(format='RGBA8',size=[8,8],samples=1,transient=True)
        g=dict(resources={k:copy.deepcopy(resource) for k in 'abc'},passes=[dict(id='b',writes=['b']),dict(id='ac',depends_on=['b'],writes=['a','c'])])
        r=graph_check(g,[['a','b'],['b','c']]);self.assertFalse(r['valid'])
        self.assertTrue(any(e.get('resources')==['a','c'] for e in r['errors']))

    def test_captured_reflection_is_not_replaced_by_fixture(self):
        import importlib.util
        import unittest.mock
        spec=importlib.util.spec_from_file_location('adversarial_runtime_test',Path(__file__).with_name('runtime.py'))
        m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
        row=dict(block_size=999,block_binding=999,offsets=[999]*3,member_types=[0x1406]*3,
                 member_sizes=[1]*3,member_row_major=[0]*3,sampler_unit=999,sampler_type='usampler2D',checked_faults=['offset','unit'])
        with tempfile.TemporaryDirectory() as d,unittest.mock.patch.object(m.runtime,'execute',return_value=(row,m.runtime.reference('C05'))):
            with self.assertRaisesRegex(ValueError,'baseline reflection'):m.run(Path(__file__),Path(d))

    def test_reducer_preserves_failure(self):
        for c in graph_cases():
            if c['expected_rule']:
                r=reduce_graph(c['graph'],c['aliases'],c['expected_rule'])
                self.assertEqual(r['status'],'REPRODUCED');self.assertTrue(r['one_minimal'])
                self.assertTrue(any(e['rule']==c['expected_rule'] for e in graph_check(r['graph'],r['aliases'])['errors']))

    def test_bounded_input(self):
        g=base_graph();g['passes']*=40
        with self.assertRaises(ValueError):graph_check(g)

    def test_consumer_barriers(self):
        rows=hazard_cases();self.assertEqual(len(rows),10)
        self.assertTrue(all(x['status']=='PASS' for x in rows))

    def test_malformed_alias(self):
        with self.assertRaises(ValueError):graph_check(base_graph(),[['a']])

    def test_report(self):
        with tempfile.TemporaryDirectory() as d:
            r=run(Path(d));self.assertEqual(r['status'],'PASS');self.assertTrue((Path(d)/'report.md').exists())

    def events(self):
        return [dict(id='w',context='worker',op='write',resource='texture'),
                dict(id='f',context='worker',op='fence',fence='f1'),
                dict(id='flush',context='worker',op='flush'),
                dict(id='wait',context='render',op='wait',fence='f1'),
                dict(id='bind',context='render',op='rebind',resource='texture'),
                dict(id='read',context='render',op='read',resource='texture',fence='f1')]

    def proof(self,events):return synchronization_proof(events,{'worker':'shared','render':'shared'})

    def test_happens_before_explicit_chain(self):
        r=self.proof(self.events());self.assertTrue(r['valid']);self.assertEqual(len(r['proofs']),1)

    def test_each_chain_link_required(self):
        for i in range(5):
            e=self.events();del e[i]
            self.assertFalse(self.proof(e)['valid'],str(i))

    def test_wrong_fence_rejected(self):
        e=self.events();e[-1]['fence']='other';self.assertFalse(self.proof(e)['valid'])

    def test_old_fence_cannot_publish_new_write(self):
        e=self.events();e.insert(3,dict(id='new_write',context='worker',op='write',resource='texture'))
        self.assertFalse(self.proof(e)['valid'])

    def test_rebind_before_wait_insufficient(self):
        e=self.events();e[3],e[4]=e[4],e[3];self.assertFalse(self.proof(e)['valid'])

    def test_unshared_contexts_rejected(self):
        self.assertFalse(synchronization_proof(self.events(),{'worker':'a','render':'b'})['valid'])

    def test_duplicate_event_rejected(self):
        e=self.events();e[1]['id']='w'
        with self.assertRaises(ValueError):self.proof(e)

    def test_same_context_program_order(self):
        e=self.events();e[-1]['context']='worker';self.assertTrue(self.proof([e[0],e[-1]])['valid'])

if __name__=='__main__':unittest.main()
