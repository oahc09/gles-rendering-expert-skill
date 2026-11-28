#!/usr/bin/env python3
"""Six normalized advice contracts; no GPU execution or model coverage claim."""
import json
from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[1]
INDEX = ROOT / 'docs/v1.1.2/rule-index.json'
CASES = ROOT / 'docs/v1.1.2/rule-cases.json'
ENTRIES = ('SKILL.md', '.cursorrules', 'agents/openai.yaml', 'agents/claude-code.yaml')

CHECKS = {
    'P112-ATTACHMENT': lambda x: x['action'] == 'preserve' or (x['action'] == 'invalidate' and x['live'] == 'dead'),
    'P112-DELETE': lambda x: (x['action'] == 'delete' and x['context'] == 'compatible' and x['generation'] == 'same') or (x['action'] == 'queue' and x['context'] in ('unavailable', 'incompatible') and x['generation'] == 'same') or (x['action'] == 'drop' and x['generation'] == 'lost'),
    'P112-PRECISION': lambda x: x['declared'] and x['supported'] and x['range_fits'] and x['error_fits'],
    'P112-VIDEO': lambda x: (x['action'] == 'import' and x['target'] == 'external' and x['extension']) or (x['action'] == 'upload' and x['target'] == '2d' and x['cpu_access'] and x['layout_valid']),
    'P112-MSAA': lambda x: x['configuration_valid'] and ((x['route'] == 'core' and x['gles'] >= 30) or (x['route'] == 'extension' and x['extension'] and x['entrypoint'])),
    'P112-DEPTH': lambda x: x['action'] == 'keep-baseline' or (x['action'] == 'adopt' and x['measured_on_target'] and x['quality_match'] and x['gain']),
}


def run():
    index = json.loads(INDEX.read_text(encoding='utf-8'))
    cases = json.loads(CASES.read_text(encoding='utf-8'))
    catalog = {r['rule_id'] for r in json.loads((ROOT / 'benchmarks/rules/catalog.json').read_text(encoding='utf-8'))}
    rule_ids = [rule['id'] for rule in index['rules']]
    if index['schema_version'] != 1 or tuple(index['entries']) != ENTRIES or len(set(rule_ids)) != len(rule_ids) or set(rule_ids) != set(CHECKS):
        raise ValueError('invalid rule index')
    for rule in index['rules']:
        if not rule['primary_sources'] or not set(rule['related_base_rule_ids']) <= catalog:
            raise ValueError(f"unmapped primary sources/base rules: {rule['id']}")
        expected = f"- {rule['id']}: {rule['instruction']}"
        for entry in ENTRIES:
            lines = (ROOT / entry).read_text(encoding='utf-8').splitlines()
            if entry == 'agents/openai.yaml':
                lines = [line.removeprefix('# ') for line in lines]
            rendered = f"- '{expected[2:].replace(chr(39), chr(39) * 2)}'" if entry.endswith('claude-code.yaml') else expected
            matching = [line.strip() for line in lines if re.match(rf"^\s*- '?{rule['id']}:", line)]
            if matching != [rendered]:
                raise ValueError(f"rule {rule['id']} drift: {entry}")
    cases_by_id = {case['id']: case for case in cases}
    if len(cases_by_id) != len(cases):
        raise ValueError('duplicate case IDs')
    for rule_id in CHECKS:
        cases_for_rule = [case for case in cases if case['rule'] == rule_id]
        if {case['valid'] for case in cases_for_rule} != {True, False}:
            raise ValueError(f'missing positive/negative behavior: {rule_id}')
    failures = [case['id'] for case in cases if CHECKS[case['rule']](case['scenario']) is not case['valid']]
    return {'scope': 'entry alignment and normalized advice only', 'rules': len(CHECKS), 'cases': len(cases), 'failed': failures}
