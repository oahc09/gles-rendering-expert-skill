import copy
import unittest
from rendergraph_optimizer import advise


def graph():
    return {'resources': {'a': {'format': 'RGBA8', 'size': [64,64]}}, 'passes': [{'id':'draw','writes':['a']}]}


class OptimizerTests(unittest.TestCase):
    def test_no_mutation(self):
        g=graph(); old=copy.deepcopy(g); advise(g,True); self.assertEqual(g,old)
    def test_missing_sync(self): self.assertEqual(advise(graph())['status'],'INSUFFICIENT_EVIDENCE')
    def test_feedback(self):
        g=graph(); g['passes'][0]['reads']=['a']; self.assertFalse(advise(g,True)['valid'])
    def test_lost_attachment(self):
        g=graph(); g['passes'][0]['discard']=['a']; g['passes'].append({'id':'later','reads':['a']}); self.assertFalse(advise(g,True)['valid'])
    def test_barrier_field_rejected(self):
        g=graph(); g['passes'][0]['barrier']='WRONG'; self.assertFalse(advise(g,True)['valid'])
    def test_bad_resource(self):
        g=graph(); g['resources']['a']['samples']=0; self.assertFalse(advise(g,True)['valid'])
    def test_cycle(self):
        g=graph(); g['passes'][0]['depends_on']=['draw']; self.assertFalse(advise(g,True)['valid'])
    def test_unknown(self):
        g=graph(); g['passes'][0]['writes']=['absent']; self.assertFalse(advise(g,True)['valid'])
    def test_transient_is_conditional(self):
        s=advise(graph(),True)['suggestions'][0]; self.assertEqual(s['status'],'RECOMMENDED_FOR_EXPERIMENT'); self.assertIn('presented',s['preconditions'][0])
    def test_imported_not_transient(self):
        g=graph(); g['resources']['a']['imported']=True; self.assertEqual(advise(g,True)['suggestions'],[])
    def test_fusion_candidate(self):
        g=graph(); g['passes'].append({'id':'next','writes':['a'],'depends_on':['draw']}); self.assertIn('PASS_FUSION_CANDIDATE',[s['kind'] for s in advise(g,True)['suggestions']])
    def test_sampling_not_fused(self):
        g=graph(); g['resources']['b']=copy.deepcopy(g['resources']['a']); g['passes'].append({'id':'next','reads':['a'],'writes':['b'],'depends_on':['draw']}); self.assertNotIn('PASS_FUSION_CANDIDATE',[s['kind'] for s in advise(g,True)['suggestions']])
    def test_no_benefit_claim(self): self.assertEqual(advise(graph(),True)['device_performance'],'NOT_RUN')
    def test_empty_no_candidate(self): self.assertEqual(advise({'resources':{},'passes':[]},True)['status'],'NO_CANDIDATE')

if __name__ == '__main__': unittest.main()
