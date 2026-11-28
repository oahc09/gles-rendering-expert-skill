#!/usr/bin/env python3
"""Run the v1.1.3 local gates and report which obligations still need evidence."""

import argparse
from contextlib import closing
from datetime import datetime, timezone
from hashlib import sha256
from importlib.metadata import version
import json
import os
from pathlib import Path
import platform
import re
import subprocess
import sys
import uuid

from check_v112_baseline import LEDGER as HISTORICAL_LEDGER, ROOT, validate as validate_history
from package_skill import CANDIDATE_VERSION


STATUS = ROOT / 'docs/v1.1.3/obligations.json'
HOST_CHECKS = {
    'radar': (['-m', 'unittest', 'discover', '-s', 'references/research', '-p', 'test_radar_history.py'],
              ('R2-02', 'R2-03')),
    'decision': (['-m', 'unittest', 'discover', '-s', 'tools', '-p', 'test_gpu_decision_v111.py'],
                 ('R2-04',)),
}
SHADOW_RUNNER = 'benchmarks/product_smoke/shadow_core30.py'
HOST_INPUTS = (
    'benchmarks/product_smoke/audit_formats_culling.py',
    'benchmarks/product_smoke/odd_video.py',
    SHADOW_RUNNER,
    'references/coverage/gles-api-catalog.json.gz',
    'references/decision/v111-request.schema.json',
    'references/decision/v111-strategies.json',
    'references/experience/v111-cases.json',
    'references/research/test_radar_history.py',
    'references/research/update_radar.py',
    'references/rules/shadow-mapping-mobile.md',
    'tools/attachment_lifecycle.py',
    'tools/check_v112_baseline.py',
    'tools/check_v113_acceptance.py',
    'tools/gpu_decision_v111.py',
    'tools/test_gpu_decision_v111.py',
)


def git(*args):
    return subprocess.check_output(['git', *args], cwd=ROOT, text=True, encoding='utf-8').strip()


def timestamp():
    return datetime.now(timezone.utc).isoformat(timespec='seconds')


def entry(path, relative_to):
    data = path.read_bytes()
    return {'path': path.relative_to(relative_to).as_posix(), 'size': len(data),
            'sha256': sha256(data).hexdigest()}


def load_ledger():
    ledger = json.loads(STATUS.read_text(encoding='utf-8'))
    plan = ROOT / ledger['plan']['path']
    if ledger['schema_version'] != 1 or ROOT / ledger['historical_ledger'] != HISTORICAL_LEDGER:
        raise ValueError('wrong obligation ledger version or historical reference')
    if entry(plan, ROOT) != ledger['plan']:
        raise ValueError('plan differs from the ledger source')
    document = plan.read_text(encoding='utf-8')
    anchors = set(re.findall(r'^\| ((?:V113-W|R2-|B|G)[0-9]{2})(?=[ /])', document, re.M))
    rows = ledger['obligations']
    ids = {row['id'] for row in rows}
    inherited = {f'V112-W{number}' for number in range(17)}
    if ids != anchors | inherited or len(ids) != len(rows):
        raise ValueError('missing, duplicate or unexpected obligation')
    for row in rows:
        if not row['work_packages'] or row['source_anchor'] not in document or any(
            package not in anchors or not package.startswith('V113-W') for package in row['work_packages']
        ):
            raise ValueError(f'invalid mapping for {row["id"]}')
    return ledger


def execute(name, args, output, *, environment=None):
    log = output / f'{name}.log'
    started_at = timestamp()
    try:
        with log.open('xb') as stream:
            result = subprocess.run([sys.executable, *args], cwd=ROOT, env=environment,
                                    stdout=stream, stderr=subprocess.STDOUT, timeout=120)
        code = result.returncode
    except subprocess.TimeoutExpired:
        code = None
    return {'name': name, 'started_at': started_at, 'finished_at': timestamp(), 'exit_code': code,
            'log': entry(log, output)}


def local_acceptance(output, include_software):
    environment = {'host_os': platform.platform(), 'abi': platform.machine(), 'python': platform.python_version(),
                   'jsonschema': version('jsonschema')}
    input_paths = (*HOST_INPUTS, STATUS.relative_to(ROOT), HISTORICAL_LEDGER.relative_to(ROOT))
    inputs = [entry(ROOT / path, ROOT) for path in input_paths]
    runs = []
    observations = {}
    for name, (args, ids) in HOST_CHECKS.items():
        result = execute(name, args, output)
        runs.append(result)
        observations.update(dict.fromkeys(ids, 'PASS' if result['exit_code'] == 0 else 'FAIL'))
    if include_software:
        software = []
        for api in ('3.0', '3.2'):
            name = f'shadow-{api}'
            report = output / f'{name}.json'
            env = dict(os.environ, EGL_PLATFORM='surfaceless', LIBGL_ALWAYS_SOFTWARE='1',
                       GALLIUM_DRIVER='llvmpipe', MESA_SHADER_CACHE_DISABLE='true',
                       MESA_GLES_VERSION_OVERRIDE=api)
            run = execute(name, [SHADOW_RUNNER, '--headers', '/usr/include', '--api', api, '--out', str(report)],
                          output, environment=env)
            if run['exit_code'] == 0:
                run['report'] = entry(report, output)
            software.append(run)
        runs.extend(software)
        observations['R2-01'] = 'PASS' if all(row['exit_code'] == 0 for row in software) else 'FAIL'
    if inputs != [entry(ROOT / path, ROOT) for path in input_paths]:
        raise ValueError('validation inputs changed during the run')
    return {'critical_inputs_manifest': inputs, 'environment_manifest': environment, 'runs': runs}, observations


def strategy_acceptance(root, store):
    from experience_cases import open_store, query, read_receipt, validate_history, verify_receipt
    from optimization_experiments import STRATEGY_EXPERIMENTS

    validated = []
    for strategy in STRATEGY_EXPERIMENTS:
        filename = strategy + '.json'
        report, digest = read_receipt(root, filename)
        if report['strategy'] != strategy or verify_receipt(report) != 'supports':
            raise ValueError(f'missing passing software receipt: {strategy}')
        validated.append({'strategy': strategy, 'path': filename, 'sha256': digest,
                          'backend': report['environment']['implementation']})
    summary = {'software_strategy_receipts': validated, 'physical_timing': 'NOT_MEASURED'}
    observations = {'V113-W04': 'PASS_SOFTWARE_SCOPE'}
    if store is not None:
        if not store.is_file():
            raise ValueError('experience store is missing')
        with closing(open_store(store)) as db:
            validate_history(db)
            rows = query(db, root)
        active = [row for row in rows if row['effective_state'] in {'CANDIDATE', 'REPRODUCED_SOFTWARE'}]
        imported = {(row['strategy'], row['receipt_sha256']) for row in active}
        passing = all((row['strategy'], row['sha256']) in imported for row in validated)
        if not passing or any(row['effective_state'] == 'STALE' for row in rows):
            raise ValueError('experience store has stale or missing strategy receipts')
        reviewed = [row for row in active if row['state'] == 'REPRODUCED_SOFTWARE']
        reviewed_cases = {row['case_id'] for row in reviewed}
        reviewed_counterexamples = {row['case_id'] for row in reviewed if row['effect'] == 'counterexample'}
        summary['experience'] = {
            'observed_unique_cases': len({row['case_id'] for row in rows}),
            'active_unique_cases': len({row['case_id'] for row in active}),
            'active_reviewed_software_cases': len(reviewed_cases),
            'active_counterexamples': len({row['case_id'] for row in active if row['effect'] == 'counterexample'}),
            'reviewed_counts_meet_50_10': len(reviewed_cases) >= 50 and len(reviewed_counterexamples) >= 10,
        }
        observations['V113-W05'] = 'PASS_SOFTWARE_INTAKE'
    return summary, observations


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, help='create a new evidence directory outside the repository')
    parser.add_argument('--software-gles', action='store_true', help='also run the Mesa GLES 3.0/3.2 shadow gates')
    parser.add_argument('--strategy-receipts', type=Path, help='directory with the six fixed strategy receipt filenames')
    parser.add_argument('--experience-store', type=Path, help='validate software experience intake from this store')
    args = parser.parse_args(argv)
    if args.software_gles and args.output is None:
        parser.error('--software-gles requires --output')
    if args.experience_store and not args.strategy_receipts:
        parser.error('--experience-store requires --strategy-receipts')
    try:
        history = validate_history(json.loads(HISTORICAL_LEDGER.read_text(encoding='utf-8')))
        ledger = load_ledger()
        commit, tree = git('rev-parse', 'HEAD', 'HEAD^{tree}').splitlines()
        dirty = bool(git('status', '--porcelain=v1', '--untracked-files=normal'))
        report = {'validator_version': 1, 'candidate': CANDIDATE_VERSION, 'source_commit': commit, 'source_tree': tree,
                  'source_tree_scope': 'HEAD_ONLY' if dirty else 'CLEAN_CHECKOUT',
                  'execution_id': str(uuid.uuid4()), 'started_at': timestamp(),
                  'historical': history, 'independent_review_ref': None}
        observations = {}
        if args.output:
            output = args.output.resolve()
            if output.is_relative_to(ROOT):
                raise ValueError('evidence directory must be outside the repository')
            output.mkdir()
            details, observations = local_acceptance(output, args.software_gles)
            if [commit, tree] != git('rev-parse', 'HEAD', 'HEAD^{tree}').splitlines() or ledger != load_ledger():
                raise ValueError('checkout or obligation ledger changed during validation')
            report.update(details)
        if args.strategy_receipts:
            details, levels = strategy_acceptance(args.strategy_receipts, args.experience_store)
            report.update(details)
            observations.update(levels)
        report['obligations'] = [{
            'id': row['id'], 'local_validation': observations.get(row['id'], 'NOT_RUN'),
            'closure': 'OPEN', 'required_evidence': row['required_evidence'],
        } for row in ledger['obligations']]
        report['unclosed_historical_obligations'] = history['mapped_obligations']
        report['technical_ready'] = (report['unclosed_historical_obligations'] == 0
                                     and all(row['closure'] == 'CLOSED' for row in report['obligations']))
        report['release_authorized'] = False
        report['finished_at'] = timestamp()
        if args.output:
            (output / 'acceptance.json').write_text(json.dumps(report, indent=2) + '\n', encoding='utf-8')
        print(json.dumps({'local_validation': observations, **{
            key: report[key] for key in ('candidate', 'source_commit', 'source_tree_scope', 'technical_ready', 'release_authorized')
        }}, indent=2))
        return 1 if 'FAIL' in observations.values() else 0
    except (OSError, ValueError, subprocess.SubprocessError) as exc:
        parser.exit(2, f'{exc}\n')


if __name__ == '__main__':
    sys.exit(main())
