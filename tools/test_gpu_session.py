import unittest
from copy import deepcopy

from gpu_session import evaluate


class SessionTest(unittest.TestCase):
    def test_probe_result_advances_or_stops_the_session(self):
        request = {'schema_version': 1,
                   'target': {'gles': '3.0', 'extensions': [], 'entrypoints': ['glTexParameteri'],
                              'probes': {'texture-mip-selection': True}},
                   'workload': {'labels': ['texture']}, 'objective': {'quality': 1},
                   'as_of': '2026-11-28'}
        ready = {'schema_version': 1, 'budget_remaining': {'seconds': 5, 'frames': 60, 'resource_bytes': 2 ** 20},
                 'facts': {'backend': 'mesa-software', 'driver': 'llvmpipe-test',
                           'timer_available': False, 'quality_oracle': 'reference-image',
                           'evidence_conflict': False, 'environment_changed': False},
                 'constraints': {}, 'attempted_probes': []}
        cases = [
            ('backend', None, 'execution-environment'),
            ('driver', None, 'execution-environment'),
            ('timer_available', None, 'timing-capability'),
            ('quality_oracle', None, 'quality-oracle'),
            ('evidence_conflict', True, 'resolve-evidence-conflict'),
        ]
        for fact, value, probe_id in cases:
            with self.subTest(fact=fact):
                pending = deepcopy(ready)
                pending['facts'][fact] = value
                result = evaluate(request, pending)
                self.assertEqual(result['next_probe']['id'], probe_id)
                pending['attempted_probes'] = [probe_id]
                result = evaluate(request, pending)
                self.assertEqual(result['stop_reason'], 'PROBE_UNRESOLVED:' + probe_id)
                pending['facts'][fact] = ready['facts'][fact]
                result = evaluate(request, pending)
                self.assertEqual(result['status'], 'EXPERIMENT_REQUIRED')
                self.assertFalse(result['gpu_time_available'])
        limited = deepcopy(ready)
        limited['constraints']['quality_error'] = {
            'unit': 'normalized', 'maximum': 0.05, 'observed': 0.1, 'source': 'test-oracle',
        }
        self.assertEqual(evaluate(request, limited)['stop_reason'], 'HARD_LIMIT_EXCEEDED:quality_error')
        ready['budget_remaining']['frames'] = 0
        self.assertEqual(evaluate(request, ready)['stop_reason'], 'PROBE_BUDGET_EXHAUSTED')


if __name__ == '__main__':
    unittest.main()
