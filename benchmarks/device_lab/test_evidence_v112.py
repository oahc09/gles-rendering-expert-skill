import copy
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import tempfile
import unittest

import evidence_v112 as e
import lab
from test_lab import fixture


class EvidenceTests(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.root = Path(tmp.name)
        self.capture = fixture()
        self.capture['snapshot']['build'] = {'benchmarks/device_lab/probe.cpp': 'a' * 64}
        self.ref = {'schema': e.REF_SCHEMA, 'path': 'captures/software.json', 'collector': 'device-lab',
                    'collector_version': '1', 'source_commit': 'b' * 40, 'captured_at': '2026-11-22T12:00:00Z',
                    'origin': 'runtime', 'platform': 'host', 'backend': 'software', 'device_id': 'lab-01',
                    'scope': {'context_generation': 1, 'surface_generation': 1}}
        self.now = datetime(2026, 11, 22, 13, tzinfo=timezone.utc)
        self.file = self.root / self.ref['path']
        self.file.parent.mkdir()
        self.expect = {'schema': e.EXPECT_SCHEMA, 'max_age_seconds': 3600}
        self.reset()

    def reset(self, set_trust=True):
        raw = json.dumps(self.capture).encode()
        self.save(raw)
        self.expect.update({key: copy.deepcopy(self.ref[key]) for key in
                            ('platform', 'backend', 'device_id', 'source_commit', 'scope')})
        self.expect['environment_sha256'] = e.adapt_legacy(copy.deepcopy(self.capture), self.ref)['environment_sha256']
        if set_trust:
            self.pin()

    def save(self, raw):
        self.file.write_bytes(raw)
        self.ref.update(size=len(raw), sha256=hashlib.sha256(raw).hexdigest())

    def pin(self):
        self.expect['trusted_reference_sha256'] = lab.digest(self.ref)

    def verify(self):
        result = e.verify(self.root, self.ref, self.expect, now=self.now)
        self.assertFalse(result['physical_verified'])
        self.assertEqual(result['counter_measurements'], 'UNKNOWN')
        self.assertEqual(result['performance_claim'], 'NOT_MEASURED')
        return result

    def invalid(self, reason):
        result = self.verify()
        self.assertEqual(result['status'], 'INVALID')
        self.assertEqual(result['reason'], reason)

    def test_pinned_software_is_not_physical_or_performance(self):
        result = self.verify()
        self.assertEqual(result['status'], 'BOUND_SOFTWARE_CORRECTNESS')
        self.assertEqual(result['profile']['driver_version'], 'UNKNOWN')
        self.assertEqual(result['reference']['sha256'], self.ref['sha256'])
        self.assertNotIn('fixture-not-real', str(result))

    def test_handfilled_physical_or_runtime_without_host_pin_stays_declared(self):
        self.expect['trusted_reference_sha256'] = None
        self.assertEqual(self.verify()['status'], 'DECLARED_ONLY')
        self.ref.update(origin='manual', backend='native', platform='Android')
        self.capture['snapshot'].update(backend='native', platform='Android', hardware_kind='physical')
        self.reset()
        self.assertEqual(self.verify()['status'], 'DECLARED_ONLY')

    def test_pinned_runtime_physical_stays_review_required(self):
        self.ref.update(backend='native', platform='Android')
        self.capture['snapshot'].update(backend='native', platform='Android', hardware_kind='physical')
        self.reset()
        self.assertEqual(self.verify()['status'], 'BOUND_RUNTIME_REVIEW_REQUIRED')
        self.capture['snapshot']['hardware_kind'] = 'software'
        self.reset()
        self.assertEqual(self.verify()['status'], 'BOUND_SOFTWARE_CORRECTNESS')

    def test_old_declaration_build_and_unknown_scope_stay_unknown(self):
        self.capture['snapshot']['build'] = 'operator label'
        self.reset()
        self.assertEqual(self.verify()['status'], 'INSUFFICIENT_EVIDENCE')
        self.ref['scope']['context_generation'] = None
        self.capture['snapshot']['context_generation'] = None
        self.reset()
        self.assertEqual(self.verify()['status'], 'INSUFFICIENT_EVIDENCE')

    def test_size_and_hash_are_measured_not_assumed(self):
        self.ref['size'] -= 1
        self.invalid('CAPTURE_SIZE_MISMATCH')
        self.ref['size'] += 1
        self.ref['sha256'] = '0' * 64
        self.invalid('CAPTURE_SHA256_MISMATCH')

    def test_wrong_time_and_collector(self):
        self.ref['collector_version'] = '2'
        self.invalid('UNKNOWN_COLLECTOR_VERSION')
        self.ref['collector_version'] = '1'
        self.ref['captured_at'] = '2026-11-22T11:59:59Z'
        self.invalid('EXPIRED_OR_FUTURE_CAPTURE')
        self.ref['captured_at'] = '2026-11-22T13:00:01Z'
        self.invalid('EXPIRED_OR_FUTURE_CAPTURE')

    def test_untrusted_metadata_cannot_relabel_original_pin(self):
        self.ref['captured_at'] = '2026-11-22T12:40:00Z'
        self.invalid('TRUST_PIN_MISMATCH')

    def test_device_id_commit_and_context_are_separate(self):
        for key, changed in [('device_id', 'lab-02'), ('source_commit', 'a' * 40),
                             ('scope', {'context_generation': 2, 'surface_generation': 1})]:
            with self.subTest(key=key):
                old = self.expect[key]
                self.expect[key] = changed
                self.invalid('EXPECTED_BINDING_MISMATCH_' + key.upper())
                self.expect[key] = old
        self.ref['scope'] = self.expect['scope'] = {'context_generation': 1, 'surface_generation': 2}
        self.invalid('CAPTURE_SCOPE_MISMATCH')

    def test_same_renderer_different_driver_or_build_invalidates_environment(self):
        for key, changed in [('gl_version', 'different driver version'),
                             ('build', {'benchmarks/device_lab/probe.cpp': 'c' * 64})]:
            with self.subTest(key=key):
                old = self.capture['snapshot'][key]
                self.capture['snapshot'][key] = changed
                self.save(json.dumps(self.capture).encode())
                self.pin()
                self.invalid('ENVIRONMENT_MISMATCH')
                self.capture['snapshot'][key] = old

    def test_unsafe_relative_paths_and_links_are_refused(self):
        for path in ('../software.json', '/etc/passwd', 'captures\\software.json', 'captures/NUL',
                     'captures//software.json', 'captures/a.', 'C:/software.json'):
            self.ref['path'] = path
            self.invalid('INVALID_RELATIVE_PATH')
        os.symlink(self.file, self.root / 'link.json')
        self.ref['path'] = 'link.json'
        self.invalid('CAPTURE_PATH_UNAVAILABLE')
        os.symlink(self.file.parent, self.root / 'link-dir')
        self.ref['path'] = 'link-dir/software.json'
        self.invalid('CAPTURE_PATH_UNAVAILABLE')
        os.link(self.file, self.root / 'hard.json')
        self.ref['path'] = 'hard.json'
        self.invalid('CAPTURE_NOT_REGULAR')

    def test_rejects_broken_json_duplicates_nonfinite_or_old_fail(self):
        for raw, reason in [(b'{', 'INVALID_JSON'), (b'{"status":1,"status":2}', 'DUPLICATE_JSON_KEY'),
                            (b'{"x":NaN}', 'NONFINITE_JSON'), (b'{"x":1e999}', 'INVALID_JSON')]:
            self.save(raw)
            self.invalid(reason)
        self.capture['snapshot']['limits']['overflow'] = int('9' * 400)
        self.save(json.dumps(self.capture).encode())
        self.invalid('LEGACY_CAPTURE_INVALID')
        del self.capture['snapshot']['limits']['overflow']
        self.capture['correctness_events'][0]['status'] = 'FAIL'
        self.save(json.dumps(self.capture).encode())
        self.invalid('LEGACY_CAPTURE_INVALID')

    def test_entry_presence_is_not_format_evidence(self):
        self.capture['snapshot']['function_entries']['eglCreateImageKHR'] = True
        self.capture['snapshot']['formats']['external_image'] = None
        self.reset()
        self.assertEqual(self.verify()['status'], 'BOUND_SOFTWARE_CORRECTNESS')
        self.assertEqual(self.verify()['profile']['counter_measurements'], 'UNKNOWN')


if __name__ == '__main__':
    unittest.main()
