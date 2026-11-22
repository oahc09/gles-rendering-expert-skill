#!/usr/bin/env python3
"""Check historical snapshot/obligation coverage. No release or execution is authorized."""
import argparse
from hashlib import sha256
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BASE = 'cefb240d1793a4dc98174230aea15b6e0889905b'
# Digest of source paths and file hashes, computed from the exact checkout above.
BASELINE_SOURCE_SET_SHA256 = 'b3512e27dcbdd63a26c6e1afd9143db65c2f351396febe7c3671d2571277b801'
LEDGER = ROOT / 'docs/v1.1.2/obligations.json'
V111_MAP = (
    'W0 W8', 'W1 W4 W8', 'W2 W6', 'W3 W4', 'W2 W4', 'W5', 'W6', 'W4 W7',
    'W1 W3 W4', 'W3 W4 W6', 'W1 W2 W6', 'W4 W6', 'W7', 'W5 W9', 'W0 W7 W8',
)
MINIMUM = {
    'decision_scenarios': 20, 'ab_protocols': 30, 'ab_negative_controls': 10,
    'experience_cases': 50, 'experience_conflicts_or_negatives': 10, 'physical_gpu_families': 2,
    'project_tasks': 25, 'composite_reasoning_cases': 20, 'quality_tradeoffs': 12,
    'end_to_end_workloads': 8, 'workload_negative_controls': 2, 'frozen_eval_tasks': 100,
    'real_off_on_responses_per_frozen_round': 200, 'new_flagship_eval_tasks': 40,
}


def source_paths():
    docs = ROOT / 'docs'
    paths = [p for p in docs.glob('**/*gate*.json') if 'v1.1.2' not in p.relative_to(docs).parts]
    paths += list(docs.glob('**/*development-plan.md'))
    paths += [docs / 'v1.1.0/debt-ledger.json', docs / 'v1.1.1/preceding-gates.md']
    return sorted(p.relative_to(ROOT).as_posix() for p in set(paths))


def snapshot(paths):
    result = {}
    for path in paths:
        data = (ROOT / path).read_bytes()
        item = {'sha256': sha256(data).hexdigest(), 'bytes': len(data)}
        if not path.endswith('.json'):
            result[path] = item
            continue
        record = json.loads(data)
        keys = []
        if isinstance(record.get('work_packages'), dict):
            keys.extend(f'work_packages/{key}' for key in sorted(record['work_packages']))
        for collection in ('blocked_work_packages', 'predecessor_blockers', 'completion_matrix', 'gates', 'debts', 'accepted_limitations'):
            value = record.get(collection)
            if isinstance(value, dict):
                keys.extend(f'{collection}/{key}' for key in sorted(value))
            if isinstance(value, list):
                keys.extend(f'{collection}/{i}' for i in range(len(value)))
        item['obligations'] = [
            {'id': f'{path}#{key}', 'source_pointer': '/' + key,
             'work_packages': V111_MAP[int(key.split('/W')[-1])].split()
             if path == 'docs/v1.1.1/release-gates.json' and key.startswith('work_packages/W') else ['W0', 'W8'],
             'disposition': 'PRESERVE_NO_WAIVER'}
            for key in keys
        ]
        result[path] = item
    return result


def validate(ledger):
    if ledger.get('schema_version') != 1 or ledger.get('baseline_commit') != BASE:
        raise ValueError('wrong predecessor baseline')
    sources = ledger.get('historical_sources')
    current = snapshot(source_paths())
    source_set = json.dumps({path: item['sha256'] for path, item in current.items()},
                            sort_keys=True, separators=(',', ':')).encode()
    if sha256(source_set).hexdigest() != BASELINE_SOURCE_SET_SHA256:
        raise ValueError('historical sources do not match pinned baseline')
    if sources != current or ledger.get('retained_minimum') != MINIMUM:
        raise ValueError('historical bytes, obligation mapping or thresholds changed')
    if ledger.get('state') != {'implementation': 'PARTIAL', 'verification': 'OFFLINE_RULES_ONLY', 'release': 'BLOCKED'}:
        raise ValueError('candidate state must remain bounded')
    # In this first slice, no new evidence can close a historic obligation. A future
    # acceptance verifier needs independently supplied run and reviewer evidence.
    if ledger.get('release_ready') is not False or ledger.get('release_authorized') is not False or ledger.get('closure_receipts') != []:
        raise ValueError('unsupported release or closure claim')
    return {'status': 'PRESERVED_NOT_CLOSED', 'files': len(sources),
            'mapped_obligations': sum(len(item.get('obligations', [])) for item in sources.values()),
            'release_ready': False, 'release_authorized': False}


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--ledger', type=Path, default=LEDGER)
    args = parser.parse_args()
    try:
        result = validate(json.loads(args.ledger.read_text(encoding='utf-8')))
    except (ValueError, OSError) as exc:
        parser.exit(1, f'{exc}\n')
    print(json.dumps(result, indent=2))
