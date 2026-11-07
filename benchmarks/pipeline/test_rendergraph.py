import json
from pathlib import Path
import unittest
import rendergraph

class RenderGraphTests(unittest.TestCase):
    def test_graph_inventory(self):
        cases = list((Path(__file__).parent / 'cases/graphs').glob('*.json'))
        self.assertGreaterEqual(len(cases), 10)
        for path in cases:
            with self.subTest(case=path.stem):
                case = json.loads(path.read_text())
                result = rendergraph.check(case['input'])
                self.assertEqual(result['valid'], case['expected_valid'])
                if case['expected_rule']:
                    self.assertIn(case['expected_rule'], [x['rule'] for x in result['errors']])
    def test_malformed(self):
        for graph in (None, [], {}, {'resources':{},'passes':[{'id':[]}]}, {'resources':{},'passes':[{'id':'a','reads':'a'}]}, {'resources':{},'passes':[{'id':'a','resolve':None}]}):
            with self.subTest(graph=graph):
                self.assertFalse(rendergraph.check(graph)['valid'])
    def test_multisample_requires_resolve(self):
        graph = {'resources':{'a':{'format':'RGBA8','size':[1,1],'samples':4,'imported':True}},'passes':[{'id':'sample','reads':['a']}]}
        self.assertIn('RG_UNRESOLVED_MSAA', [e['rule'] for e in rendergraph.check(graph)['errors']])
    def test_boolean_flags(self):
        for flag in ('imported', 'transient'):
            graph = {'resources':{'a':{'format':'RGBA8','size':[1,1],flag:'false'}},'passes':[]}
            self.assertFalse(rendergraph.check(graph)['valid'])
    def test_imported_not_aliasable(self):
        r={'format':'RGBA8','size':[1,1],'transient':True,'imported':True}
        graph={'resources':{'a':r,'b':r},'passes':[{'id':'a','reads':['a']},{'id':'b','reads':['b']}]}
        self.assertEqual(rendergraph.check(graph)['alias_candidates'], [])
    def test_topological_order(self):
        result = rendergraph.check({'resources': {}, 'passes': [{'id':'b','depends_on':['a']},{'id':'a'}]})
        self.assertEqual(result['order'], ['a','b'])
    def test_alias_lifetimes(self):
        resource = {'format':'RGBA8','size':[1,1],'transient':True}
        result = rendergraph.check({'resources':{'a':resource,'b':resource},'passes':[{'id':'a','writes':['a']},{'id':'b','writes':['b']}]})
        self.assertEqual(result['alias_candidates'], [['a','b']])

if __name__ == '__main__':
    unittest.main()
