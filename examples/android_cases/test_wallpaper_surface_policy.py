"""Host policy execution and Java integration checks; not Android or device EGL proof."""
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parent / 'wallpaper'
JAVA = ROOT / 'src/main/java/org/example/gleslab'
SOURCE = (JAVA / 'IslandWallpaper.java').read_text()


class WallpaperSurfaceTest(unittest.TestCase):
    def test_real_qualified_host_policy(self):
        java = shutil.which('java')
        if not java:
            self.skipTest('Java runtime not available')
        javac = shutil.which('javac')
        if javac:
            compiler = [javac, '--release', '17']
        else:
            modules = subprocess.run([java, '--list-modules'], capture_output=True, text=True, timeout=10)
            if modules.returncode != 0 or 'jdk.compiler@' not in modules.stdout:
                self.skipTest('Java compiler module not available')
            compiler = [java, '-m', 'jdk.compiler/com.sun.tools.javac.Main',
                        '-source', '17', '-target', '17', '-Xlint:-options']
        with tempfile.TemporaryDirectory() as t:
            compiled = subprocess.run(compiler + ['-d', t, str(JAVA / 'WallpaperSurfacePolicy.java'),
                                                  str(ROOT / 'tests/WallpaperSurfacePolicyTest.java')],
                                      capture_output=True, text=True, timeout=30)
            self.assertEqual(compiled.returncode, 0, compiled.stderr)
            result = subprocess.run([java, '-cp', t, 'org.example.gleslab.WallpaperSurfacePolicyTest'],
                                    capture_output=True, text=True, timeout=30)
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertIn('PASS: 8 owner policy cases', result.stdout)

    def test_android_owner_wires_drawable_release_without_context_reset(self):
        attach = SOURCE.split('void attach(', 1)[1].split('private void attachDrawable()', 1)[0]
        replacement = attach.split('} else if (action == WallpaperSurfacePolicy.Action.REPLACE_DRAWABLE)', 1)[1]
        self.assertIn('releaseSurface();', replacement)
        self.assertNotIn('releaseAll();', replacement)
        self.assertIn('if (action != WallpaperSurfacePolicy.Action.KEEP_DRAWABLE) attachDrawable();', replacement)
        detach = SOURCE.split('void detach()', 1)[1].split('void shutdown()', 1)[0]
        self.assertIn('releaseSurface();', detach)
        self.assertNotIn('releaseAll();', detach)
        surface_release = SOURCE.split('private void releaseSurface()', 1)[1].split('private void releaseAll()', 1)[0]
        self.assertNotIn('eglDestroyContext', surface_release)
        self.assertNotIn('program = 0', surface_release)
        lost = SOURCE.split('private void recoverLostContext()', 1)[1].split('private static final class', 1)[0]
        self.assertLess(lost.index('program = 0'), lost.index('releaseAll()'))
        self.assertEqual(lost.count('createSurface()'), 1)
        self.assertIn('if (program == 0) program = makeProgram();', SOURCE)
        self.assertIn('contextGeneration=', SOURCE)
        self.assertIn('surfaceGeneration=', SOURCE)
