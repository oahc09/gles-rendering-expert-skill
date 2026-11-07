import json
from pathlib import Path
import unittest
import hazards

class HazardTests(unittest.TestCase):
    def test_hazard_inventory(self):
        cases = list((Path(__file__).parent / 'cases/hazards').glob('*.json'))
        self.assertGreaterEqual(len(cases), 12)
        for path in cases:
            with self.subTest(case=path.stem):
                case = json.loads(path.read_text())
                result = hazards.check(case['input'])
                self.assertEqual(result['valid'], case['expected_valid'])
                if case['expected_rule']:
                    self.assertIn(case['expected_rule'], [x['rule'] for x in result['errors']])
    def test_barrier_before_write_does_not_fix(self):
        trace={'gles':'3.1','events':[{'barrier':['GL_ALL_BARRIER_BITS'],'accesses':[{'resource':'a','kind':'image','mode':'write'}]},{'accesses':[{'resource':'a','kind':'sample','mode':'read'}]}]}
        self.assertFalse(hazards.check(trace)['valid'])
    def test_malformed(self):
        for trace in (None, {}, {'events':[None]}, {'events':[{'accesses':['bad']}]}, {'events':[{'barrier':'GL_ALL_BARRIER_BITS'}]}):
            self.assertFalse(hazards.check(trace)['valid'])
    def test_sync_booleans(self):
        for flag in ('fence_after_write','producer_flush','consumer_wait','consumer_rebind'):
            self.assertFalse(hazards.check({'events':[{'sync':{flag:'false'}}]})['valid'])
    def test_context_visibility_persists_until_next_write(self):
        write = {'context': 'producer', 'accesses': [{'resource':'r','kind':'framebuffer','mode':'write'}]}
        read = {'context': 'consumer', 'accesses': [{'resource':'r','kind':'sample','mode':'read'}]}
        sync = dict(read, sync={'producer':'producer', 'fence_after_write':True,
                               'producer_flush':True, 'consumer_wait':True, 'consumer_rebind':True})
        self.assertTrue(hazards.check({'gles':'3.1','events':[write,sync,read]})['valid'])
        self.assertFalse(hazards.check({'gles':'3.1','events':[write,sync,read,write,read]})['valid'])
        other = dict(read, context='third')
        self.assertFalse(hazards.check({'gles':'3.1','events':[write,sync,other]})['valid'])
    def test_dynamic_is_warning(self):
        result=hazards.check({'gles':'3.1','events':[{'intra_dispatch_dependency':True}]})
        self.assertTrue(result['valid']);self.assertEqual(result['warnings'][0]['rule'],'HZ_DYNAMIC')

if __name__ == '__main__':
    unittest.main()
