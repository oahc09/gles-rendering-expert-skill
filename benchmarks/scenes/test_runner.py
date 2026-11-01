import tempfile
import unittest
from pathlib import Path
import run

class ImageContractTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup);self.root=Path(self.tmp.name)
    def image(self,name,data=b'\x10\x20\x30',header=b'P6\n1 1\n255\n'):
        p=self.root/name;p.write_bytes(header+data);return p
    def test_equal(self):self.assertTrue(run.compare(self.image('a'),self.image('b'))['pass'])
    def test_small_tolerance(self):self.assertTrue(run.compare(self.image('a'),self.image('b',b'\x11\x21\x31'))['pass'])
    def test_visible_regression(self):self.assertFalse(run.compare(self.image('a'),self.image('b',b'\xff\xff\xff'))['pass'])
    def test_truncated_rejected(self):
        with self.assertRaises(ValueError):run.read_ppm(self.image('a',b'\x10'))
    def test_trailing_rejected(self):
        with self.assertRaises(ValueError):run.read_ppm(self.image('a',b'\x10'*4))
    def test_wrong_magic(self):
        with self.assertRaises(ValueError):run.read_ppm(self.image('a',header=b'P3\n1 1\n255\n'))
    def test_mismatched_dimensions(self):
        with self.assertRaises(ValueError):run.compare(self.image('a'),self.image('b',b'\x10'*6,b'P6\n2 1\n255\n'))
    def test_size_limit(self):
        with self.assertRaises(ValueError):run.read_ppm(self.image('a',header=b'P6\n99999 1\n255\n'))
    def test_golden_inventory(self):
        import json
        m=json.loads((run.GOLDEN/'manifest.json').read_text());self.assertEqual(set(m['images']),set(run.SCENES))
        for s in run.SCENES:self.assertEqual(run.digest(run.GOLDEN/(s+'.ppm')),m['images'][s]['sha256'])
    def test_capability_exit_is_not_pass(self):
        import sys
        p=self.root/'blocked';p.write_text('#!/bin/sh\necho BLOCKED_BY_CAPABILITY >&2\nexit 3\n');p.chmod(0o755)
        with self.assertRaises(run.CapabilityBlocked):run.execute(p,'S01',self.root/'out',96,64,'baseline')
    def test_shader_to_api_buffer_update_guard(self):
        source=(run.ROOT/'examples/scenes/scene_lab.cpp').read_text()
        block=source[source.index('static void compute_draw'):source.index('static void gaussian')]
        self.assertIn('glMemoryBarrier(GL_BUFFER_UPDATE_BARRIER_BIT)',block)
        self.assertLess(block.index('glMemoryBarrier(GL_BUFFER_UPDATE_BARRIER_BIT)'),block.index('glBindBuffer(GL_DRAW_INDIRECT_BUFFER, indirect)'))
    def test_crash_is_not_visual_rejection(self):
        p=self.root/'crash';p.write_text('#!/bin/sh\nexit 139\n');p.chmod(0o755)
        with self.assertRaises(RuntimeError):run.execute(p,'S01',self.root/'out',96,64,'degraded')

if __name__=='__main__':unittest.main()
