import json
import sys
import unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).parent))
import model

class StateMachine(unittest.TestCase):
    def test_case_oracles(self):
        self.assertGreaterEqual(len(model.cases()),40)
        for c in model.cases():
            with self.subTest(id=c['id']):self.assertEqual(model.replay(c['sequence']),c['expected'])
    def test_faults_reduced_replayed_and_fixed(self):
        self.assertGreaterEqual(len(model.DOMAINS),10)
        for d in model.DOMAINS:
            with self.subTest(domain=d):
                r=model.minimize_fault(d);self.assertTrue(r['one_minimal']);self.assertLess(len(r['minimal']),len(r['original']))
                self.assertTrue(all(s[-1]=='HARNESS_FAILURE' for s in r['repetitions']));self.assertEqual(r['corrected'][-1],'PASS')
    def test_fault_is_not_real_reset(self):self.assertFalse(model.minimize_fault('texture')['actual_device_reset'])
    def test_replay_budget(self):self.assertRaises(ValueError,model.replay,['noise']*129)
    def test_unknown_operation_rejected(self):self.assertRaises(ValueError,model.replay,['bogus:texture'])
    def test_reset_invalidation(self):self.assertEqual(model.replay(['create:texture','bind:texture','reset','audit:texture']),['PASS']*4)

if __name__=='__main__':unittest.main()
