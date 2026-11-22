import copy
import json
import unittest
from unittest.mock import patch

import check_v112_baseline as gate


class BaselineTests(unittest.TestCase):
    def setUp(self):
        self.ledger = json.loads(gate.LEDGER.read_text(encoding='utf-8'))

    def test_bound_history_without_closures(self):
        self.assertEqual(gate.validate(self.ledger)['status'], 'PRESERVED_NOT_CLOSED')

    def test_deleted_obligation_or_changed_threshold(self):
        for mutate in (
            lambda x: x['historical_sources']['docs/v1.1.1/release-gates.json']['obligations'].pop(),
            lambda x: x['retained_minimum'].update(physical_gpu_families=1),
        ):
            with self.subTest(mutation=mutate):
                changed = copy.deepcopy(self.ledger)
                mutate(changed)
                with self.assertRaises(ValueError):
                    gate.validate(changed)

    def test_history_and_ledger_changed_together(self):
        changed = self.ledger['historical_sources']
        changed['docs/release-gates.json']['sha256'] = '0' * 64
        with patch.object(gate, 'snapshot', return_value=changed), self.assertRaisesRegex(ValueError, 'pinned baseline'):
            gate.validate(self.ledger)

    def test_cannot_edit_readiness_state_or_close_by_self_assertion(self):
        for change in (
            {'release_ready': True},
            {'release_authorized': True},
            {'closure_receipts': [{'status': 'PASS'}]},
            {'state': {'implementation': 'PARTIAL', 'verification': 'PASS', 'release': 'READY'}},
        ):
            with self.subTest(change=change), self.assertRaises(ValueError):
                gate.validate({**self.ledger, **change})
