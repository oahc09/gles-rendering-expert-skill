"""Oracle tests run without a GL context; actual runtime is separately required."""
import copy
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest

spec = importlib.util.spec_from_file_location('pipeline_runtime', Path(__file__).with_name('runtime.py'))
runtime = importlib.util.module_from_spec(spec)
spec.loader.exec_module(runtime)


class RuntimeReferences(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        runtime.write_references(self.root)

    def tearDown(self):
        self.temp.cleanup()

    def mutate_manifest(self, callback):
        path = self.root / 'manifest.json'
        manifest = json.loads(path.read_text())
        callback(manifest)
        path.write_text(json.dumps(manifest))

    def test_complete_independent_inventory(self):
        self.assertEqual(len(runtime.validate_references(self.root)['images']), 6)

    def test_committed_references_match_oracle(self):
        runtime.validate_references(Path(__file__).with_name('goldens'))

    def test_missing_reference_rejected(self):
        self.mutate_manifest(lambda m: m['images'].pop('C01'))
        with self.assertRaises(ValueError):
            runtime.validate_references(self.root)

    def test_extra_reference_rejected(self):
        self.mutate_manifest(lambda m: m['images'].update(C07=copy.deepcopy(m['images']['C01'])))
        with self.assertRaises(ValueError):
            runtime.validate_references(self.root)

    def test_traversal_rejected(self):
        self.mutate_manifest(lambda m: m['images']['C01'].update(file='../C01.ppm'))
        with self.assertRaises(ValueError):
            runtime.validate_references(self.root)

    def test_tolerance_inflation_rejected(self):
        self.mutate_manifest(lambda m: m['images']['C01'].update(max_channel_error_u8=255))
        with self.assertRaises(ValueError):
            runtime.validate_references(self.root)

    def test_tamper_rejected_even_with_updated_hash(self):
        path = self.root / 'C01.ppm'
        pixels = bytearray(runtime.reference('C01'))
        pixels[0] ^= 127
        runtime.visual.write_ppm(path, runtime.SIZE, runtime.SIZE, pixels)
        self.mutate_manifest(lambda m: m['images']['C01'].update(sha256=runtime.digest(path)))
        with self.assertRaises(ValueError):
            runtime.validate_references(self.root)

    def test_identical_pixels_pass(self):
        pixels = runtime.reference('C03')
        self.assertTrue(runtime.compare_pixels(pixels, pixels, 0)['pass'])

    def test_single_pixel_regression_rejected(self):
        pixels = runtime.reference('C01')
        bad = bytearray(pixels)
        bad[20] = (bad[20] + 20) % 256
        self.assertFalse(runtime.compare_pixels(bad, pixels, 2)['pass'])

    def test_truncated_pixels_rejected(self):
        with self.assertRaises(ValueError):
            runtime.compare_pixels(b'123', b'123', 0)

    def test_quantization_is_clamped(self):
        self.assertEqual(runtime.quantize(2), 255)
        self.assertEqual(runtime.quantize(-1), 0)
        self.assertEqual(runtime.quantize(.5), 128)

    def test_srgb_known_boundary_and_inverse(self):
        self.assertAlmostEqual(runtime.srgb_decode(.04045), .00313080495)
        for value in (0, .001, .02, .5, 1):
            self.assertAlmostEqual(runtime.srgb_decode(runtime.srgb_encode(value)), value, places=7)

    def test_hdr_oracle_retains_highlights(self):
        image = runtime.reference('C03')
        self.assertGreater(image[31 * 3], 220)
        self.assertGreater(image[31 * 3], runtime.quantize(.5))

    def test_six_scenes_are_independent(self):
        self.assertEqual(len(set(runtime.reference(scene) for scene in runtime.SCENES)), 6)

    def test_unknown_scene_rejected(self):
        with self.assertRaises(ValueError):
            runtime.reference('UNKNOWN')


if __name__ == '__main__':
    unittest.main()
