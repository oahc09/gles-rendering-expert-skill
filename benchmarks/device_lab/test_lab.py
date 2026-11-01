import copy
import unittest
from lab import validate
from compare import compare

def fixture():
    return {'status':'CAPTURED','snapshot':{'build':'synthetic','platform':'host','os':'test','os_build':'test','api_level':None,'device':'fixture-not-real','backend':'software','backend_evidence':{'kind':'controlled_creation'},'hardware_kind':'software','egl_vendor':'fixture','egl_version':'1.5','egl_extensions':[],'gl_vendor':'fixture','gl_renderer':'fixture','gl_version':'3.1','glsl_version':'310 es','gl_extensions':[],'precision':{},'limits':{'max_texture_size':2048},'formats':{'RGBA8':True},'function_entries':{},'runtime_import_probes':{'AHardwareBuffer':None},'context_generation':1,'surface_generation':1},'correctness_events':[{'case':'synthetic-control','status':'PASS'}]}
class LabTests(unittest.TestCase):
    def test_canonical_fingerprint_stable(self):
        a=fixture();b=copy.deepcopy(a);b['snapshot']['surface_generation']=2
        self.assertEqual(validate(a,{'platform':'host','backend':'software'})['fingerprint'],validate(b,{'platform':'host','backend':'software'})['fingerprint'])
    def test_driver_changes_fingerprint(self):
        a=fixture();b=copy.deepcopy(a);b['snapshot']['gl_version']='3.2'
        self.assertNotEqual(validate(a,{'platform':'host','backend':'software'})['fingerprint'],validate(b,{'platform':'host','backend':'software'})['fingerprint'])
    def test_substring_evidence_rejected(self):
        a=fixture();a['snapshot']['backend_evidence']['kind']='renderer_substring'
        with self.assertRaises(ValueError):validate(a,{'platform':'host','backend':'software'})
    def test_failed_correctness_rejected(self):
        a=fixture();a['correctness_events'][0]['status']='FAIL'
        with self.assertRaises(ValueError):validate(a,{'platform':'host','backend':'software'})
    def test_missing_precision_rejected(self):
        a=fixture();del a['snapshot']['precision']
        with self.assertRaises(ValueError):validate(a,{'platform':'host','backend':'software'})
    def test_silent_fallback_rejected(self):
        with self.assertRaises(ValueError):validate(fixture(),{'platform':'host','backend':'angle_vulkan'})
    def test_nan_limit_rejected(self):
        a=fixture();a['snapshot']['limits']['max_texture_size']=float('nan')
        with self.assertRaises(ValueError):validate(a,{'platform':'host','backend':'software'})
    def test_software_not_target_pair(self):self.assertEqual(compare(fixture(),fixture())['status'],'NOT_TARGET_PAIR')
    def test_pair_still_not_acceptance(self):
        a=fixture();b=fixture()
        for c,backend in [(a,'native'),(b,'angle_vulkan')]:c['snapshot'].update(platform='Android',backend=backend,hardware_kind='physical')
        self.assertEqual(compare(a,b)['status'],'PAIRED_CAPTURE_REVIEW_REQUIRED');self.assertFalse(compare(a,b)['acceptance'])
    def test_different_device_no_pair(self):
        a=fixture();b=fixture();b['snapshot']['device']='other';self.assertFalse(compare(a,b)['same_device'])
if __name__=='__main__':unittest.main()
