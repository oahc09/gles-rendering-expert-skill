#!/usr/bin/env python3
"""Read-only W2 adapter for a bounded legacy device-lab capture."""

import argparse
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import re
import stat
import sys

import lab

PROFILE_SCHEMA = 'gles.device-profile/v1'
REF_SCHEMA = 'gles.device-evidence-ref/v1'
EXPECT_SCHEMA = 'gles.device-evidence-expected/v1'
MAX_CAPTURE = 2 * 1024 * 1024
MAX_METADATA = 64 * 1024
HEX64 = re.compile(r'[a-f0-9]{64}')
COMMIT = re.compile(r'[a-f0-9]{40}')
TOKEN = re.compile(r'[A-Za-z0-9][A-Za-z0-9_.-]{0,95}')
PATH_TOKEN = re.compile(r'[A-Za-z0-9_-][A-Za-z0-9_.-]{0,127}')
RESERVED_DEVICE = re.compile(r'(?:CON|PRN|AUX|NUL|COM[0-9]|LPT[0-9])(?:\..*)?', re.IGNORECASE)
PLATFORMS = {'host', 'Android', 'Windows', 'EmbeddedLinux'}
COLLECTOR = ('device-lab', '1')
ORIGINS = {'manual', 'runtime'}
REF_KEYS = {'schema', 'path', 'size', 'sha256', 'collector', 'collector_version', 'source_commit',
            'captured_at', 'origin', 'platform', 'backend', 'device_id', 'scope'}
EXPECTED_KEYS = {'schema', 'device_id', 'platform', 'backend', 'source_commit',
                 'environment_sha256', 'scope', 'max_age_seconds', 'trusted_reference_sha256'}
SCOPE_KEYS = {'context_generation', 'surface_generation'}


class Rejected(ValueError):
    """Safe, non-payload diagnostic."""


def check(value, reason):
    if not value:
        raise Rejected(reason)


def exact(value, keys, reason):
    check(type(value) is dict and set(value) == keys, reason)


def json_object(raw):
    def pairs(items):
        output = {}
        for key, value in items:
            check(key not in output, 'DUPLICATE_JSON_KEY')
            output[key] = value
        return output

    def invalid_literal(_):
        raise Rejected('NONFINITE_JSON')

    try:
        obj = json.loads(raw.decode('utf-8'), object_pairs_hook=pairs, parse_constant=invalid_literal)
        check(type(obj) is dict, 'JSON_OBJECT_REQUIRED')
        # Python accepts 1e999 as a nonfinite float via parse_float. Canonical
        # encoding also rejects it in nested optional legacy fields.
        json.dumps(obj, allow_nan=False)
        return obj
    except Rejected:
        raise
    except (UnicodeError, ValueError, RecursionError):
        raise Rejected('INVALID_JSON') from None


def matches(pattern, value):
    return type(value) is str and pattern.fullmatch(value) is not None


def capture_time(value):
    check(type(value) is str and
          re.fullmatch(r'[0-9]{4}-[0-9]{2}-[0-9]{2}T[0-9]{2}:[0-9]{2}:[0-9]{2}Z', value),
          'INVALID_CAPTURE_TIME')
    try:
        return datetime.fromisoformat(value[:-1] + '+00:00')
    except ValueError:
        raise Rejected('INVALID_CAPTURE_TIME') from None


def path_parts(value):
    check(type(value) is str and 0 < len(value) <= 512, 'INVALID_RELATIVE_PATH')
    parts = value.split('/')
    check(1 <= len(parts) <= 16 and all(matches(PATH_TOKEN, part) and not part.endswith('.')
                                      and not RESERVED_DEVICE.fullmatch(part) for part in parts),
          'INVALID_RELATIVE_PATH')
    return parts


def capture_bytes(root, relative, size):
    # A trusted, immutable evidence root is required. Walk the relative path
    # with directory descriptors to refuse symlinks even after a rename.
    parts = path_parts(relative)
    check(hasattr(os, 'O_NOFOLLOW') and os.open in os.supports_dir_fd,
          'HOST_NO_SAFE_RELATIVE_READ')
    directory = os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW
    leaf = os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK
    opened = []
    try:
        opened.append(os.open(root, directory))
        for part in parts[:-1]:
            opened.append(os.open(part, directory, dir_fd=opened[-1]))
        fd = os.open(parts[-1], leaf, dir_fd=opened[-1])
        opened.append(fd)
        before = os.fstat(fd)
        check(stat.S_ISREG(before.st_mode) and before.st_nlink == 1, 'CAPTURE_NOT_REGULAR')
        check(before.st_size == size, 'CAPTURE_SIZE_MISMATCH')
        with os.fdopen(os.dup(fd), 'rb') as stream:
            raw = stream.read(size + 1)
        after = os.fstat(fd)
        check(len(raw) == size and
              (before.st_size, before.st_mtime_ns, before.st_ctime_ns) ==
              (after.st_size, after.st_mtime_ns, after.st_ctime_ns),
              'CAPTURE_CHANGED_DURING_READ')
        return raw
    except OSError:
        raise Rejected('CAPTURE_PATH_UNAVAILABLE') from None
    finally:
        for fd in reversed(opened):
            os.close(fd)


def scope_value(scope):
    exact(scope, SCOPE_KEYS, 'INVALID_SCOPE')
    check(all(value is None or (type(value) is int and 1 <= value <= 2 ** 53 - 1)
              for value in scope.values()), 'INVALID_SCOPE')
    return {name: scope[name] for name in sorted(SCOPE_KEYS)}


def metadata_common(row):
    check(matches(TOKEN, row['device_id']), 'INVALID_DEVICE_ID')
    check(type(row['platform']) is str and row['platform'] in PLATFORMS
          and type(row['backend']) is str and row['backend'] in lab.BACKENDS,
          'INVALID_PLATFORM_BACKEND')
    check(matches(COMMIT, row['source_commit']), 'INVALID_SOURCE_COMMIT')
    scope_value(row['scope'])


def adapt_legacy(record, reference):
    """Adapt a lab v1 stdout CAPTURED record without inferring missing telemetry."""
    if record.get('status') == 'BLOCKED_BY_HARDWARE':
        raise Rejected('CAPTURE_BLOCKED_BY_HARDWARE')
    try:
        check(record.get('performance_claim', 'NOT_MEASURED') == 'NOT_MEASURED', 'UNSUPPORTED_PERFORMANCE_CLAIM')
        lab.validate(record, {'platform': reference['platform'], 'backend': reference['backend']})
    except Rejected:
        raise
    except (ValueError, TypeError, KeyError, AttributeError, OverflowError):
        raise Rejected('LEGACY_CAPTURE_INVALID') from None
    snapshot = record['snapshot']
    for key in ('os', 'os_build', 'device', 'egl_vendor', 'egl_version', 'gl_vendor',
                'gl_renderer', 'gl_version', 'glsl_version'):
        value = snapshot[key]
        check(value is None or (type(value) is str and 0 < len(value) <= 512), 'INVALID_SNAPSHOT_FIELD')
    for key in ('egl_extensions', 'gl_extensions'):
        tokens = snapshot[key]
        check(len(tokens) <= 2048 and all(matches(TOKEN, token) for token in tokens)
              and len(set(tokens)) == len(tokens), 'INVALID_EXTENSION_TOKENS')
    build = snapshot['build']
    check((type(build) is str and 0 < len(build) <= 512)
          or (type(build) is dict and len(build) <= 64
              and all(matches(HEX64, value) for value in build.values())), 'INVALID_SNAPSHOT_BUILD')
    build_known = type(build) is dict and bool(build)
    if build_known:
        for path in build:
            path_parts(path)
    check(snapshot['api_level'] is None or (type(snapshot['api_level']) is int and
          1 <= snapshot['api_level'] <= 500), 'INVALID_API_LEVEL')
    observed_scope = scope_value({name: snapshot[name] for name in SCOPE_KEYS})
    check(observed_scope == reference['scope'], 'CAPTURE_SCOPE_MISMATCH')
    environment = {key: snapshot[key] for key in sorted(lab.FIELDS - SCOPE_KEYS)}
    for key in ('egl_extensions', 'gl_extensions'):
        environment[key] = sorted(environment[key])
    # Retain the capture's actual snapshot identity alongside the legacy digest;
    # it is not a durable global identity of a GPU or a verified physical device.
    return {'schema': PROFILE_SCHEMA, 'platform': snapshot['platform'],
            'backend': snapshot['backend'], 'hardware_kind_reported': snapshot['hardware_kind'],
            'lab_fingerprint_sha256': record['fingerprint'],
            'environment_sha256': lab.digest(environment), 'scope': observed_scope,
            'driver_version': 'UNKNOWN', 'abi': 'UNKNOWN',
            'build_binding': 'RECORDED_COMPONENT_HASHES' if build_known else 'UNKNOWN',
            'counter_measurements': 'UNKNOWN', 'performance_claim': 'NOT_MEASURED'}


def verify(root, reference, expected, *, now):
    """Opening paths is local-only. Expected bindings must come from the trusted host."""
    try:
        return _verify(root, reference, expected, now)
    except Rejected as error:
        return {'status': 'INVALID', 'reason': str(error), 'physical_verified': False,
                'performance_claim': 'NOT_MEASURED', 'counter_measurements': 'UNKNOWN'}


def _verify(root, ref, expected, now):
    exact(ref, REF_KEYS, 'INVALID_EVIDENCE_REFERENCE')
    exact(expected, EXPECTED_KEYS, 'INVALID_EXPECTED_BINDINGS')
    check(ref['schema'] == REF_SCHEMA and expected['schema'] == EXPECT_SCHEMA, 'INVALID_SCHEMA')
    check((ref['collector'], ref['collector_version']) == COLLECTOR, 'UNKNOWN_COLLECTOR_VERSION')
    check(type(ref['origin']) is str and ref['origin'] in ORIGINS, 'INVALID_ORIGIN')
    metadata_common(ref)
    metadata_common(expected)
    check(type(ref['size']) is int and 0 < ref['size'] <= MAX_CAPTURE, 'INVALID_CAPTURE_SIZE')
    check(matches(HEX64, ref['sha256']) and matches(HEX64, expected['environment_sha256']),
          'INVALID_HASH')
    pin = expected['trusted_reference_sha256']
    check(pin is None or matches(HEX64, pin), 'INVALID_TRUST_PIN')
    check(type(expected['max_age_seconds']) is int and 1 <= expected['max_age_seconds'] <= 31 * 86400,
          'INVALID_MAX_AGE')
    check(isinstance(now, datetime) and now.utcoffset() is not None, 'TRUSTED_CLOCK_REQUIRED')
    captured = capture_time(ref['captured_at'])
    age = (now - captured).total_seconds()
    check(0 <= age <= expected['max_age_seconds'], 'EXPIRED_OR_FUTURE_CAPTURE')
    for field in ('device_id', 'platform', 'backend', 'source_commit', 'scope'):
        check(ref[field] == expected[field], 'EXPECTED_BINDING_MISMATCH_' + field.upper())
    body = capture_bytes(root, ref['path'], ref['size'])
    check(hashlib.sha256(body).hexdigest() == ref['sha256'], 'CAPTURE_SHA256_MISMATCH')
    profile = adapt_legacy(json_object(body), ref)
    check(profile['environment_sha256'] == expected['environment_sha256'], 'ENVIRONMENT_MISMATCH')
    if pin is not None:
        check(pin == lab.digest(ref), 'TRUST_PIN_MISMATCH')
    if ref['origin'] == 'manual' or pin is None:
        status = 'DECLARED_ONLY'
    elif (ref['backend'] == 'unknown' or profile['hardware_kind_reported'] == 'unknown'
          or profile['build_binding'] == 'UNKNOWN' or any(value is None for value in ref['scope'].values())):
        status = 'INSUFFICIENT_EVIDENCE'
    elif profile['hardware_kind_reported'] == 'software':
        status = 'BOUND_SOFTWARE_CORRECTNESS'
    else:
        status = 'BOUND_RUNTIME_REVIEW_REQUIRED'
    return {'status': status, 'reference': {k: ref[k] for k in ('schema', 'path', 'sha256', 'size',
            'collector', 'collector_version', 'source_commit', 'captured_at', 'origin')},
            'profile': profile, 'physical_verified': False, 'performance_claim': 'NOT_MEASURED',
            'counter_measurements': 'UNKNOWN'}


def read_metadata(path):
    check(hasattr(os, 'O_NOFOLLOW') and hasattr(os, 'O_NONBLOCK'),
          'HOST_NO_SAFE_METADATA_READ')
    fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
    with os.fdopen(fd, 'rb') as stream:
        info = os.fstat(stream.fileno())
        check(stat.S_ISREG(info.st_mode), 'METADATA_NOT_REGULAR')
        check(info.st_size <= MAX_METADATA, 'METADATA_TOO_LARGE')
        payload = stream.read(MAX_METADATA + 1)
    check(len(payload) <= MAX_METADATA, 'METADATA_TOO_LARGE')
    return json_object(payload)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    for key in ('root', 'reference', 'expected'):
        parser.add_argument('--' + key, required=True, type=Path)
    args = parser.parse_args(argv)
    try:
        result = verify(args.root, read_metadata(args.reference), read_metadata(args.expected),
                        now=datetime.now(timezone.utc))
    except (OSError, Rejected):
        result = {'status': 'INVALID', 'reason': 'METADATA_UNAVAILABLE_OR_INVALID',
                  'physical_verified': False, 'performance_claim': 'NOT_MEASURED',
                  'counter_measurements': 'UNKNOWN'}
    print(json.dumps(result, indent=2, sort_keys=True))
    return 2 if result['status'] == 'INVALID' else 0


if __name__ == '__main__':
    sys.exit(main())
