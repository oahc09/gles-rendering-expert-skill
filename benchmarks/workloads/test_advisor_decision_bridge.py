import copy
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'tools'))
from optimization_advisor import advise


def kiosk():
    return {'workload': {'workload_id': 'es30-kiosk-portrait-preview', 'provenance': 'synthetic',
        'resolution': [1080, 2400], 'metrics': {
            name: {'value': value, 'unit': unit, 'sample_count': 60, 'tool': 'authored', 'raw_trace': 'none'}
            for name, value, unit in [('compute_ms', 9, 'ms'), ('dispatch_count', 1, 'count')]}},
        'candidates': [{'id': 'portrait-compute', 'experiment': 'shader-advanced-v1',
            'fallback': 'Keep validated fragment-only filter', 'labels': ['COMPUTE'],
            'capability_supported': True, 'estimated_gain': 1, 'confidence': 1}]}


def context(gles='3.1'):
    return {'schema_version': 1, 'as_of': '2026-11-22', 'objective': {'frame_time': 1},
            'workload': {'labels': ['compute']},
            'target': {'gles': gles, 'extensions': [], 'entrypoints': ['glDispatchCompute', 'glMemoryBarrier'],
                       'probes': {'compute-to-fragment': True}}}


class AdvisorDecisionBridge(unittest.TestCase):
    def test_es30_kiosk_fails_closed_even_with_caps_and_probe_claims(self):
        request = kiosk()
        self.assertEqual(advise(request)['candidates'][0]['decision_alignment']['status'],
                         'DECISION_CONTEXT_REQUIRED')
        request['decision_request'] = context('3.0')
        result = advise(request)['candidates'][0]
        self.assertEqual(result['status'], 'INSUFFICIENT_EVIDENCE')
        self.assertEqual(result['priority_score'], 0)
        self.assertIn('NOT_CORE:glDispatchCompute', result['decision_alignment']['blocked_reasons'])

    def test_compatible_device_gets_hypothesis_only_and_deterministic_result(self):
        request = kiosk()
        request['decision_request'] = context()
        result = advise(request)
        candidate = result['candidates'][0]
        self.assertEqual(candidate['status'], 'RECOMMENDED_FOR_EXPERIMENT')
        self.assertEqual(candidate['decision_alignment']['strategy'], 'compute-to-fragment')
        self.assertEqual(candidate['decision_alignment']['evidence'], 'DECLARED_INPUTS_ONLY')
        self.assertFalse(candidate['decision_alignment']['execution_authorized'])
        self.assertFalse(candidate['auto_accept'])
        self.assertFalse(result['automatic_renderer_mutation'])
        self.assertIsNone(candidate['gain_fraction'])
        self.assertEqual(result, advise(copy.deepcopy(request)))

    def test_probe_entrypoint_and_scope_never_admit_by_priority_weight(self):
        for name, mutate, expected in (
            ('missing barrier', lambda d: d['target']['entrypoints'].remove('glMemoryBarrier'), 'BLOCKED'),
            ('probe failure', lambda d: d['target']['probes'].update({'compute-to-fragment': False}), 'BLOCKED'),
            ('unrun probe', lambda d: d['target']['probes'].clear(), 'PROBE_REQUIRED'),
            ('caller-only analysis', lambda d: d.update(allowed_actions=['analyze']), 'ANALYZE_ONLY'),
        ):
            with self.subTest(case=name):
                request = kiosk()
                request['decision_request'] = context()
                mutate(request['decision_request'])
                result = advise(request)['candidates'][0]
                self.assertEqual(result['decision_alignment']['status'], expected)
                self.assertEqual(result['status'], 'INSUFFICIENT_EVIDENCE')
                self.assertEqual(result['priority_score'], 0)

    def test_wallpaper_startup_cannot_route_to_steady_state_graph_scaling(self):
        request = kiosk()
        request['workload'].update(workload_id='wallpaper-preview-cold-start', metrics={
            name: {'value': value, 'unit': unit, 'sample_count': 60, 'tool': 'authored', 'raw_trace': 'none'}
            for name, value, unit in [('bandwidth_pct_peak', 88, 'percent'), ('gpu_ms', 11, 'ms')]})
        request['candidates'][0].update(id='steady-state-scaling', experiment='rgba8-graph-scale-replay-v1',
                                        labels=['BANDWIDTH'])
        self.assertEqual(advise(request)['candidates'][0]['status'], 'RECOMMENDED_FOR_EXPERIMENT')
        request['decision_request'] = context()
        request['decision_request']['objective'] = {'startup': 1}
        request['decision_request']['workload']['labels'] = ['bandwidth', 'msaa']
        result = advise(request)
        self.assertEqual(result['objective_evaluation']['status'], 'UNSUPPORTED_GOALS')
        self.assertEqual(result['candidates'][0]['status'], 'INSUFFICIENT_EVIDENCE')

    def test_mobile_postfx_invalid_fallback_and_failed_quality_are_hard_stops(self):
        request = kiosk()
        request['workload'].update(workload_id='product-preview-postfx', metrics={
            name: {'value': value, 'unit': unit, 'sample_count': 60, 'tool': 'authored', 'raw_trace': 'none'}
            for name, value, unit in [('fragment_alu_pct', 86, 'percent'), ('gpu_ms', 10, 'ms')]})
        candidate = request['candidates'][0]
        candidate.update(experiment='postfx-resolution-loss-v1', labels=['FRAGMENT_ALU'])
        for invalid in ('', '   ', ['baseline'], None):
            with self.subTest(fallback=invalid):
                candidate['fallback'] = invalid
                result = advise(request)['candidates'][0]
                self.assertEqual(result['status'], 'INSUFFICIENT_EVIDENCE')
                self.assertFalse(result['ranking_basis']['completeness_checks']['fallback'])
        candidate['fallback'] = 'Keep full-resolution postprocess'
        self.assertEqual(advise(request)['candidates'][0]['status'], 'RECOMMENDED_FOR_EXPERIMENT')
        candidate['quality'] = {'pass': False}
        self.assertEqual(advise(request)['candidates'][0]['status'], 'REJECTED_BY_QUALITY')

    def test_cli_runs_same_gate_and_refuses_invalid_decision_context(self):
        request = kiosk()
        request['decision_request'] = context('3.0')
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'kiosk.json'
            for invalid in (False, True):
                if invalid:
                    request['decision_request']['unrecognized'] = True
                path.write_text(json.dumps(request), encoding='utf-8')
                completed = subprocess.run([sys.executable, str(ROOT / 'tools/optimization_advisor.py'), str(path)],
                                           capture_output=True, encoding='utf-8', timeout=20, check=False)
                output = json.loads(completed.stdout)
                if invalid:
                    self.assertEqual(completed.returncode, 2)
                    self.assertEqual(output['status'], 'INVALID')
                else:
                    self.assertEqual(completed.returncode, 0, completed.stderr)
                    self.assertEqual(output['candidates'][0]['status'], 'INSUFFICIENT_EVIDENCE')
