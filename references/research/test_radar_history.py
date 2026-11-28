"""Fresh checkout boundaries, no live GitHub or real promotion."""
import datetime as dt
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import update_radar as radar


def row(source, ident, day):
    return dict(source=source, id=ident, event_at=f"{day}T12:00:00Z")


class RadarHistoryTest(unittest.TestCase):
    def test_weekly_monthly_fresh_archive_and_same_day_run(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            fixture = root / 'input.json'

            def run(batch, start, end, rows, prior=None):
                fixture.write_text(json.dumps(rows))
                archive = root / batch
                history = root / f'{batch}.json'
                argv = ['update_radar.py', '--archive', str(archive), '--input', str(fixture),
                        '--start', start, '--end', end, '--history-out', str(history)]
                if prior:
                    argv += ['--history-in', str(prior)]
                with patch('sys.argv', argv):
                    self.assertEqual(radar.main(), 0)
                return json.loads((archive / end / 'radar.json').read_text()), history

            first = row('cocos-engine', '123', '2026-11-21')
            next_ = row('godot', '123', '2026-11-23')  # Same ID on a distinct source is not a duplicate.
            newest = row('unity-graphics', '456', '2026-11-23')
            a, a_state = run('weekly', '2026-11-16', '2026-11-22', [first])
            b, b_state = run('monthly', '2026-08-26', '2026-11-23', [first, next_], a_state)
            c, c_state = run('weekly-same-day', '2026-11-17', '2026-11-23', [first, next_, newest], b_state)
            self.assertEqual(a['history']['mode'], 'NO_PRIOR_COMPLETE_HISTORY')
            self.assertEqual(a['items'], [first])
            self.assertEqual(b['history']['prior_through'], '2026-11-22')
            self.assertEqual(b['items'], [next_])
            self.assertEqual(c['history']['retained_identities'], 2)
            self.assertEqual(c['items'], [newest])
            self.assertEqual(len(json.loads(c_state.read_text())['items']), 3)

    def test_incomplete_retrieval_reports_failure_and_never_publishes_history(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            argv = ['update_radar.py', '--archive', str(root / 'reports'),
                    '--source', 'cocos-engine', '--start', '2026-11-20', '--end', '2026-11-22',
                    '--history-out', str(root / 'history.json')]
            with patch('sys.argv', argv), patch.object(radar, 'collect',
                                                       return_value=([row('cocos-engine', '42', '2026-11-21')], False)):
                self.assertEqual(radar.main(), 2)
            self.assertFalse((root / 'history.json').exists())
            result = json.loads((root / 'reports/2026-11-22/radar.json').read_text())
            self.assertEqual(result['status'], 'INCOMPLETE')
            self.assertFalse(result['history']['write_admitted'])

    def test_expiry_and_rejection(self):
        newest = dt.date(2026, 11, 27)
        prior = dt.date(2026, 11, 20)
        with tempfile.TemporaryDirectory() as d:
            path = Path(d) / 'history.json'
            radar.write_history(path, prior, {}, [
                row('godot', 'outdated', '2026-08-25'),
                row('unity-graphics', 'boundary', '2026-08-30'),
                row('cocos-engine', 'recent', '2026-11-20'),
            ])
            self.assertEqual(len(json.loads(path.read_text())['items']), 3)
            self.assertEqual(set(radar.read_history(path, newest)[1]),
                             {'unity-graphics:boundary', 'cocos-engine:recent'})
            with self.assertRaisesRegex(ValueError, 'newer'):
                radar.read_history(path, dt.date(2026, 11, 19))
            with self.assertRaises(FileExistsError):
                radar.write_history(path, newest, {}, [])
            payload = json.loads(path.read_text())
            payload['items'].append(payload['items'][0])
            path.write_text(json.dumps(payload))
            with self.assertRaisesRegex(ValueError, 'duplicate'):
                radar.read_history(path, newest)
            payload['items'] = [{'source': 'godot', 'id': '../../escape', 'event_day': '2026-11-20'}]
            path.write_text(json.dumps(payload))
            with self.assertRaisesRegex(ValueError, 'invalid history item id'):
                radar.read_history(path, newest)
