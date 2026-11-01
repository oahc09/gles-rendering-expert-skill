import importlib.util
from pathlib import Path
import unittest
p=Path(__file__).resolve().parents[2]/'examples/texture_pipeline/policy.py'
s=importlib.util.spec_from_file_location('policy',p);policy=importlib.util.module_from_spec(s);s.loader.exec_module(policy)
class PipelineTests(unittest.TestCase):
    def test_target_capabilities_not_brand(self):
        self.assertEqual(policy.texture_target(3,['GL_KHR_texture_compression_astc_ldr']),'astc')
        self.assertEqual(policy.texture_target(3,[]),'etc2')
        self.assertEqual(policy.texture_target(2,[]),'rgba')
        self.assertEqual(policy.texture_target(3,['GL_KHR_texture_compression_astc_ldr'],['astc']),'etc2')
        self.assertEqual(policy.texture_target(3,[],['etc2']),'rgba')
        self.assertIsNone(policy.texture_target(2,[],['rgba']))
        self.assertEqual(policy.texture_target(2,['GL_KHR_texture_compression_astc_ldr_FAKE']),'rgba')
    def test_invalid_capability_inputs(self):
        for major in (-1,0,1,4,True,'3',None):
            with self.subTest(major=major),self.assertRaises(ValueError):policy.texture_target(major,[])
        for extensions in ([None],[1],[''],['GL_A GL_B'],'GL_A'):
            with self.subTest(extensions=extensions),self.assertRaises(ValueError):policy.texture_target(3,extensions)
        for denied in (['bad'],[None],'astc'):
            with self.subTest(denied=denied),self.assertRaises(ValueError):policy.texture_target(3,[],denied)
    def test_yuv_neutral_black_white(self):
        for matrix in ('BT601','BT709','BT2020'):
            self.assertEqual(policy.yuv_rgb(16/255,128/255,128/255,matrix), (0,0,0))
            self.assertEqual(policy.yuv_rgb(235/255,128/255,128/255,matrix), (1,1,1))
            self.assertEqual(policy.yuv_rgb(0,128/255,128/255,matrix,False), (0,0,0))
    def test_yuv_metadata_changes_result(self):
        self.assertNotEqual(policy.yuv_rgb(.5,.4,.7,'BT601'),policy.yuv_rgb(.5,.4,.7,'BT709'))
        self.assertNotEqual(policy.yuv_rgb(.5,.4,.7,'BT709'),policy.yuv_rgb(.5,.4,.7,'BT709',False))
        with self.assertRaises(ValueError):policy.yuv_rgb(float('nan'),0,0,'BT709')
    def test_external_missing_extension_safe(self):
        m=dict(protected=False,rotation=0,matrix='BT709',range='limited',transfer='SDR',source='SurfaceTexture')
        self.assertEqual(policy.video_path(m,[],[])['path'],'UNSUPPORTED_EXTERNAL')
        ex=['GL_OES_EGL_image_external','GL_OES_EGL_image_external_essl3']
        self.assertEqual(policy.video_path(m,ex,[])['path'],'EXTERNAL_ESSL3')
        m['matrix']='unknown'
        with self.assertRaises(ValueError):policy.video_path(m,ex,[])
    def test_protected_never_stages(self):
        for gl,egl in (([],[]),(['GL_EXT_protected_textures'],['EGL_EXT_protected_content'])):
            result=policy.video_path({'protected':True},gl,egl)
            self.assertEqual(result['path'],'BLOCKED_PROTECTED_PIPELINE');self.assertFalse(result['readback']);self.assertFalse(result['plaintext_export'])
    def test_rotation(self):
        self.assertEqual(policy.rotate_uv(.2,.3,90),(.3,.8))
        self.assertEqual(policy.rotate_uv(.2,.3,180),(.8,.7))
        self.assertEqual(policy.rotate_uv(.2,.3,270),(.7,.2))
    def test_activity_wires_guard_before_producers(self):
        source=(Path(__file__).resolve().parents[2]/'examples/android_cases/surfacevideo/src/main/java/org/example/gleslab/ExternalSurfaceActivity.java').read_text()
        self.assertLess(source.index('if(protectedRequested)'),source.index('if(ahbRequested&&ahb.create())'))
        self.assertLess(source.index('VideoInputGuard.select'),source.index('consumer=new SurfaceTexture'))
        self.assertIn('VideoInputGuard.acquireFrame(consumer,transform,0,true)',source)
        self.assertNotIn('yuv_rgb',source)
    def test_hdr_needs_explicit_tonemap(self):
        m=dict(protected=False,rotation=0,matrix='BT2020',range='limited',transfer='PQ',source='SurfaceTexture')
        self.assertEqual(policy.video_path(m,[],[])['path'],'BLOCKED_HDR_TONEMAP_REQUIRED')
if __name__=='__main__':unittest.main()
