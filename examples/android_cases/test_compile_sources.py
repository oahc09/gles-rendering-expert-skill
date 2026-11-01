"""CLI infrastructure regression; these tests are not Android compile evidence."""
import importlib.util
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

SCRIPT = Path(__file__).with_name('compile_sources.py')

class SourceCompileInfrastructure(unittest.TestCase):
    def test_missing_toolchain_is_blocked_not_pass(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder); report = root/'result.json'
            result = subprocess.run([sys.executable, str(SCRIPT), '--jdk', str(root/'jdk'),
                '--ndk', str(root/'ndk'), '--android-jar', str(root/'android.jar'), '--output', str(report)],
                text=True, capture_output=True, timeout=30)
            self.assertEqual(result.returncode, 2)
            evidence = json.loads(report.read_text())
            self.assertEqual(evidence['status'], 'BLOCKED_BY_TOOLCHAIN')
            self.assertGreaterEqual(len(evidence['missing']), 4)
            self.assertEqual(evidence['checks'], [])
            self.assertEqual(evidence['device_execution'], 'NOT_RUN')

    def test_process_failure_is_preserved(self):
        spec = importlib.util.spec_from_file_location('android_source_compile', SCRIPT)
        module = importlib.util.module_from_spec(spec); spec.loader.exec_module(module)
        result = module.invoke([sys.executable, '-c', 'import sys; print("failure evidence",file=sys.stderr);sys.exit(7)'])
        self.assertEqual(result['exit_code'], 7)
        self.assertIn('failure evidence', result['stderr'])

if __name__ == '__main__':
    unittest.main()
