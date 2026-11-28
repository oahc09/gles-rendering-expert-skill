#!/usr/bin/env python3
"""Govern software strategy experience and replay its effect on Decision and Advisor."""

import argparse
from copy import deepcopy
from datetime import datetime, timezone
from hashlib import sha256
import json
from pathlib import Path
import re
import sqlite3
import sys

from gpu_decision_v111 import CASES, decide, read, require, token
from optimization_advisor import advise
from optimization_experiments import STRATEGY_EXPERIMENTS, resolve

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'benchmarks/workflow'))
from strategies import DIGESTED, FETCH, MIP, SCHEDULE, decision_request, golden, identity, pixels_pass

MAX_RECEIPT_BYTES = 4 * 1024 * 1024
SHA256 = re.compile(r'[0-9a-f]{64}')
TERMINAL = {'REJECTED', 'RETRACTED'}


def open_store(path):
    db = sqlite3.connect(path)
    db.row_factory = sqlite3.Row
    db.execute('''CREATE TABLE IF NOT EXISTS experience (
        case_id TEXT NOT NULL, scope TEXT NOT NULL, revision INTEGER NOT NULL,
        state TEXT NOT NULL, entry TEXT NOT NULL,
        PRIMARY KEY(case_id, scope, revision)
    )''')
    return db


def read_receipt(root, relative, expected_sha256=None):
    root = root.resolve(strict=True)
    relative = Path(relative)
    require(not relative.is_absolute() and '..' not in relative.parts and relative.parts,
            'receipt file must be relative to evidence root')
    path = root / relative
    require(path.resolve(strict=True) == path and path.is_file(), 'receipt must be a regular local file')
    with path.open('rb') as stream:
        raw = stream.read(MAX_RECEIPT_BYTES + 1)
    require(len(raw) <= MAX_RECEIPT_BYTES, 'receipt exceeds size bound')
    digest = sha256(raw).hexdigest()
    require(expected_sha256 is None or expected_sha256 == digest, 'receipt SHA-256 mismatch')
    return json.loads(raw), digest


def verify_receipt(report):
    require(report.get('schema') == 'gles.strategy-receipt/v1', 'unknown receipt schema')
    strategy, case = report['strategy'], report['case']
    require(strategy in STRATEGY_EXPERIMENTS and (case == 'equivalent' or (strategy == MIP and case == 'glyph')),
            'unregistered case')
    experiment = STRATEGY_EXPERIMENTS[strategy]
    require(report['experiment'] == resolve(experiment) and report['workload'] == f'{experiment}-{case}',
            'workload or runner binding changed')
    require(set(report['inputs']) == set(DIGESTED), 'incomplete experiment inputs')
    for path, digest in report['inputs'].items():
        require(sha256((ROOT / path).read_bytes()).hexdigest() == digest, 'source changed: ' + path)
    environment = report['environment']
    require(environment['implementation'] in {'mesa', 'angle'} and report['gpu_time_ns'] is None
            and report['physical_performance'] == 'NOT_MEASURED' and report['production_selection'] == 'baseline'
            and report['environment_sha256'] == identity(environment), 'unsupported evidence provenance')
    start = datetime.fromisoformat(report['started_at'])
    finish = datetime.fromisoformat(report['finished_at'])
    require(start.tzinfo is not None and finish.tzinfo is not None and start <= finish,
            'invalid execution timestamps')
    advisor_input = report['advisor_input']
    recorded = advisor_input['decision_request']
    request = decision_request(strategy, environment, case, recorded['as_of'])
    require(request == recorded and report['decision'] == decide(request), 'decision binding mismatch')
    require(report['advisor'] == advise(advisor_input), 'advisor result mismatch')
    require(advisor_input['workload']['workload_id'] == report['workload']
            and len(advisor_input['candidates']) == 1
            and advisor_input['candidates'][0]['experiment'] == experiment,
            'advisor input does not bind registered experiment')
    return verified_quality(report, strategy, case)


def verified_quality(report, strategy, case):
    expected = golden(strategy, case)
    require(report['expected_rgba8'] == expected, 'oracle payload differs from registered case')
    rows = report['observations']
    order = SCHEDULE[:-1] if strategy == FETCH else SCHEDULE
    require(report['order'] == list(order), 'unregistered run order')
    if report['status'] == 'BLOCKED':
        return None
    require(not report['blocker'] and [row['variant'] for row in rows] == ['baseline', *order],
            'missing paired observations')
    quality = []
    for index, row in enumerate(rows):
        passed = pixels_pass(row['pixels'], expected)
        require(row['warmup'] is (index == 0) and row['quality_pass'] is passed,
                'observation quality field does not match readback')
        if row['variant'] != 'candidate':
            require(passed is (row['variant'] == 'baseline'), 'control did not behave as expected')
        else:
            quality.append(passed)
    outcome = 'HOST_PASS' if all(quality) else 'QUALITY_FAIL'
    require(report['status'] == outcome and
            report['advisor_input']['candidates'][0]['quality']['pass'] is all(quality) and
            report['advisor']['candidates'][0]['status'] ==
            ('INSUFFICIENT_EVIDENCE' if all(quality) else 'REJECTED_BY_QUALITY'),
            'reported outcome differs from observation')
    return 'supports' if outcome == 'HOST_PASS' else 'counterexample'


def latest(db, case_id=None, scope=None):
    rows = db.execute('''SELECT entry FROM experience e WHERE revision = (
        SELECT MAX(revision) FROM experience r WHERE r.case_id=e.case_id AND r.scope=e.scope
    ) AND (? IS NULL OR e.case_id=?) AND (? IS NULL OR e.scope=?) ORDER BY e.case_id, e.scope''',
                      (case_id, case_id, scope, scope))
    return [json.loads(row['entry']) for row in rows]


def add_revision(db, entry):
    db.execute('INSERT INTO experience (case_id, scope, revision, state, entry) VALUES (?, ?, ?, ?, ?)',
               (entry['case_id'], entry['scope'], entry['revision'], entry['state'],
                json.dumps(entry, sort_keys=True, allow_nan=False)))


def import_receipt(db, root, relative, author, digest=None):
    require(token(author), 'invalid importer')
    report, digest = read_receipt(root, relative, digest)
    effect = verify_receipt(report)
    if effect is None:
        return {'status': 'BLOCKED_RUN_RETAINED', 'receipt': str(relative), 'sha256': digest}
    strategy, case = report['strategy'], report['case']
    ident, scope = f'{strategy}.{case}', report['environment_sha256']
    root_cause = ('mip-prefilter-removes-glyph-detail' if strategy == MIP and case == 'glyph'
                  else f'{strategy}-fixed-compatibility-control')
    with db:
        db.execute('BEGIN IMMEDIATE')
        prior = latest(db, ident, scope)
        if prior:
            previous = prior[0]
            if previous['receipt_sha256'] == digest:
                return previous
            require(previous['state'] not in TERMINAL, 'case scope is closed; retain a new case only for a distinct root cause')
        entry = {'case_id': ident, 'scope': scope, 'revision': prior[0]['revision'] + 1 if prior else 1,
                 'state': 'CANDIDATE', 'evidence': 'SOFTWARE_OBSERVATION', 'effect': effect,
                 'strategy': strategy, 'workload': report['workload'], 'root_cause': root_cause,
                 'api': report['environment']['api'], 'backend': report['environment']['implementation'],
                 'renderer': report['environment']['renderer'], 'driver': report['environment']['api'],
                 'profile': report['advisor_input']['decision_request']['target']['profile'],
                 'receipt': Path(relative).as_posix(), 'receipt_sha256': digest, 'importer': author,
                 'recorded_at': datetime.now(timezone.utc).isoformat()}
        add_revision(db, entry)
    return entry


def matching_receipt(entry, root):
    report, _ = read_receipt(root, entry['receipt'], entry['receipt_sha256'])
    effect = verify_receipt(report)
    require(effect is not None and report['environment_sha256'] == entry['scope']
            and f'{report["strategy"]}.{report["case"]}' == entry['case_id']
            and report['workload'] == entry['workload'] and effect == entry['effect'],
            'case does not bind receipt')
    return report


def transition(db, root, case_id, scope, *, state, actor, reason):
    require(token(actor) and isinstance(reason, str) and 0 < len(reason.strip()) <= 1000, 'actor and reason required')
    require(state in {'REPRODUCED_SOFTWARE', 'REJECTED', 'RETRACTED'}, 'invalid transition')
    with db:
        db.execute('BEGIN IMMEDIATE')
        rows = latest(db, case_id, scope)
        require(len(rows) == 1, 'unknown case scope')
        previous = rows[0]
        if state == 'RETRACTED':
            require(previous['state'] in {'CANDIDATE', 'REPRODUCED_SOFTWARE'}, 'invalid retract transition')
        else:
            require(previous['state'] == 'CANDIDATE' and actor != previous['importer'],
                    'review requires a candidate and a separate identified reviewer')
            matching_receipt(previous, root)
        entry = dict(previous, revision=previous['revision'] + 1, state=state,
                     actor=actor, reason=reason, recorded_at=datetime.now(timezone.utc).isoformat())
        add_revision(db, entry)
    return entry


def validate_history(db):
    previous = {}
    for row in db.execute('SELECT * FROM experience ORDER BY case_id, scope, revision'):
        entry = json.loads(row['entry'])
        key = row['case_id'], row['scope']
        identity_matches = all(entry[field] == row[field] for field in ('case_id', 'scope', 'revision', 'state'))
        require(identity_matches and SHA256.fullmatch(row['scope']) and token(entry['importer']) and
                entry['evidence'] == 'SOFTWARE_OBSERVATION', 'inconsistent revision identity')
        prior = previous.get(key)
        state = row['state']
        if prior is None:
            require(row['revision'] == 1 and state == 'CANDIDATE', 'invalid initial revision')
        else:
            require(prior['revision'] + 1 == entry['revision'] and prior['state'] not in TERMINAL,
                    'revision gap or transition after terminal state')
            if state != 'CANDIDATE':
                require(state in {'REPRODUCED_SOFTWARE', 'REJECTED', 'RETRACTED'} and token(entry['actor'])
                        and type(entry['reason']) is str and bool(entry['reason'].strip())
                        and entry['receipt_sha256'] == prior['receipt_sha256'], 'invalid governance event')
            if state in {'REPRODUCED_SOFTWARE', 'REJECTED'}:
                require(prior['state'] == 'CANDIDATE' and entry['actor'] != prior['importer'],
                        'review must have a different actor')
        previous[key] = entry


def query(db, root, **selection):
    rows = []
    for entry in latest(db):
        if selection.get('strategy') and entry['strategy'] != selection['strategy']:
            continue
        keys = {key: value for key, value in selection.items() if key != 'strategy' and value is not None}
        scope = 'EXACT' if {'workload', 'scope'} <= keys.keys() and all(entry[k] == v for k, v in keys.items()) else 'RELATED'
        state, reason = entry['state'], None
        if state not in TERMINAL:
            try:
                matching_receipt(entry, root)
            except (OSError, KeyError, TypeError, ValueError) as error:
                state, reason = 'STALE', str(error)
        rows.append({**entry, 'effective_state': state, 'match': scope, 'invalid_reason': reason})
    return rows


def apply_to_request(db, root, request, workload, scope):
    request = deepcopy(request)
    rows = query(db, root, workload=workload, scope=scope)
    guarded = [entry for entry in rows if entry['match'] == 'EXACT'
               and entry.get('profile') == request.get('target', {}).get('profile')
               and entry['effect'] == 'counterexample'
               and entry['effective_state'] in {'CANDIDATE', 'REPRODUCED_SOFTWARE'}]
    if guarded:
        request['blocked_strategies'] = sorted(set(request.get('blocked_strategies', [])) |
                                               {entry['strategy'] for entry in guarded})
    return request, sorted({entry['case_id'] for entry in guarded}), rows


def evaluate(db, root, relative):
    report, digest = read_receipt(root, relative)
    verify_receipt(report)
    advisor_input = deepcopy(report['advisor_input'])
    request, guarded, rows = apply_to_request(db, root, advisor_input['decision_request'],
                                             report['workload'], report['environment_sha256'])
    advisor_input['decision_request'] = request
    # This replay already has a stable environment, but requires fresh quality
    # evidence for adoption. An exact known failed oracle can stop a repeated run.
    request['target']['probes'].pop(report['strategy'], None)
    for candidate in advisor_input['candidates']:
        candidate.pop('measurement', None)
        candidate['quality']['pass'] = None
    return {'source_receipt_sha256': digest, 'applied_quality_guards': guarded, 'experience': rows,
            'decision': decide(request, cases=read(CASES)), 'advisor': advise(advisor_input)}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--store', type=Path, required=True)
    parser.add_argument('--evidence-root', type=Path, required=True)
    commands = parser.add_subparsers(dest='command', required=True)
    commands.add_parser('validate')
    importer = commands.add_parser('import')
    importer.add_argument('receipt')
    importer.add_argument('--actor', required=True)
    importer.add_argument('--sha256')
    selector = commands.add_parser('query')
    for option in ('strategy', 'workload', 'api', 'backend', 'driver', 'scope'):
        selector.add_argument('--' + option)
    for name in ('review', 'retract'):
        action = commands.add_parser(name)
        action.add_argument('case_id')
        action.add_argument('--scope', required=True)
        action.add_argument('--actor', required=True)
        action.add_argument('--reason', required=True)
        if name == 'review':
            action.add_argument('--verdict', choices=['reproduce-software', 'reject'], required=True)
    commands.add_parser('evaluate').add_argument('receipt')
    args = parser.parse_args()
    try:
        db = open_store(args.store)
        if args.command == 'import':
            require(args.sha256 is None or SHA256.fullmatch(args.sha256), 'invalid SHA-256')
            result = import_receipt(db, args.evidence_root, args.receipt, args.actor, args.sha256)
        elif args.command in ('review', 'retract'):
            state = ('RETRACTED' if args.command == 'retract' else
                     'REPRODUCED_SOFTWARE' if args.verdict == 'reproduce-software' else 'REJECTED')
            result = transition(db, args.evidence_root, args.case_id, args.scope,
                                state=state, actor=args.actor, reason=args.reason)
        elif args.command == 'evaluate':
            result = evaluate(db, args.evidence_root, args.receipt)
        elif args.command == 'query':
            result = query(db, args.evidence_root, **{key: getattr(args, key) for key in
                           ('strategy', 'workload', 'api', 'backend', 'driver', 'scope')})
        else:
            validate_history(db)
            rows = query(db, args.evidence_root)
            stale = [row for row in rows if row['effective_state'] == 'STALE']
            active = [row for row in rows if row['effective_state'] in {'CANDIDATE', 'REPRODUCED_SOFTWARE'}]
            print(json.dumps({'stale': stale,
                              'unique_active_cases': len({row['case_id'] for row in active}),
                              'unique_active_counterexamples': len({row['case_id'] for row in active
                                                                   if row['effect'] == 'counterexample'}),
                              'reviewed_software_cases': len({row['case_id'] for row in active
                                                              if row['state'] == 'REPRODUCED_SOFTWARE'}),
                              'physical_device_cases': 0}, indent=2))
            return bool(stale)
    except (OSError, KeyError, TypeError, ValueError, sqlite3.Error) as error:
        parser.exit(2, f'{error}\n')
    print(json.dumps(result, indent=2))
    return 0


if __name__ == '__main__':
    sys.exit(main())
