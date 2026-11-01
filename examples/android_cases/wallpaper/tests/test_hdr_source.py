"""Source contracts and transfer-function reference math, not device validation."""
import json
import math
from pathlib import Path
import re
import unittest
ROOT=Path(__file__).resolve().parents[1]
SOURCE=(ROOT/'src/main/java/org/example/gleslab/IslandWallpaper.java').read_text()
HELPER=(ROOT/'src/main/java/org/example/gleslab/HdrEglOutput.java').read_text()
SHADER=json.loads('"'+re.findall(r'"(#version[^"\\]*(?:\\.[^"\\]*)*)"',SOURCE)[1]+'"')
class HdrSourceTests(unittest.TestCase):
    def test_mode_specific_api_guard(self):
        self.assertIn('Build.VERSION.SDK_INT >= 34',HELPER)
        self.assertIn('display.getMode().getSupportedHdrTypes()',HELPER)
        self.assertIn('Build.VERSION.SDK_INT >= 29',SOURCE)
        self.assertIn('probeDisplay(getDisplayContext())',SOURCE)
    def test_fallback_rebuild_not_relabel(self):
        self.assertIn('releaseAll(); window = retained; forceSdr = true;',SOURCE)
        self.assertIn('ensureContext(); createSurface();',SOURCE)
        self.assertIn('if (context == EGL14.EGL_NO_CONTEXT && pq)',SOURCE)
    def test_surface_and_attachment_queries(self):
        self.assertIn('EGL14.eglQuerySurface',SOURCE)
        self.assertIn('GL_FRAMEBUFFER_ATTACHMENT_COLOR_ENCODING',SOURCE)
        self.assertIn('HdrOutputPolicy.acceptsPqSurface',SOURCE)
    def test_pq_constants_and_gamut_transform(self):
        for token in ['2610./16384.','2523./32.','3424./4096.','2413./128.','2392./128.','nits/10000.','to2020*scene*203.']:
            self.assertIn(token,SHADER)
        for nits,expected in [(100,0.5080784215),(1000,0.7518270962),(10000,1.0)]:
            p=(nits/10000)**(2610/16384)
            value=((3424/4096+(2413/128)*p)/(1+(2392/128)*p))**(2523/32)
            self.assertAlmostEqual(value,expected,places=8)
    def test_exactly_one_output_encoding(self):
        self.assertIn('outputEncoding==2',SHADER)
        self.assertIn('outputEncoding==1?mapped:srgb(mapped)',SHADER)
        self.assertIn('physicalHDR=NOT_VERIFIED',SOURCE)
    def test_foreground_reprobes(self):
        body=SOURCE[SOURCE.index('onVisibilityChanged'):SOURCE.index('private HdrEglOutput displayCapabilities')]
        self.assertIn('displayCapabilities()',body)
if __name__=='__main__':unittest.main()
