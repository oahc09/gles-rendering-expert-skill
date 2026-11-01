"""Source contract guards only; native compilation evidence is separately recorded."""
from pathlib import Path
import unittest

ROOT=Path(__file__).parent
CPP=(ROOT/'surfacevideo/src/main/cpp/ahb_texture.cpp').read_text()
JAVA=(ROOT/'surfacevideo/src/main/java/org/example/gleslab/NativeHardwareBufferDisplay.java').read_text()

class AhbContractTests(unittest.TestCase):
    def test_strict_extension_gate(self):
        for name in ('EGL_ANDROID_get_native_client_buffer','EGL_ANDROID_image_native_buffer','EGL_KHR_image_base','GL_OES_EGL_image'):
            self.assertIn(name,CPP)
    def test_allocation_ownership_and_stride(self):
        self.assertIn('AHardwareBuffer_allocate',CPP);self.assertIn('AHardwareBuffer_release',CPP)
        self.assertIn('desc.stride',CPP);self.assertIn('AHARDWAREBUFFER_USAGE_CPU_WRITE_OFTEN',CPP)
    def test_cpu_unlock_is_synchronous(self):self.assertIn('AHardwareBuffer_unlock(owner->buffer, nullptr)',CPP)
    def test_import_has_no_context(self):self.assertRegex(CPP,r'EGL_NO_CONTEXT,\s*EGL_NATIVE_BUFFER_ANDROID')
    def test_gl_completion_before_delete(self):
        self.assertLess(CPP.index('glFinish()'),CPP.index('glDeleteTextures'))
    def test_private_handle_reset_after_release(self):
        self.assertIn('nativeRelease(handle,false)',JAVA)
        self.assertIn('handle=0;program=0;owner=EGL14.EGL_NO_CONTEXT',JAVA)
    def test_pattern_failure_falls_back(self):self.assertIn('if(!nativeCheckPattern(handle))',JAVA)
    def test_pack_state_not_assumed(self):
        for name in ('GL_PIXEL_PACK_BUFFER_BINDING','GL_PACK_ROW_LENGTH','GL_PACK_SKIP_ROWS','GL_PACK_SKIP_PIXELS'):self.assertIn(name,CPP)
    def test_16k_link_flag(self):self.assertIn('max-page-size=16384',(ROOT/'surfacevideo/src/main/cpp/CMakeLists.txt').read_text())

if __name__=='__main__':unittest.main()
