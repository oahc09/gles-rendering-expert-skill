#!/usr/bin/env python3
"""Validate truthful candidate bookkeeping; --require-release enforces all gates."""
import argparse
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ALLOWED = {'PASS', 'PARTIAL', 'BLOCKED_BY_HARDWARE', 'BLOCKED_BY_PROVIDER', 'NOT_RUN'}

def check(data, skill):
    assert data['target_version'] == '1.0.3'
    assert set(data['work_packages']) == {f'W{i}' for i in range(8)}
    for key, item in data['work_packages'].items():
        assert item['status'] in ALLOWED, key
        assert item['implementation'] and item['acceptance'] and item['remaining'], key
        for path in item['implementation']:
            assert (ROOT / path).exists(), (key, path)
    ready = all(item['status'] == 'PASS' for item in data['work_packages'].values())
    match = re.search(r'^\s*version:\s*[\"\']?([0-9]+\.[0-9]+\.[0-9]+)', skill, re.M)
    assert match, 'SKILL metadata version missing'
    if not ready:
        assert match.group(1) == '1.0.2', 'Do not bump before all gates pass'
        assert data['release_ready'] is False
    if ready:
        assert match.group(1) == data['target_version'], 'Accepted release must use target metadata version'
    assert data['metadata_version'] == match.group(1), 'Gate metadata version differs from SKILL'
    assert data['release_ready'] == ready, 'Release flag must reflect all gates'
    return ready

def main():
    p = argparse.ArgumentParser()
    p.add_argument('--require-release', action='store_true')
    args = p.parse_args()
    data = json.loads((ROOT/'docs/release-gates.json').read_text())
    ready = check(data, (ROOT/'SKILL.md').read_text())
    print(json.dumps({'candidate_bookkeeping':'PASS','release_ready':ready,'blocked_work_packages':{key:item['status'] for key,item in data['work_packages'].items() if item['status']!='PASS'},'note':'Bookkeeping PASS is NOT release acceptance.'},indent=2))
    return 0 if ready or not args.require_release else 2

if __name__ == '__main__':
    raise SystemExit(main())
