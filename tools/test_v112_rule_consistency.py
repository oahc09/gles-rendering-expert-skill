"""Make the v1.1.2 opt-in rule CLI part of the existing tools discovery."""
import json
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
INPUTS = (
    'tools/validate_rules.py', 'tools/rule_consistency_v112.py',
    'benchmarks/rules/catalog.json', 'benchmarks/rules/cases.json', 'benchmarks/rules/inventory.md',
    'docs/v1.1.2/rule-index.json', 'docs/v1.1.2/rule-cases.json',
    'SKILL.md', '.cursorrules', 'agents/openai.yaml', 'agents/claude-code.yaml',
)


def run(root, report):
    return subprocess.run(
        [sys.executable, str(root / 'tools/validate_rules.py'), '--v112', '--output', str(report)],
        cwd=root, capture_output=True, encoding='utf-8', timeout=30, check=False,
    )


class V112RuleConsistencyCLI(unittest.TestCase):
    def test_cli_writes_passing_v112_report(self):
        with tempfile.TemporaryDirectory() as work:
            report = Path(work) / 'rules.json'
            result = run(ROOT, report)
            self.assertEqual(result.returncode, 0, result.stderr)
            receipt = json.loads(report.read_text(encoding='utf-8'))
        self.assertEqual(receipt['failed'], [])
        self.assertEqual(receipt['v112']['rules'], 6)
        self.assertEqual(receipt['v112']['cases'], 29)
        self.assertEqual(receipt['v112']['failed'], [])

    def test_cli_rejects_rule_drift_in_one_entry(self):
        with tempfile.TemporaryDirectory() as work:
            root = Path(work)
            for relative in INPUTS:
                target = root / relative
                target.parent.mkdir(parents=True, exist_ok=True)
                shutil.copyfile(ROOT / relative, target)
            entry = root / 'agents/openai.yaml'
            contents = entry.read_bytes()
            old = b'P112-ATTACHMENT: MUST preserve attachment contents'
            self.assertEqual(contents.count(old), 1)
            entry.write_bytes(contents.replace(old, b'P112-ATTACHMENT: MAY discard attachment contents'))
            report = root / 'report.json'
            result = run(root, report)
            self.assertNotEqual(result.returncode, 0)
            self.assertIn('rule P112-ATTACHMENT drift: agents/openai.yaml', result.stderr)
            self.assertFalse(report.exists())
