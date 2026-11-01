"""Structural safeguards only: NOT javac, Android compilation or device execution."""
import unittest
from pathlib import Path
import xml.etree.ElementTree as ET

ROOT=Path(__file__).parent
NS='{http://schemas.android.com/apk/res/android}'
class SourceContracts(unittest.TestCase):
    def source(self,module):
        name = 'IslandWallpaper.java' if module == 'wallpaper' else 'ExternalSurfaceActivity.java'
        return next((ROOT/module/'src/main/java').rglob(name)).read_text()
    def test_manifests_parse_and_entrypoint_exists(self):
        for module,kind in [('wallpaper','service'),('surfacevideo','activity')]:
            root=ET.parse(ROOT/module/'src/main/AndroidManifest.xml').getroot()
            name=root.find('application/'+kind).get(NS+'name')
            self.assertTrue((ROOT/module/'src/main/java'/Path(*name.split('.'))).with_suffix('.java').is_file())
    def test_gles_requirement_explicit(self):
        for module in ('wallpaper','surfacevideo'):
            node=ET.parse(ROOT/module/'src/main/AndroidManifest.xml').getroot().find('uses-feature')
            self.assertEqual(node.get(NS+'glEsVersion'),'0x00030000')
    def test_no_invented_glue_event(self):
        for module in ('wallpaper','surfacevideo'):self.assertNotIn('APP_CMD_CONTEXT_LOST',self.source(module))
    def test_surface_and_context_errors_distinct(self):
        s=self.source('wallpaper');self.assertIn('EGL14.EGL_CONTEXT_LOST',s);self.assertIn('EGL14.EGL_BAD_SURFACE',s)
    def test_owner_and_vsync(self):
        s=self.source('wallpaper');self.assertIn('new RenderLoop()',s);self.assertIn('HandlerThread',s);self.assertIn('postFrameCallback',s)
    def test_surface_destroy_waits_for_owner_ack_or_exit(self):
        s=self.source('wallpaper')
        body=s[s.index('void detach()'):s.index('void shutdown()')]
        self.assertIn('Looper.myLooper() == handler.getLooper()',body)
        self.assertIn('choreographer.removeFrameCallback(this)',body)
        self.assertIn('boolean posted = handler.post(release)',body)
        self.assertIn('while (!ownerExited && (!posted || !acknowledged[0]))',body)
        self.assertIn('ownerCompletion.wait()',body)
        self.assertIn('Thread.currentThread().interrupt()',body)
        self.assertNotIn('Thread.sleep',body)
        self.assertIn('ownerExited = true',s)
        self.assertIn('ownerCompletion.notifyAll()',s)
    def test_external_essl3_and_transform(self):
        s=self.source('surfacevideo')
        helper=next((ROOT/'surfacevideo/src/main/java').rglob('VideoInputGuard.java')).read_text()
        self.assertIn('GL_OES_EGL_image_external_essl3',s)
        self.assertIn('VideoInputGuard.acquireFrame(consumer,transform,0,true)',s)
        self.assertIn('VideoInputGuard.select',s)
        self.assertIn('GL_OES_EGL_image_external_essl3',helper)
        self.assertIn('input.updateTexImage()',helper)
        self.assertIn('input.getTransformMatrix(producer)',helper)
        self.assertLess(helper.index('input.updateTexImage()'),helper.index('input.getTransformMatrix(producer)'))
    def test_pause_stops_producer_before_consumer(self):
        s=self.source('surfacevideo');self.assertLess(s.index('renderer.stopProducer(); view.queueEvent'),s.index('view.onPause();'))
    def test_sdr_not_hdr_claim(self):self.assertIn('chosenOutput=SDR_RGBA8',self.source('surfacevideo'))
    def test_target_unrun_documented(self):self.assertIn('NOT been run on Android hardware',(ROOT/'README.md').read_text())

if __name__=='__main__':unittest.main()
