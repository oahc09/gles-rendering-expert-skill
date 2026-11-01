#!/usr/bin/env python3
"""Structured contract tests, NOT a C++ parser/compiler or GPU conformance test."""
import argparse
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

def valid(rule, x):
    predicates = {
        'R001': lambda: x['buffer'] in ('BACK', 'NONE'),
        'R002': lambda: x['buffer'] == 'NONE' or (type(x['buffer']) is int and 0 <= x['buffer'] < x['max_attachments']),
        'R003': lambda: (x['format'], x['type']) == ('RGBA', 'UNSIGNED_BYTE'),
        'R004': lambda: x['border'] == 0,
        'R005': lambda: 0 <= x['width'] <= x['limit'] and 0 <= x['height'] <= x['limit'],
        'R006': lambda: x['flags'] == 0,
        'R007': lambda: x['timeout'] == 'TIMEOUT_IGNORED',
        'R008': lambda: x['condition'] == 'GPU_COMMANDS_COMPLETE' and x['flags'] == 0,
        'R009': lambda: x['shared'] and x['producer_flush'] and x['consumer_wait'],
        'R010': lambda: x['gles'] in (30, 31, 32) and x['glsl'] in (100, 300, 310, 320) and x['glsl'] <= x['gles'] * 10,
        'R011': lambda: not x['uses_core_compute'] or x['gles'] >= 31,
        'R012': lambda: not x['uses_core_geometry'] or x['gles'] >= 32,
        'R013': lambda: x['alignment'] > 0 and x['offset'] >= 0 and x['offset'] % x['alignment'] == 0,
        'R014': lambda: x['alignment'] in (1, 2, 4, 8),
        'R015': lambda: (x['read'] or x['write']) and not (x['read'] and x['invalidate']),
        'R016': lambda: x['attachment'] in ('DEPTH_ATTACHMENT', 'STENCIL_ATTACHMENT', 'DEPTH_STENCIL_ATTACHMENT') or (x['attachment'].startswith('COLOR_ATTACHMENT') and x['attachment'][16:].isdigit() and 0 <= int(x['attachment'][16:]) < x['max_attachments']),
        'R017': lambda: x['attachment'] in ('DEPTH', 'STENCIL', 'COLOR'),
        'R018': lambda: not (x['future_read'] and x['invalidate']),
        'R019': lambda: x['filter'] in ('NEAREST', 'LINEAR') and (x['buffer_kind'] == 'normalized_color' or (x['buffer_kind'] in ('integer_color', 'depth', 'stencil') and x['filter'] == 'NEAREST')),
        'R020': lambda: not x['draw'] or x['complete'],
        'R021': lambda: not x['call'] or (x['advertised'] and x['entrypoint']),
        'R022': lambda: (x['error'], x['action']) in (('CONTEXT_LOST', 'recreate_context_resources'), ('BAD_SURFACE', 'recreate_surface')),
        'R023': lambda: x['event'] in ('APP_CMD_INPUT_CHANGED', 'APP_CMD_INIT_WINDOW', 'APP_CMD_TERM_WINDOW', 'APP_CMD_WINDOW_RESIZED', 'APP_CMD_WINDOW_REDRAW_NEEDED', 'APP_CMD_CONTENT_RECT_CHANGED', 'APP_CMD_GAINED_FOCUS', 'APP_CMD_LOST_FOCUS', 'APP_CMD_CONFIG_CHANGED', 'APP_CMD_LOW_MEMORY', 'APP_CMD_START', 'APP_CMD_RESUME', 'APP_CMD_SAVE_STATE', 'APP_CMD_PAUSE', 'APP_CMD_STOP', 'APP_CMD_DESTROY'),
        'R024': lambda: not (x['pbo_bound'] and x['mapped']),
        'R025': lambda: 0 <= x['index'] < x['max_attributes'],
        'R026': lambda: not (x['two_fetches'] and x['claims_faster']) or x['measured'],
        'R027': lambda: not x['claims_bandwidth_win'] or (x['hardware'] and x['counters']),
        'R028': lambda: not (x['essl'] >= 300 and x['external']) or x['essl3_extension'],
        'R029': lambda: not x['uses_float'] or x['declared_precision'],
        'R030': lambda: not (x['same_image_sampled_written'] and x['draw']),
    }
    return bool(predicates[rule]())

def run():
    catalog_path = ROOT / 'benchmarks/rules/catalog.json'
    cases_path = ROOT / 'benchmarks/rules/cases.json'
    catalog = json.loads(catalog_path.read_text())
    cases = json.loads(cases_path.read_text())
    rules = {r['rule_id']: r for r in catalog}
    assert len(rules) == len(catalog), 'Duplicate rules'
    assert len({c['case_id'] for c in cases}) == len(cases), 'Duplicate case IDs'
    assert len({(c['rule_id'], json.dumps(c['input'], sort_keys=True)) for c in cases}) == len(cases), 'Duplicate scenario inputs'
    assert len(cases) >= 100, 'Need at least 100 distinct contract cases'
    required = {'rule_id','gles_min_version','glsl_version','required_extensions','platform','vendor_conditions','severity','normative_source','positive_tests','negative_tests','fallback','source_file'}
    failures = []
    for r in catalog:
        assert required <= r.keys(), r['rule_id']
        assert (ROOT / r['source_file']).is_file(), r['source_file']
        for label, expected in [('positive_tests', True), ('negative_tests', False)]:
            assert r[label], (r['rule_id'], label)
            for case_id in r[label]:
                assert any(c['case_id'] == case_id and c['rule_id'] == r['rule_id'] and c['expected_valid'] is expected for c in cases), case_id
    for c in cases:
        r = rules[c['rule_id']]
        assert set(c['input']) == set(r['fields']), c['case_id']
        observed = valid(c['rule_id'], c['input'])
        if observed is not c['expected_valid']:
            failures.append({'case_id': c['case_id'], 'expected': c['expected_valid'], 'actual': observed})
    return {'suite':'structured-rule-contracts','scope':'normalized inputs only; not source analysis, compilation, runtime or model behavior','rules':len(rules),'cases':len(cases),'passed':len(cases)-len(failures),'failed':failures,'sha256':{str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest() for p in (catalog_path,cases_path,Path(__file__))}}

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--output', type=Path)
    args = parser.parse_args()
    result = run()
    text = json.dumps(result, indent=2)
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(text+'\n')
    print(text)
    raise SystemExit(bool(result['failed']))
