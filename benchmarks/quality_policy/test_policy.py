import unittest
from policy import QualityPolicy
CAPS={'msaa_samples':[1,2,4],'max_texture_size':4096,'max_anisotropy':8}
def s(t,p95=10,**extra):return dict(t_s=t,p95_ms=p95,budget_ms=16.667,backend='native_gles',**extra)
class PolicyTests(unittest.TestCase):
    def run_samples(self,rows,**kwargs):
        p=QualityPolicy(**kwargs);return [p.step(x,capabilities=CAPS,approved_levels=[0,1,2]) for x in rows]
    def test_deterministic(self):
        rows=[s(i,30 if i<25 else 10) for i in range(60)];self.assertEqual(self.run_samples(rows),self.run_samples(rows))
    def test_spike(self):self.assertTrue(all(x['level']==0 for x in self.run_samples([s(i,30 if i==4 else 10) for i in range(20)])))
    def test_sustained_then_recovers(self):
        rows=self.run_samples([s(i,30 if i<25 else 10) for i in range(60)])
        self.assertEqual(rows[3]['level'],1);self.assertEqual(rows[13]['level'],2);self.assertEqual(rows[-1]['level'],0)
        self.assertIn('RECOVERING',[r['state'] for r in rows])
    def test_jitter_no_oscillation(self):
        rows=self.run_samples([s(i,19 if i%2 else 12) for i in range(200)]);self.assertTrue(all(x['level']==0 for x in rows))
    def test_changes_rate_limited(self):
        rows=self.run_samples([s(i,30 if i%22<15 else 8) for i in range(300)])
        times=[r['t_s'] for r in rows if r['changed']];self.assertTrue(all(b-a>=10 for a,b in zip(times,times[1:])))
    def test_floor(self):self.assertLessEqual(max(r['level'] for r in self.run_samples([s(i,40) for i in range(100)],floor=1)),1)
    def test_disabled_retains(self):
        p=QualityPolicy();[p.step(s(i,30)) for i in range(8)]
        r=p.step(s(8,30),enabled=False);self.assertEqual(r['level'],1);self.assertFalse(r['may_apply'])
    def test_gap_not_continuous_pressure(self):
        p=QualityPolicy();p.step(s(0,30));self.assertEqual(p.step(s(100,30))['level'],0)
    def test_hot_degrades_even_fast(self):self.assertEqual(self.run_samples([s(i,8,thermal_status=3) for i in range(20)])[-1]['level'],2)
    def test_background_does_not_degrade(self):self.assertTrue(all(r['level']==0 for r in self.run_samples([s(i,40,foreground=False) for i in range(30)])))
    def test_unknown_capability_blocks_apply(self):self.assertFalse(QualityPolicy().step(s(0),approved_levels=[0])['may_apply'])
    def test_visual_gate(self):self.assertFalse(QualityPolicy().step(s(0),capabilities=CAPS)['may_apply'])
    def test_approved_does_not_change_os(self):
        r=QualityPolicy().step(s(0),capabilities=CAPS,approved_levels=[0]);self.assertTrue(r['may_apply']);self.assertFalse(r['operating_system_changes'])
    def test_backend_kept(self):
        for backend in ('angle','vulkan','software'):
            row=s(0);row['backend']=backend;self.assertEqual(QualityPolicy().step(row)['backend'],backend)
    def test_no_anisotropy_extension_assumption(self):self.assertEqual(QualityPolicy().step(s(0))['recommendation']['anisotropy'],1)
    def test_invalid_time_and_nan(self):
        p=QualityPolicy();p.step(s(0))
        with self.assertRaises(ValueError):p.step(s(0))
        with self.assertRaises(ValueError):QualityPolicy().step(s(0,float('nan')))
    def test_temperature_rise_blocks_recovery(self):
        rows=[s(i,30) for i in range(20)]+[s(i,8,thermal_trend_c_per_min=1) for i in range(20,60)]
        self.assertEqual(self.run_samples(rows)[-1]['level'],2)
    def test_invalid_capabilities_atomic(self):
        p=QualityPolicy();before=dict(p.__dict__)
        with self.assertRaises(ValueError):p.step(s(0,30),capabilities={'msaa_samples':'invalid'})
        self.assertEqual(p.__dict__,before)
        self.assertEqual(p.step(s(0,30),capabilities=CAPS)['state'],'PRESSURED')
    def test_output_does_not_mutate_other_instances(self):
        first=QualityPolicy().step(s(0));first['recommendation']['postprocess'].clear()
        self.assertEqual(QualityPolicy().step(s(0))['recommendation']['postprocess'],['tone_map','bloom'])
    def test_invalid_foreground_is_atomic(self):
        p=QualityPolicy()
        with self.assertRaises(ValueError):p.step(s(0,foreground='false'))
        self.assertEqual(p.last_t,-1)
if __name__=='__main__':unittest.main()
