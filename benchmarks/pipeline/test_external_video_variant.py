"""External camera/decoder sampler preflight, not an EGL or video-device test."""
from gzip import decompress
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'tools'))
from coverage.capability import CapabilityNegotiator


class ExternalVideoVariantTests(unittest.TestCase):
    def test_variant_and_negotiator_agree_on_both_external_dependencies(self):
        base = 'GL_OES_EGL_image_external'
        essl3 = 'GL_OES_EGL_image_external_essl3'
        catalog = json.loads(decompress((ROOT / 'references/coverage/gles-api-catalog.json.gz').read_bytes()))
        with tempfile.TemporaryDirectory() as directory:
            manifest = Path(directory) / 'video.json'
            for extensions, missing in (([essl3], [base]), ([base], [essl3]), ([], [base, essl3]), ([base, essl3], [])):
                with self.subTest(extensions=extensions):
                    manifest.write_text(json.dumps({'gles': '3.0', 'features': ['external_texture'],
                        'extensions': extensions, 'required_extensions': [], 'quality': 'medium'}),
                        encoding='utf-8')
                    result = subprocess.run([sys.executable, str(ROOT / 'benchmarks/pipeline/variants.py'), str(manifest)],
                        cwd=ROOT, capture_output=True, encoding='utf-8', timeout=15, check=False)
                    self.assertEqual(result.returncode, int(bool(missing)), result.stderr)
                    self.assertEqual(json.loads(result.stdout)['errors'], ['MISSING_EXTENSION:' + item for item in missing])
                    capability = CapabilityNegotiator(catalog, '3.0', extensions, ['glEGLImageTargetTexture2DOES'])
                    observed = capability.priority('external_texture', egl_version='1.5',
                        egl_extensions=['EGL_KHR_image_base'], essl_version='3.00', probe_pass=True)
                    self.assertIs(observed['usable'], not missing)

    def test_ordinary_2d_fallback_has_no_external_extension_requirement(self):
        with tempfile.TemporaryDirectory() as directory:
            manifest = Path(directory) / 'fallback.json'
            manifest.write_text('{"gles":"3.0","features":["unlit"],"extensions":[],"quality":"medium"}', encoding='utf-8')
            result = subprocess.run([sys.executable, str(ROOT / 'benchmarks/pipeline/variants.py'), str(manifest)],
                cwd=ROOT, capture_output=True, encoding='utf-8', timeout=15, check=False)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(json.loads(result.stdout), {'errors': []})
