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

def postfx():
    g=graph();g['resources']['b']={'format':'RGBA8','size':[64,64]};g['resources']['c']={'format':'RGBA8','size':[64,64]}
    g['passes'] += [{'id':'post','reads':['a'],'writes':['b'],'depends_on':['draw']},{'id':'present','reads':['b'],'writes':['c'],'depends_on':['post']}]
    contract={'pass_id':'post','scale':0.5,'experiment_id':'postfx-resolution-loss-v1','normalized_uv':True,'kernel_rescaling':True,'downstream_resampling':True,'external_output':False,'temporal_history':False,'quality_budget':{'max_abs_rgba_error':0.01,'max_silhouette_error':0.01,'max_temporal_error':0.01,'golden_id':'fixed-scene'}}
    return g,contract

class PostFXTests(unittest.TestCase):
    def check_rejected(self,field,value):
        g,c=postfx();c[field]=value
        r=advise(g,True,[c]);self.assertEqual(r['postfx_reviews'][0]['status'],'REJECTED');self.assertNotIn('POSTFX_SCALE_CANDIDATE',[x['kind'] for x in r['suggestions']])
    def test_valid_contract(self):
        g,c=postfx();old=copy.deepcopy(g);r=advise(g,True,[c]);x=[x for x in r['suggestions'] if x['kind']=='POSTFX_SCALE_CANDIDATE'][0]
        self.assertEqual(x['proposed_sizes'],{'b':[32,32]});self.assertEqual(x['semantic_proof'],'NOT_PROVEN');self.assertEqual(g,old)
    def test_unknown_pass(self):self.check_rejected('pass_id','missing')
    def test_boolean_scale(self):self.check_rejected('scale',True)
    def test_nan_scale(self):self.check_rejected('scale',float('nan'))
    def test_noop_scale(self):self.check_rejected('scale',1)
    def test_zero_size(self):self.check_rejected('scale',0.001)
    def test_external_output(self):self.check_rejected('external_output',True)
    def test_history(self):self.check_rejected('temporal_history',True)
    def test_missing_kernel(self):self.check_rejected('kernel_rescaling',False)
    def test_bad_bool(self):self.check_rejected('normalized_uv','true')
    def test_no_budget(self):self.check_rejected('quality_budget',{})
    def test_infinite_budget(self):
        g,c=postfx();c['quality_budget']['max_abs_rgba_error']=float('inf');self.check_rejected('quality_budget',c['quality_budget'])
    def test_final_output(self):
        g,c=postfx();g['passes'].pop();self.assertEqual(advise(g,True,[c])['postfx_reviews'][0]['status'],'REJECTED')
    def test_duplicate(self):
        g,c=postfx();self.assertEqual(advise(g,True,[c,c])['postfx_reviews'][1]['status'],'REJECTED')
    def test_unknown_fields(self):
        g,c=postfx();c['magic_speedup']=2;self.assertEqual(advise(g,True,[c])['postfx_reviews'][0]['status'],'REJECTED')
    def test_imported_attachment(self):
        g,c=postfx();g['resources']['b']['imported']=True;self.assertEqual(advise(g,True,[c])['postfx_reviews'][0]['status'],'REJECTED')
    def test_integer_target(self):
        g,c=postfx();g['resources']['b']['format']='R32UI';self.assertEqual(advise(g,True,[c])['postfx_reviews'][0]['status'],'REJECTED')
    def test_invalid_graph_still_rejected(self):
        g,c=postfx();g['passes'][1]['reads']=['b'];self.assertFalse(advise(g,True,[c])['valid'])
    def test_sync_still_required(self):
        g,c=postfx();self.assertEqual(advise(g,False,[c])['status'],'INSUFFICIENT_EVIDENCE')
    def test_no_experiment(self):self.check_rejected('experiment_id','')

    def test_unregistered_experiment(self):self.check_rejected('experiment_id','not-a-command')
    def test_invalid_size_rejected_by_checker(self):
        for size in ([64], [64,64,64], [0,64], '64x64', [True,64]):
            g,c=postfx();g['resources']['b']['size']=size;self.assertFalse(advise(g,True,[c])['valid'])
    def test_registered_validation(self):
        g,c=postfx();r=advise(g,True,[c]);suggestion=next(x for x in r['suggestions'] if x['kind']=='POSTFX_SCALE_CANDIDATE');self.assertIn('postfx_quality.py',suggestion['validation'])

if __name__ == '__main__': unittest.main()
