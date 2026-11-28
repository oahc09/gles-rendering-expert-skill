#!/usr/bin/env python3
"""Run one registered finite GLES experiment, preserving raw observations and fallback."""

import argparse
from copy import deepcopy
from datetime import date, datetime, timezone
import hashlib
import importlib.util
import json
from pathlib import Path
import platform
import re
import subprocess
import sys
import tempfile
from time import perf_counter_ns

from strategy_render import COLORS, Unsupported, may_reuse, render_ring, resolve_once, resolve_scope

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'tools'))
from gpu_decision_v111 import decide, read
from optimization_advisor import advise
from optimization_experiments import EXPECTED_OUTCOMES, STRATEGY_EXPERIMENTS, outcome_exit_code, resolve

STRATEGIES = ROOT / 'references/decision/v111-strategies.json'
DISCARD = 'discard-dead-attachment'
RING = 'fence-ring-reuse'
MIP = 'texture-mip-selection'
RESOLVE = 'resolve-msaa-once'
COMPUTE = 'compute-to-fragment'
FETCH = 'coherent-framebuffer-fetch'
DIGESTED = (
    'benchmarks/workflow/strategies.py', 'benchmarks/workflow/strategy_render.py',
    'benchmarks/differential/run.py', 'benchmarks/attachment_controls/run.py',
    'benchmarks/attachment_controls/discard.py', 'benchmarks/texture_access/mechanisms.py',
    'benchmarks/shader_ab/run.py', 'benchmarks/shader_ab/advanced.py',
    'benchmarks/coverage/framebuffer-fetch/run.py', 'tools/coverage/framebuffer_fetch.py',
    'tools/gpu_decision_v111.py', 'tools/optimization_advisor.py', 'tools/optimization_experiments.py',
    'tools/attachment_lifecycle.py', 'references/decision/v111-strategies.json',
    'benchmarks/workflow/run.py', 'tools/workload_fingerprint.py',
    'references/coverage/gles-api-catalog.json.gz', 'references/experience/v111-cases.json',
)
SCHEDULE = ('baseline', 'baseline', 'baseline', 'candidate', 'candidate', 'baseline', 'baseline', 'negative')
OBJECTIVES = {DISCARD: 'bandwidth', RING: 'frame_time', MIP: 'quality',
              RESOLVE: 'frame_time', COMPUTE: 'frame_time', FETCH: 'bandwidth'}
GLYPH = [channel for y in range(4) for x in range(4)
         for channel in ([255, 255, 255, 255] if x in (y, 3 - y) else [0, 0, 0, 255])]


def load_module(relative):
    spec = importlib.util.spec_from_file_location('strategy_' + Path(relative).stem, ROOT / relative)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def identity(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(',', ':'),
                                     allow_nan=False).encode()).hexdigest()


def observed_environment(metadata):
    environment = {key: metadata[key] for key in (
        'renderer', 'vendor', 'api', 'implementation', 'egl_vendor', 'os', 'os_build', 'libraries')}
    environment['extensions'] = sorted(metadata['extensions'])
    environment['abi'] = platform.machine()
    return environment


def strategy_policy(strategy):
    return next(row for row in read(STRATEGIES) if row['id'] == strategy)


def entrypoints(policy):
    return policy['core_entrypoints'] + policy.get('extension_entrypoints', [])


def decision_blocker(strategy, request):
    row = next((row for row in decide(request)['candidates'] if row['strategy'] == strategy), None)
    if row is None:
        return 'no relevant candidate'
    if row['status'] != 'EXPERIMENT_REQUIRED':
        return ', '.join(row['blocked_reasons']) or row['status']
    return None


def golden(strategy, case):
    rgba = {
        DISCARD: [204, 51, 102, 128], RESOLVE: [0, 255, 0, 255],
        COMPUTE: [64, 128, 191, 255], FETCH: [128, 191, 64, 255],
    }
    if strategy in rgba:
        return rgba[strategy] * 16
    if strategy == RING:
        return [round(255 * channel) for _ in range(4) for color in COLORS for channel in color]
    texture = load_module('benchmarks/texture_access/mechanisms.py')
    near = next(row['golden'] for row in texture.cases() if row['id'] == 'direct-upload-baseline')
    return near + ([128, 128, 128, 255] * 16 if case == 'equivalent' else GLYPH)


def pixels_pass(pixels, expected):
    return (type(pixels) is list and len(pixels) == len(expected) and
            all(type(value) is int and 0 <= value <= 255 and abs(value - reference) <= 1
                for value, reference in zip(pixels, expected)))


def texture_draw(host, module, case, variant):
    cases = {row['id']: row for row in module.cases()}
    near = host.execute(cases['direct-upload-baseline'])
    if variant == 'negative':
        # A legal incomplete sampler yields opaque black. The image oracle
        # rejects this path without treating GL_NO_ERROR as completeness.
        request = dict(cases['generated-mipmap'], mode='incomplete-mip')
    elif variant == 'candidate':
        request = cases['generated-mipmap']
    elif case == 'glyph':
        request = cases['direct-upload-baseline']
    else:
        request = cases['linear-filter']
    if case == 'glyph':
        request = dict(request, image=(4, 4, GLYPH))
    far = host.execute(request)
    if near['gl_error'] or far['gl_error']:
        raise RuntimeError('texture control issued an invalid GL operation')
    return {'pixels': near['pixels'] + far['pixels'], 'observations': [near, far]}


def native_session(config, strategy, case, as_of):
    if strategy == COMPUTE:
        module = load_module('benchmarks/shader_ab/advanced.py')
        host = module.AdvancedHost(config)
    elif strategy == MIP:
        module = load_module('benchmarks/texture_access/mechanisms.py')
        host = module.TextureHost(config)
    elif strategy == DISCARD:
        module = load_module('benchmarks/attachment_controls/discard.py')
        host = module.attachments.Host(config)
    else:
        module = load_module('benchmarks/differential/run.py')
        host = module.Host(config)
    try:
        environment = observed_environment(host.metadata)
        environment['callable_entrypoints'] = sorted(
            name for name in entrypoints(strategy_policy(strategy))
            if callable(getattr(host.gl, name, None)))
        request = decision_request(strategy, environment, case, as_of)
        if blocker := decision_blocker(strategy, request):
            return environment, [], {}, blocker
        controls = {}
        if strategy == COMPUTE:
            controls['consumer_barrier_guard'] = host.draw('compute', barrier=False)
            if not host.supports_compute:
                raise Unsupported('GLES 3.1 required')
            if controls['consumer_barrier_guard']['status'] != 'REJECTED_UNSAFE':
                raise RuntimeError('missing barrier control was not rejected')
        elif strategy == RING:
            controls = {'timeout_rejected': not may_reuse(0x911B, 1, 1),
                        'stale_generation_rejected': not may_reuse(0x911A, 1, 2)}
        elif strategy == RESOLVE:
            controls = {'intermediate_consumer_rejected': not resolve_scope(4, intermediate_consumer=True),
                        'incompatible_format_rejected': not resolve_scope(4, same_format=False),
                        'stale_generation_rejected': not resolve_scope(4, generation_matches=False)}
        elif strategy == MIP:
            controls = {'logical_peak_asset_bytes': {'baseline': 64 if case == 'glyph' else 16,
                                                     'candidate': 84 if case == 'glyph' else 20},
                        'incomplete_chain_uses_image_oracle': True}
        elif strategy == DISCARD:
            negative = deepcopy(request)
            negative['workload']['discard_scope']['lifecycle'].append({'op': 'consume', 'attachment': 'depth'})
            controls['later_consumer_rejected'] = (
                decision_blocker(strategy, negative) == 'ATTACHMENT_HAS_LATER_CONSUMER')
        if any(value is False for value in controls.values() if type(value) is bool):
            raise RuntimeError('registered preflight guard failed')

        def draw(variant):
            if strategy == DISCARD:
                return {'pixels': module.render(host, variant == 'candidate', 0 if variant == 'negative' else 1)}
            if strategy == RING:
                return render_ring(host, variant)
            if strategy == RESOLVE:
                return resolve_once(host, variant)
            if strategy == MIP:
                return texture_draw(host, module, case, variant)
            result = host.draw('uniform_constant' if variant == 'baseline' else 'compute',
                               wrong=variant == 'negative')
            if result.get('status') != 'EXECUTED' or result['harness_gl_error']:
                raise RuntimeError('compute render did not complete')
            return result

        rows = []
        for index, variant in enumerate(('baseline',) + SCHEDULE):
            start = perf_counter_ns()
            observation = draw(variant)
            wall = perf_counter_ns() - start
            rows.append({**observation, 'variant': variant, 'warmup': index == 0,
                         'host_wall_ns_including_setup_and_readback': wall})
        return environment, rows, controls, None
    except Unsupported as error:
        return environment, [], controls, str(error)
    finally:
        host.close()


def fetch_session(config_path, as_of):
    source = ROOT / 'benchmarks/coverage/framebuffer-fetch/run.py'
    rows, controls = [], {}
    env = None
    blocker = None
    # The existing diagnostic corpus documents a driver-process crash. Keep
    # each mode isolated so a failed candidate cannot destroy fallback evidence.
    with tempfile.TemporaryDirectory(prefix='gles-fetch-') as directory:
        for index, variant in enumerate(('baseline',) + SCHEDULE[:-1]):
            mode = 'coherent' if variant == 'candidate' else 'fallback'
            if mode == 'coherent' and blocker is None:
                blocker = decision_blocker(FETCH, decision_request(FETCH, env, 'equivalent', as_of))
            if blocker and mode == 'coherent':
                continue
            output = Path(directory) / f'{index}.json'
            try:
                start = perf_counter_ns()
                result = subprocess.run([sys.executable, str(source), '--config', str(config_path),
                                         '--output', str(output), '--mode', mode], timeout=30,
                                        capture_output=True, text=True, cwd=ROOT)
                wall = perf_counter_ns() - start
            except subprocess.TimeoutExpired:
                if mode == 'fallback':
                    raise
                blocker = 'coherent fetch child timed out'
                continue
            if not output.is_file():
                if mode == 'fallback':
                    raise RuntimeError(f'ping-pong child failed: {result.returncode}: {result.stderr}')
                blocker = f'coherent fetch child exited {result.returncode} without receipt'
                continue
            report = json.loads(output.read_text(encoding='utf-8'))
            current = observed_environment(report['environment'])
            current['callable_entrypoints'] = []
            if env is not None and current != env:
                raise RuntimeError('fetch environment changed during the experiment')
            env = current
            row = next(row for row in report['rows'] if row['mode'] == mode)
            if row['status'] == 'NOT_SUPPORTED':
                blocker = 'GL_EXT_shader_framebuffer_fetch unavailable'
                continue
            if result.returncode or row['status'] != 'PASS':
                if mode == 'fallback':
                    raise RuntimeError('ping-pong oracle failed')
                if 'pixels' not in row or row.get('gl_error'):
                    blocker = 'coherent fetch compile, link or driver failure'
                    controls['failed_candidate'] = row
                    continue
            rows.append({'variant': variant, 'warmup': index == 0,
                         'host_wall_ns_including_process_startup': wall, **row})
    controls['requires_exact_extension'] = 'GL_EXT_shader_framebuffer_fetch'
    controls['noncoherent_is_distinct'] = True
    return env, rows, controls, blocker


def decision_request(strategy, environment, case, as_of):
    policy = strategy_policy(strategy)
    version = re.match(r'OpenGL ES (\d+\.\d+)', environment['api'])
    if version is None:
        raise ValueError('unknown GLES version: ' + environment['api'])
    extensions = set(policy.get('extensions', []))
    request = {'schema_version': 1, 'as_of': as_of,
               'objective': {OBJECTIVES[strategy]: 1},
               'target': {'gles': version[1], 'extensions': sorted(extensions.intersection(environment['extensions'])),
                          'entrypoints': sorted(set(entrypoints(policy)).intersection(environment['callable_entrypoints'])),
                          'probes': {strategy: True},
                          'profile': 'v113-' + identity([environment, strategy, case])},
               'workload': {'labels': [policy['labels'][0]]}}
    if strategy == DISCARD:
        request['workload']['discard_scope'] = load_module('benchmarks/attachment_controls/discard.py').SCOPE
    return request


def run(config_path, strategy, case, output):
    if case != 'equivalent' and (case != 'glyph' or strategy != MIP):
        raise ValueError('unregistered strategy case')
    experiment = STRATEGY_EXPERIMENTS[strategy]
    config_path = config_path.resolve()
    config = read(config_path)
    if config['kind'] not in ('mesa', 'angle'):
        raise ValueError('software backend required')
    inputs = {path: hashlib.sha256((ROOT / path).read_bytes()).hexdigest() for path in DIGESTED}
    start = datetime.now(timezone.utc)
    as_of = date.today().isoformat()
    environment, rows, controls, blocker = (fetch_session(config_path, as_of) if strategy == FETCH
                                            else native_session(config, strategy, case, as_of))
    request = decision_request(strategy, environment, case, as_of)
    initial = decide(request)
    if strategy == FETCH:
        negative = deepcopy(request)
        negative['target']['extensions'] = ['GL_EXT_shader_framebuffer_fetch_non_coherent']
        controls['noncoherent_does_not_enable_coherent'] = (
            decide(negative)['status'] == 'NO_EXPERIMENT_RECOMMENDED')
    expected = golden(strategy, case)
    for row in rows:
        row['quality_pass'] = pixels_pass(row['pixels'], expected)
    base = [row for row in rows if row['variant'] == 'baseline']
    candidate = [row for row in rows if row['variant'] == 'candidate']
    negative = [row for row in rows if row['variant'] == 'negative']
    controls_ok = (bool(base) and all(row['quality_pass'] for row in base) and
                   all(not row['quality_pass'] for row in negative) and
                   all(value for value in controls.values() if type(value) is bool))
    if blocker:
        status = 'BLOCKED'
    elif not controls_ok or len(candidate) != 2 or initial['status'] != 'EXPERIMENT_REQUIRED':
        status = 'FAIL'
    elif not all(row['quality_pass'] for row in candidate):
        status = 'QUALITY_FAIL'
    else:
        status = 'HOST_PASS'
    workload = f'{experiment}-{case}'
    candidate_input = {
        'id': strategy, 'experiment': experiment, 'fallback': 'baseline',
        'capability_supported': blocker is None and initial['status'] == 'EXPERIMENT_REQUIRED',
        'measurement': {'provenance': 'software'}, 'quality': {
            'pass': None if blocker else status == 'HOST_PASS', 'golden_id': f'{workload}-rgba8',
            'thresholds': {'max_8bit_error': 1},
        },
    }
    advisor_input = {
        'decision_request': request,
        'workload': {'workload_id': workload, 'provenance': 'synthetic', 'resolution': [4, 4]},
        'candidates': [candidate_input],
    }
    advisor = advise(advisor_input)
    aa = [row for row in base if not row['warmup']][:2]
    timing_key = 'host_wall_ns_including_setup_and_readback'
    noise = abs(aa[0][timing_key] - aa[1][timing_key]) if len(aa) == 2 and timing_key in aa[0] else None
    if any(hashlib.sha256((ROOT / path).read_bytes()).hexdigest() != sha for path, sha in inputs.items()):
        raise RuntimeError('experiment inputs changed during execution')
    receipt = {'schema': 'gles.strategy-receipt/v1', 'strategy': strategy, 'case': case,
               'status': status, 'blocker': blocker, 'experiment': resolve(experiment),
               'workload': workload, 'inputs': inputs,
               'environment': environment, 'environment_sha256': identity(environment),
               'started_at': start.isoformat(), 'finished_at': datetime.now(timezone.utc).isoformat(),
               'expected_rgba8': expected, 'order': list(SCHEDULE[:-1] if strategy == FETCH else SCHEDULE),
               'observations': rows, 'guards': controls, 'advisor_input': advisor_input,
               'decision': initial, 'advisor': advisor, 'production_selection': 'baseline',
               'aa_host_wall_delta_ns': noise, 'gpu_time_ns': None, 'physical_performance': 'NOT_MEASURED'}
    with output.open('x', encoding='utf-8') as stream:
        json.dump(receipt, stream, indent=2, allow_nan=False)
        stream.write('\n')
    return receipt


def run_composition(config_path, output):
    modules = load_module('benchmarks/differential/run.py')
    host = modules.Host(read(config_path))
    variants = {
        'baseline': ('baseline', False),
        'discard': ('baseline', True),
        'single-resolve': ('candidate', False),
        'discard-and-single-resolve': ('candidate', True),
    }
    try:
        rows = {name: resolve_once(host, variant, use_depth=True, discard_depth=discard)
                for name, (variant, discard) in variants.items()}
        status = 'HOST_PASS' if all(pixels_pass(row['pixels'], golden(RESOLVE, 'equivalent'))
                                    for row in rows.values()) else 'FAIL'
        report = {'schema': 'gles.strategy-composition/v1', 'status': status, 'rows': rows,
                  'environment': observed_environment(host.metadata), 'gpu_time_ns': None}
    except Unsupported as error:
        report = {'schema': 'gles.strategy-composition/v1', 'status': 'BLOCKED', 'blocker': str(error)}
    finally:
        host.close()
    with output.open('x', encoding='utf-8') as stream:
        json.dump(report, stream, indent=2)
        stream.write('\n')
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--config', type=Path, required=True)
    selection = parser.add_mutually_exclusive_group(required=True)
    selection.add_argument('--strategy', choices=STRATEGY_EXPERIMENTS)
    selection.add_argument('--composition', action='store_true')
    parser.add_argument('--case', choices=['equivalent', 'glyph'], default='equivalent')
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--expect', choices=EXPECTED_OUTCOMES)
    args = parser.parse_args()
    try:
        if args.composition:
            report = run_composition(args.config, args.output)
            print(report['status'])
            return outcome_exit_code(report['status'], args.expect)
        receipt = run(args.config, args.strategy, args.case, args.output)
    except (ValueError, KeyError, TypeError, OSError, RuntimeError, subprocess.SubprocessError) as error:
        parser.exit(2, str(error) + '\n')
    print(json.dumps({key: receipt[key] for key in ('strategy', 'case', 'status', 'blocker')}))
    return outcome_exit_code(receipt['status'], args.expect)


if __name__ == '__main__':
    sys.exit(main())
