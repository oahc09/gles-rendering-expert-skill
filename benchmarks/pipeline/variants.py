"""Conservative GLES feature validation and driver-local binary-cache policy."""
import argparse
import hashlib
import itertools
import re
import json

VERSIONS = ('3.0', '3.1', '3.2')
FEATURES = {'compute': '3.1', 'ssbo': '3.1', 'image': '3.1', 'geometry': '3.2',
            'tessellation': '3.2', 'pbr': '3.0', 'unlit': '3.0', 'external_texture': '3.0'}

def strings(value, name):
    if not isinstance(value, list) or any(not isinstance(x, str) or not x for x in value) or len(set(value)) != len(value):
        raise ValueError(name + ' must be a unique string array')
    return value

def validate(variant):
    if not isinstance(variant, dict): raise ValueError('variant must be an object')
    version = variant.get('gles')
    if version not in VERSIONS: raise ValueError('gles must be 3.0, 3.1 or 3.2')
    features = strings(variant.get('features', []), 'features')
    extensions = strings(variant.get('extensions', []), 'extensions')
    required = strings(variant.get('required_extensions', []), 'required_extensions')
    errors = []
    for feature in features:
        if feature not in FEATURES: errors.append('UNKNOWN_FEATURE:' + feature)
        elif version < FEATURES[feature]: errors.append('GLES_VERSION:' + feature + ':requires ' + FEATURES[feature])
    if {'pbr', 'unlit'} <= set(features): errors.append('MUTUALLY_EXCLUSIVE:pbr,unlit')
    if variant.get('quality') not in ('low', 'medium', 'high'): errors.append('QUALITY_TIER')
    for extension in required:
        if extension not in extensions: errors.append('MISSING_EXTENSION:' + extension)
    if 'external_texture' in features and 'GL_OES_EGL_image_external_essl3' not in extensions:
        errors.append('MISSING_EXTENSION:GL_OES_EGL_image_external_essl3')
    macros = variant.get('macros', {})
    if not isinstance(macros, dict) or any(not isinstance(k, str) or not k.isidentifier() or not isinstance(v, str) for k, v in macros.items()):
        raise ValueError('macros must map identifiers to strings')
    return errors

def generate(feature_axes, versions, extensions, qualities, *, max_candidates=4096, max_variants=128):
    """Refuse exponential work before expansion; deterministic accepted-prefix pruning."""
    strings(feature_axes, 'feature_axes'); strings(versions, 'versions'); strings(extensions, 'extensions'); strings(qualities, 'qualities')
    for name, value in [('max_candidates', max_candidates), ('max_variants', max_variants)]:
        if type(value) is not int or value < 1: raise ValueError(name + ' must be positive integer')
    count = (2 ** len(feature_axes)) * len(versions) * len(qualities)
    if count > max_candidates: raise ValueError('GENERATION_BUDGET:' + str(count))
    accepted, rejected, pruned = [], [], 0
    for version, quality, flags in itertools.product(versions, qualities, itertools.product((False, True), repeat=len(feature_axes))):
        row = dict(gles=version, quality=quality, extensions=extensions, features=[f for f, on in zip(feature_axes, flags) if on])
        errors = validate(row)
        if errors: rejected.append(dict(variant=row, errors=errors))
        elif len(accepted) < max_variants: accepted.append(row)
        else: pruned += 1
    return dict(variants=accepted, rejected=rejected, pruned=pruned, candidates=count)

def cache_key(source, macros, options, device):
    if not isinstance(source, str) or not source: raise ValueError('source required')
    if not isinstance(macros, dict) or any(not isinstance(k, str) or not isinstance(v, str) for k,v in macros.items()): raise ValueError('macros must map strings')
    strings(options, 'options')
    if not isinstance(device, dict): raise ValueError('device required')
    for field in ('vendor', 'renderer', 'version', 'driver', 'backend', 'material_abi'):
        if not isinstance(device.get(field), str) or not device[field]: raise ValueError('device.' + field + ' required')
    strings(device.get('extensions'), 'device.extensions')
    identity = {k: device[k] for k in ('vendor','renderer','version','driver','backend','material_abi')}
    identity['extensions'] = sorted(device['extensions'])
    return hashlib.sha256(json.dumps([source, macros, options, identity], sort_keys=True, separators=(',', ':')).encode()).hexdigest()

def load_program(record, key, supported_formats, load_binary, compile_source, *, max_binary_bytes=16 * 1024 * 1024):
    """Callbacks perform actual GL operations. Loader MUST return GL_LINK_STATUS."""
    strings_key = isinstance(key, str) and re.fullmatch(r'[0-9a-f]{64}', key) is not None
    if type(max_binary_bytes) is not int or not 1 <= max_binary_bytes <= 64 * 1024 * 1024: raise ValueError('max_binary_bytes must be 1..67108864')
    if not strings_key or not isinstance(supported_formats, list) or any(type(x) is not int or x < 0 for x in supported_formats): raise ValueError('invalid cache key/formats')
    reason = 'CACHE_MISS'
    if isinstance(record, dict) and record.get('key') == key:
        if type(record.get('format')) is not int or record.get('format') not in supported_formats: reason = 'FORMAT_UNSUPPORTED'
        elif not isinstance(record.get('binary'), bytes) or not record['binary']: reason = 'BINARY_INVALID'
        elif len(record['binary']) > max_binary_bytes: reason = 'BINARY_TOO_LARGE'
        else:
            try:
                if load_binary(record['format'], record['binary']) is True: return {'path': 'binary', 'reason': 'LINK_SUCCESS'}
                reason = 'BINARY_LINK_FAILED'
            except Exception: reason = 'BINARY_LOAD_ERROR'
    # Both corrupt binaries and stale device keys fall back, never silently succeed.
    if compile_source() is not True: raise RuntimeError('SOURCE_COMPILE_LINK_FAILED:' + reason)
    return {'path': 'source', 'reason': reason}

if __name__ == '__main__':
    parser = argparse.ArgumentParser(); parser.add_argument('manifest'); args = parser.parse_args()
    try:
        errors = validate(json.load(open(args.manifest))); print(json.dumps({'errors': errors})); raise SystemExit(bool(errors))
    except (ValueError, OSError) as exc: parser.exit(2, str(exc) + '\n')
