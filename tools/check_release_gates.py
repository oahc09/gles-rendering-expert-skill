"""Validate truthful candidate bookkeeping; --require-release enforces all gates."""
import argparse
import json
import re
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
ALLOWED = {'PASS', 'PARTIAL', 'BLOCKED_BY_HARDWARE', 'BLOCKED_BY_PROVIDER', 'NOT_RUN'}

def require(condition, message):
    if not condition:
        raise AssertionError(message)

def check(data, skill, previous=None, ancestor=None, oldest=None, origin=None):
    require(data['target_version'] in ('1.0.3', '1.0.4', '1.0.5', '1.0.6', '1.0.7'), 'Gate validation failed')
    require(set(data['work_packages']) == {f'W{i}' for i in range(10 if data['target_version']=='1.0.7' else 11 if data['target_version']=='1.0.6' else 9 if data['target_version']=='1.0.5' else 8)}, 'Gate validation failed')
    for key, item in data['work_packages'].items():
        require(item['status'] in ALLOWED, key)
        require(item['implementation'] and item['acceptance'] and item['remaining'], key)
        for path in item['implementation']:
            require((ROOT / path).exists(), (key, path))
    unreleased_metadata = '1.0.2'
    ready = all((item['status'] == 'PASS' for item in data['work_packages'].values()))
    if data['target_version'] == '1.0.4':
        require(previous is not None, 'v1.0.4 requires preserved prior release gates')
        require(data.get('prior_release_gate') == 'docs/release-gates.json', 'Do not replace prior gates')
        require(not data.get('accepted_limitations'), 'No maintainer risk waiver was authorized for this candidate')
        require(previous.get('target_version') == '1.0.3', 'Prior gates must describe v1.0.3')
        require(set(previous.get('work_packages', {})) == {f'W{i}' for i in range(8)}, 'Prior work packages incomplete')
        for key, item in previous['work_packages'].items():
            require(item.get('status') in ALLOWED, 'Invalid prior status: ' + key)
            require(bool(item.get('implementation')) and bool(item.get('acceptance')) and bool(item.get('remaining')), 'Incomplete prior evidence fields: ' + key)
        prior_ready = all(item['status'] == 'PASS' for item in previous['work_packages'].values())
        require(previous.get('release_ready') is prior_ready, 'Prior release flag contradicts prior work packages')
        if prior_ready:
            require(previous.get('metadata_version') == '1.0.3', 'Prior accepted release must have v1.0.3 metadata')
            unreleased_metadata = '1.0.3'
        ready = ready and prior_ready
    if data['target_version'] == '1.0.5':
        require(previous is not None and previous.get('target_version') == '1.0.4', 'v1.0.5 requires exact v1.0.4 predecessor')
        require(ancestor is not None and ancestor.get('target_version') == '1.0.3', 'v1.0.5 requires v1.0.3 ancestor')
        require(data.get('prior_release_gate') == 'docs/v1.0.4-release-gates.json', 'Do not replace predecessor gates')
        require(not data.get('accepted_limitations'), 'No risk waiver authorized')
        require(type(data.get('release_authorized')) is bool, 'Explicit release authorization flag required')
        prior_ready = check(previous, 'version: '+str(previous.get('metadata_version')), ancestor)
        unreleased_metadata = previous['metadata_version']
        ready = ready and prior_ready and data['release_authorized']
    if data['target_version'] == '1.0.6':
        require(previous is not None and previous.get('target_version') == '1.0.5', 'v1.0.6 requires exact v1.0.5 predecessor')
        require(ancestor is not None and ancestor.get('target_version') == '1.0.4', 'v1.0.6 requires exact v1.0.4 ancestor')
        require(oldest is not None and oldest.get('target_version') == '1.0.3', 'v1.0.6 requires exact v1.0.3 origin')
        require(data.get('prior_release_gate') == 'docs/v1.0.5/release-gates.json', 'Do not replace prior gates')
        require(not data.get('accepted_limitations'), 'No risk waiver authorized')
        require(type(data.get('release_authorized')) is bool, 'Explicit release authorization flag required')
        prior_ready = check(previous, 'version: '+str(previous.get('metadata_version')), ancestor, oldest)
        unreleased_metadata = previous['metadata_version']
        ready = ready and prior_ready and data['release_authorized']
    if data['target_version'] == '1.0.7':
        require(previous is not None and previous.get('target_version') == '1.0.6', 'v1.0.7 requires exact v1.0.6 predecessor')
        require(ancestor is not None and ancestor.get('target_version') == '1.0.5', 'v1.0.7 requires exact v1.0.5 ancestor')
        require(oldest is not None and oldest.get('target_version') == '1.0.4', 'v1.0.7 requires exact v1.0.4 ancestor')
        require(origin is not None and origin.get('target_version') == '1.0.3', 'v1.0.7 requires exact v1.0.3 origin')
        require(data.get('prior_release_gate') == 'docs/v1.0.6/release-gates.json', 'Do not replace prior gates')
        require(not data.get('accepted_limitations'), 'No risk waiver authorized')
        require(type(data.get('release_authorized')) is bool, 'Explicit release authorization flag required')
        prior_ready = check(previous, 'version: '+str(previous.get('metadata_version')), ancestor, oldest, origin)
        unreleased_metadata = previous['metadata_version']
        ready = ready and prior_ready and data['release_authorized']
    match = re.search('^\\s*version:\\s*[\\"\\\']?([0-9]+\\.[0-9]+\\.[0-9]+)', skill, re.M)
    require(match, 'SKILL metadata version missing')
    if not ready:
        require(match.group(1) == unreleased_metadata, 'Do not bump before all gates pass')
        require(data['release_ready'] is False, 'Gate validation failed')
    if ready:
        require(match.group(1) == data['target_version'], 'Accepted release must use target metadata version')
    require(data['metadata_version'] == match.group(1), 'Gate metadata version differs from SKILL')
    require(data['release_ready'] == ready, 'Release flag must reflect all gates')
    return ready

def main():
    p = argparse.ArgumentParser()
    p.add_argument('--require-release', action='store_true')
    p.add_argument('--gates', choices=['v1.0.3', 'v1.0.4', 'v1.0.5', 'v1.0.6', 'v1.0.7'], default='v1.0.3')
    args = p.parse_args()
    previous = json.loads((ROOT / 'docs/release-gates.json').read_text())
    if args.gates == 'v1.0.7':
        data = json.loads((ROOT / 'docs/v1.0.7-release-gates.json').read_text())
        predecessor = json.loads((ROOT / 'docs/v1.0.6/release-gates.json').read_text())
        ancestor = json.loads((ROOT / 'docs/v1.0.5/release-gates.json').read_text())
        oldest = json.loads((ROOT / 'docs/v1.0.4-release-gates.json').read_text())
        ready = check(data, (ROOT / 'SKILL.md').read_text(), predecessor, ancestor, oldest, previous)
    elif args.gates == 'v1.0.6':
        data = json.loads((ROOT / 'docs/v1.0.6/release-gates.json').read_text())
        predecessor = json.loads((ROOT / 'docs/v1.0.5/release-gates.json').read_text())
        ancestor = json.loads((ROOT / 'docs/v1.0.4-release-gates.json').read_text())
        ready = check(data, (ROOT / 'SKILL.md').read_text(), predecessor, ancestor, previous)
    elif args.gates == 'v1.0.5':
        data = json.loads((ROOT / 'docs/v1.0.5/release-gates.json').read_text())
        predecessor = json.loads((ROOT / 'docs/v1.0.4-release-gates.json').read_text())
        ready = check(data, (ROOT / 'SKILL.md').read_text(), predecessor, previous)
    else:
        data = previous if args.gates == 'v1.0.3' else json.loads((ROOT / 'docs/v1.0.4-release-gates.json').read_text())
        ready = check(data, (ROOT / 'SKILL.md').read_text(), previous if args.gates == 'v1.0.4' else None)
    print(json.dumps({'candidate_bookkeeping': 'PASS', 'release_ready': ready, 'blocked_work_packages': {key: item['status'] for key, item in data['work_packages'].items() if item['status'] != 'PASS'}, 'note': 'Bookkeeping PASS is NOT release acceptance.'}, indent=2))
    return 0 if ready or not args.require_release else 2
if __name__ == '__main__':
    raise SystemExit(main())
