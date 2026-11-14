import copy, tempfile, unittest
from pathlib import Path
from unittest.mock import patch
import shader_pipeline as p

class PipelineTests(unittest.TestCase):
    def setUp(self):self.case,self.broken=p.fixture('ssbo-add');self.good=self.case['sources']['shader.comp']
    def test_inventory(self):self.assertEqual(len(p.inventory()),4)
    def test_frozen_expression_envelope(self):
        self.assertEqual(p.validate_patch(self.case,self.good)['sources'],self.case['sources'])
        for s in (self.good.replace('local_size_x=1','local_size_x=2'),self.good.replace('2.0+3.0','while(true){}'),self.good.replace('2.0+3.0','value'),self.good+'x'):
            with self.assertRaises(ValueError):p.validate_patch(self.case,s)
    def test_patch_quota(self):
        with self.assertRaises(ValueError):p.validate_patch(self.case,'x'*4097)
    def test_missing_compiler_closed(self):
        with tempfile.TemporaryDirectory() as t:
            r=p.run('ssbo-add',self.good,'/missing',[],Path(t)/'report')
            self.assertEqual(r['host_status'],'BLOCKED_BY_TOOLCHAIN');self.assertEqual(r['provider_status'],'BLOCKED_BY_PROVIDER')
    def test_config_requires_two_implementations(self):
        for c in ([],[{'kind':'mesa'}]*2,[{'kind':'mesa'},{'kind':'angle','command':'bad'}]):
            with self.assertRaises((ValueError,FileNotFoundError)):p.validate_configs(c)
    def test_never_accepts_missing_driver(self):
        with self.assertRaises(FileNotFoundError):p.validate_configs([dict(kind='mesa',egl='/missing',gles='/missing'),dict(kind='angle',egl='/missing2',gles='/missing2',icd='/missing2')])
    def test_output_not_overwritten(self):
        with tempfile.TemporaryDirectory() as t:
            with self.assertRaises(FileExistsError):p.run('ssbo-add',self.good,None,[],Path(t))
    def test_original_corruption_is_fixed(self):
        self.assertIn('undefined_input',self.broken['sources']['shader.comp']);self.assertNotIn('undefined_input',self.good)

if __name__=='__main__':unittest.main()
