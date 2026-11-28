#!/usr/bin/env python3
"""Apply hard limits and propose at most one bounded probe around the v1 GPU decision."""

import argparse
import hashlib
import json
from pathlib import Path
import sys

from gpu_decision_v111 import check_keys, decide, read, require, token


FACTS = ('backend', 'driver', 'timer_available', 'quality_oracle', 'evidence_conflict', 'environment_changed')
PROBES = {
    'execution-environment': ('backend or driver is unknown', 'record actual backend and driver', 'stop if identity remains unknown'),
    'resolve-evidence-conflict': ('captures disagree', 'keep only evidence matching the session', 'stop if the conflict remains'),
    'attachment-consumers': ('attachment lifetime is incomplete', 'check every later attachment consumer', 'keep the original store if any consumer exists'),
    'quality-oracle': ('quality oracle is missing', 'record the oracle and its tolerance', 'stop if no correctness criterion is available'),
    'timing-capability': ('timer availability is unknown', 'record whether the target supports a usable timer', 'leave GPU time unknown if a timer is unavailable'),
    'hard-limit-evidence': ('hard constraint lacks a measurement', 'record the requested metric in its declared unit', 'keep baseline if still unknown or over budget'),
    'strategy-correctness': ('candidate correctness probe has not run', 'check the strategy preconditions and correctness', 'block the candidate if correctness fails'),
}
UNITS = {'resource_bytes': 'bytes', 'latency_ms': 'ms', 'quality_error': 'normalized',
         'thermal_severity': 'ordinal'}


def nonnegative_integer(value):
    return type(value) is int and 0 <= value < 2 ** 53


def metric(value):
    return type(value) in (int, float) and 0 <= value < 2 ** 53


def diagnose(session, legacy):
    check_keys(session, ('schema_version', 'facts', 'budget_remaining', 'constraints', 'attempted_probes'))
    require(type(session['schema_version']) is int and session['schema_version'] == 1, 'unsupported session version')
    facts, budget = session['facts'], session['budget_remaining']
    check_keys(facts, FACTS)
    check_keys(budget, ('seconds', 'frames', 'resource_bytes'))
    require(all(nonnegative_integer(value) for value in budget.values()), 'invalid remaining budget')
    for name in ('backend', 'driver', 'quality_oracle'):
        value = facts[name]
        require(value is None or (type(value) is str and 0 < len(value) <= 512 and value != 'UNKNOWN'),
                f'invalid {name}; use null for unknown')
    for name in ('timer_available', 'evidence_conflict', 'environment_changed'):
        require(facts[name] is None or type(facts[name]) is bool, f'invalid {name}')
    attempted = session['attempted_probes']
    require(type(attempted) is list and all(token(name) and name in PROBES for name in attempted)
            and len(set(attempted)) == len(attempted), 'invalid probe history')

    constraints = session['constraints']
    check_keys(constraints, (), UNITS)
    violated, unknown = [], []
    for name, row in sorted(constraints.items()):
        check_keys(row, ('unit', 'maximum', 'observed', 'source'))
        require(row['unit'] == UNITS[name] and metric(row['maximum']) and
                (row['observed'] is None or metric(row['observed'])) and token(row['source']),
                f'invalid hard constraint {name}')
        if row['observed'] is None:
            unknown.append(name)
        elif row['observed'] > row['maximum']:
            violated.append(name)
    if facts['environment_changed'] is not False:
        return 'KEEP_BASELINE', 'ENVIRONMENT_CHANGED_OR_UNBOUND', None
    if facts['evidence_conflict'] is False and violated:
        return 'KEEP_BASELINE', 'HARD_LIMIT_EXCEEDED:' + ','.join(violated), None
    if not all(budget.values()):
        return 'KEEP_BASELINE', 'PROBE_BUDGET_EXHAUSTED', None

    candidates = [row for row in legacy['candidates'] if row['status'] in {'PROBE_REQUIRED', 'EXPERIMENT_REQUIRED'}]
    if not candidates:
        return 'KEEP_BASELINE', 'NO_ELIGIBLE_CANDIDATE', None

    candidate = candidates[0]
    preconditions = candidate['preconditions']
    probe = None
    if facts['evidence_conflict'] is not False:
        probe = 'resolve-evidence-conflict'
    elif facts['backend'] is None or facts['driver'] is None:
        probe = 'execution-environment'
    elif preconditions.get('attachment_liveness') in {'MISSING_SCOPE', 'INCOMPLETE_SCOPE'}:
        probe = 'attachment-consumers'
    elif facts['quality_oracle'] is None:
        probe = 'quality-oracle'
    elif unknown:
        probe = 'hard-limit-evidence'
    elif facts['timer_available'] is None:
        probe = 'timing-capability'
    elif preconditions['correctness_probe'] is None:
        probe = 'strategy-correctness'
    if probe is None:
        return 'EXPERIMENT_REQUIRED', 'CORRECTNESS_AND_MEASUREMENT_REQUIRED', None
    if probe in attempted:
        return 'KEEP_BASELINE', 'PROBE_UNRESOLVED:' + probe, None
    question, if_resolved, if_unresolved = PROBES[probe]
    return 'PROBE_REQUIRED', None, {
        'id': probe, 'strategy': candidate['strategy'], 'question': question,
        'if_resolved': if_resolved, 'if_unresolved': if_unresolved,
        'unknown_constraints': unknown, 'budget_ceiling': budget,
    }


def evaluate(request, session):
    legacy = decide(request)
    status, reason, probe = diagnose(session, legacy)
    identity = json.dumps([legacy['decision_id'], session], allow_nan=False, sort_keys=True, separators=(',', ':'))
    return {'schema': 'gles.decision-session/v1',
            'decision_id': hashlib.sha256(identity.encode()).hexdigest(),
            'status': status, 'stop_reason': reason, 'next_probe': probe,
            'fallback': 'baseline', 'gpu_time_available': session['facts']['timer_available'],
            'evidence_class': 'DECLARED', 'legacy_decision': legacy}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('request', type=Path, help='existing v1 decision request')
    parser.add_argument('session', type=Path, help='operator-supplied facts, limits and remaining probe budget')
    parser.add_argument('--experience-store', type=Path)
    parser.add_argument('--evidence-root', type=Path)
    parser.add_argument('--environment-sha256')
    parser.add_argument('--workload-id')
    args = parser.parse_args()
    try:
        selected = (args.experience_store, args.evidence_root, args.environment_sha256, args.workload_id)
        if any(selected) and not all(selected):
            parser.error('experience use requires store, evidence root, environment digest and workload ID')
        request = read(args.request, exact=True)
        guarded = []
        if args.experience_store:
            from contextlib import closing
            from experience_cases import SHA256, apply_to_request, open_store

            require(args.experience_store.is_file() and SHA256.fullmatch(args.environment_sha256),
                    'invalid experience store or environment digest')
            with closing(open_store(args.experience_store)) as db:
                request, guarded, _ = apply_to_request(db, args.evidence_root, request,
                                                       args.workload_id, args.environment_sha256)
        result = evaluate(request, read(args.session))
        if args.experience_store:
            result['applied_quality_guards'] = guarded
    except (OSError, ValueError, KeyError, TypeError) as error:
        parser.exit(2, f'{error}\n')
    print(json.dumps(result, indent=2))


if __name__ == '__main__':
    sys.exit(main())
