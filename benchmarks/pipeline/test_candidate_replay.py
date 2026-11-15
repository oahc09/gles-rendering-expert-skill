import copy,sys,unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[2]/'tools'))
from rendergraph_replay import baseline,transform,validate,digest
from candidate_replay import golden,Host
class GraphReplay(unittest.TestCase):
    def test_copy_and_hash(self):
        g=baseline();old=copy.deepcopy(g);r=transform(g)
        self.assertEqual(g,old);self.assertEqual(r['fallback'],g)
        self.assertNotEqual(r['baseline_sha256'],r['candidate_sha256'])
        self.assertEqual(r['candidate']['resources']['intermediate']['size'],[2,2])
    def test_sync(self):
        r=validate(baseline());self.assertEqual(r['memory_barrier_bits'],0);self.assertEqual(r['status'],'PASS')
    def test_missing_dependency(self):
        g=baseline();g['passes'][1].pop('depends_on')
        with self.assertRaises(ValueError):validate(g)
    def test_feedback(self):
        g=baseline();g['passes'][1]['writes']=['scene']
        with self.assertRaises(ValueError):validate(g)
    def test_missing_attachment(self):
        g=baseline();g['resources'].pop('intermediate')
        with self.assertRaises(ValueError):validate(g)
    def test_false_barrier(self):
        for bits in (0,0x2000,'GL_ALL_BARRIER_BITS'):
            g=baseline();g['passes'][1]['barrier']=bits
            with self.assertRaises(ValueError):validate(g)
    def test_incoherent_stage(self):
        g=baseline();g['passes'][0]['imageStore']=True
        with self.assertRaises(ValueError):validate(g)
    def test_external_or_alias(self):
        for key in ('imported','transient','alias'):
            g=baseline();g['resources']['scene'][key]=True
            with self.assertRaises(ValueError):validate(g)
    def test_discard(self):
        g=baseline();g['passes'][0]['discard']=['scene']
        with self.assertRaises(ValueError):validate(g)
    def test_msaa(self):
        g=baseline();g['resources']['scene']['samples']=4
        with self.assertRaises(ValueError):validate(g)
    def test_repeat_transform(self):
        with self.assertRaises(ValueError):transform(transform(baseline())['candidate'])
    def test_bounds(self):
        for size in ([1,1],[65,65],[4,4,4]):
            g=baseline();g['resources']['intermediate']['size']=size
            with self.assertRaises(ValueError):validate(g)
    def test_goldens(self):
        self.assertEqual(golden('constant',False),golden('constant',True))
        self.assertNotEqual(golden('checkerboard',False),golden('checkerboard',True))
    def test_preflight_before_host_access(self):
        # An uninitialized Host must reject invalid graph before any native API lookup.
        h=object.__new__(Host);g=baseline();g['passes'][1]['barrier']=0
        with self.assertRaises(ValueError):h.replay(g,'constant')
if __name__=='__main__':unittest.main()
