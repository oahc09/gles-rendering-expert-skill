"""Compare a depth store and invalidate after the last consumer in an offscreen GLES pass."""

import argparse
from copy import deepcopy
import ctypes as c
from hashlib import sha256
import importlib.util
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'tools'))
from gpu_decision_v111 import decide
from optimization_advisor import advise
from optimization_experiments import DISCARD_EXPERIMENT

spec = importlib.util.spec_from_file_location('discard_attachment_host', Path(__file__).with_name('run.py'))
attachments = importlib.util.module_from_spec(spec)
spec.loader.exec_module(attachments)
U, I, P, F = attachments.U, attachments.I, attachments.P, attachments.F

GOLDEN = [204, 51, 102, 128] * 16
SCOPE = {
    'attachment': 'depth', 'end_event': 2, 'complete': True,
    'attachments': [
        {'id': 'color', 'width': 4, 'height': 4, 'format': 'RGBA8', 'samples': 1},
        {'id': 'depth', 'width': 4, 'height': 4, 'format': 'DEPTH16', 'samples': 1},
    ],
    'lifecycle': [
        {'op': 'begin', 'fbo': 'offscreen', 'loads': {'color': 'clear', 'depth': 'clear'}},
        {'op': 'draw', 'writes': ['color', 'depth'], 'coverage': 'full_overwrite'},
        {'op': 'end', 'stores': {'color': 'store', 'depth': 'store'}},
        {'op': 'consume', 'attachment': 'color'},
    ],
}


def render(host, discard, depth_value):
    gl = host.fn
    framebuffer, color, depth, vao = U(), U(), U(), U()
    try:
        gl('glGenFramebuffers', None, [I, P])(1, c.byref(framebuffer))
        gl('glBindFramebuffer', None, [U, U])(0x8D40, framebuffer)
        color = host.texture(False)
        host.attach(color)
        gl('glGenRenderbuffers', None, [I, P])(1, c.byref(depth))
        gl('glBindRenderbuffer', None, [U, U])(0x8D41, depth)
        gl('glRenderbufferStorage', None, [U, U, I, I])(0x8D41, 0x81A5, 4, 4)
        gl('glFramebufferRenderbuffer', None, [U, U, U, U])(0x8D40, 0x8D00, 0x8D41, depth)
        if gl('glCheckFramebufferStatus', U, [U])(0x8D40) != 0x8CD5:
            raise RuntimeError('incomplete depth/color FBO')
        gl('glGenVertexArrays', None, [I, P])(1, c.byref(vao))
        gl('glBindVertexArray', None, [U])(vao)
        gl('glViewport', None, [I, I, I, I])(0, 0, 4, 4)
        gl('glDisable', None, [U])(0x0BD0)  # DITHER
        gl('glEnable', None, [U])(0x0B71)  # DEPTH_TEST
        gl('glClearDepthf', None, [F])(depth_value)
        gl('glClearColor', None, [F] * 4)(0, 0, 0, 0)
        gl('glClear', None, [U])(0x4100)
        host.draw(attachments.FLOAT)
        if discard:
            gl('glInvalidateFramebuffer', None, [U, I, P])(0x8D40, 1, (U * 1)(0x8D00))
        # The color output survives. The discarded depth is never observed.
        return host.read(False)
    finally:
        gl('glBindFramebuffer', None, [U, U])(0x8D40, 0)
        gl('glBindVertexArray', None, [U])(0)
        for obj, function in [(framebuffer, 'glDeleteFramebuffers'), (color, 'glDeleteTextures'),
                              (depth, 'glDeleteRenderbuffers'), (vao, 'glDeleteVertexArrays')]:
            if obj.value:
                gl(function, None, [I, P])(1, c.byref(obj))


def run(config, output):
    host = attachments.Host(config)
    try:
        request = {'schema_version': 1,
                   'target': {'gles': host.metadata['api'].split()[2], 'extensions': [],
                              'entrypoints': ['glInvalidateFramebuffer'],
                              'probes': {'discard-dead-attachment': True}},
                   'workload': {'labels': ['attachment-store'], 'discard_scope': SCOPE},
                   'objective': {'bandwidth': 1}, 'as_of': '2026-11-28'}
        decision = decide(request)
        if decision['status'] != 'EXPERIMENT_REQUIRED':
            raise RuntimeError('attachment lifetime or capability rejected')
        negative = deepcopy(request)
        negative['workload']['discard_scope']['lifecycle'].append({'op': 'consume', 'attachment': 'depth'})
        negative_decision = decide(negative)
        later_consumer_blocked = any('ATTACHMENT_HAS_LATER_CONSUMER' in row['blocked_reasons']
                                     for row in negative_decision['candidates'])
        observations = {
            'baseline': render(host, False, 1),
            'baseline_repeat': render(host, False, 1),
            'candidate': render(host, True, 1),
            'rollback': render(host, False, 1),
            'wrong_depth_control': render(host, False, 0),
        }
        quality = {name: attachments.compare(pixels, GOLDEN) for name, pixels in observations.items()}
        passed = (later_consumer_blocked and
                  all(row['status'] == ('FAIL' if name == 'wrong_depth_control' else 'PASS')
                      for name, row in quality.items()))
        advice = advise({'decision_request': request,
                         'workload': {'workload_id': DISCARD_EXPERIMENT, 'provenance': 'synthetic',
                                      'resolution': [4, 4]},
                         'candidates': [{'id': 'discard-depth', 'experiment': DISCARD_EXPERIMENT,
                                         'fallback': 'baseline', 'capability_supported': True,
                                         'quality': {'pass': passed, 'golden_id': 'analytic-rgba8-depth-test',
                                                     'thresholds': {'max_error': 1}},
                                         'measurement': {'provenance': 'software'}}]})
        report = {'schema_version': 1, 'status': 'HOST_PASS' if passed else 'FAIL',
                  'experiment_id': DISCARD_EXPERIMENT, 'environment': host.metadata,
                  'decision': decision, 'later_consumer_rejected': later_consumer_blocked,
                  'expected_pixels': GOLDEN, 'pixels': observations, 'quality': quality,
                  'advisor': advice, 'production_selection': 'baseline',
                  'aa_scope': 'image correctness', 'performance': 'NOT_MEASURED',
                  'inputs': {str(path.relative_to(ROOT)): sha256(path.read_bytes()).hexdigest()
                             for path in [Path(__file__).resolve(), ROOT / 'benchmarks/attachment_controls/run.py',
                                          ROOT / 'benchmarks/differential/run.py']}}
    finally:
        host.close()
    with output.open('x', encoding='utf-8') as file:
        json.dump(report, file, indent=2)
        file.write('\n')
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--config', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    report = run(json.loads(args.config.read_text(encoding='utf-8')), args.output)
    print(report['status'])
    return report['status'] != 'HOST_PASS'


if __name__ == '__main__':
    sys.exit(main())
