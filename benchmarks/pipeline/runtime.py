#!/usr/bin/env python3
"""Actual EGL/GLES acceptance captures against independent analytic references.

Goldens are CPU arithmetic, never captured from the renderer under test. Existing
strict P6 codec/SSIM is reused. Runtime failures cannot silently become PASS.
"""
import argparse
from datetime import datetime, timezone
import hashlib
import importlib.util
import json
import math
import os
from pathlib import Path
import struct
import subprocess

ROOT = Path(__file__).resolve().parents[2]
HERE = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location('pipeline_visual_compare', ROOT / 'benchmarks/visual_quality/compare.py')
visual = importlib.util.module_from_spec(spec)
spec.loader.exec_module(visual)
SIZE = 32
SCENES = {
    'C01': ('sRGB texture decode, linear lighting, sRGB FBO encode', 2),
    'C02': ('Premultiplied glass gradient and particle disk', 2),
    'C03': ('RGBA16F radiance, Reinhard tonemap', 1),
    'C04': ('Scene, bright extraction, blur, bloom composite', 2),
    'C05': ('Reflected std140 material and RGBA8 base color texture', 1),
    'C06': ('RGBA8 multisample blend and resolve followed by tonemap', 1),
}
SCENARIO_REFERENCE = {'S01': None, 'S02': None, 'S03': 'C05', 'S04': 'C04',
                      'S05': None, 'S06': 'C06', 'S07': 'C02', 'S08': 'C01',
                      'S09': 'C05', 'S10': None}


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def quantize(x):
    return max(0, min(255, int(math.floor(x * 255 + .5))))


def half(x):
    return struct.unpack('e', struct.pack('e', x))[0]


def srgb_decode(x):
    return x / 12.92 if x <= .04045 else ((x + .055) / 1.055) ** 2.4


def srgb_encode(x):
    return 12.92 * x if x <= .0031308 else 1.055 * x ** (1 / 2.4) - .055


def reference(scene):
    """Top-down RGB8 oracle; all intermediate storage quantization explicit."""
    if scene not in SCENES:
        raise ValueError('Unknown analytic scene')
    pixels = []
    for y in range(SIZE - 1, -1, -1):
        for x in range(SIZE):
            u, v = (x + .5) / SIZE, (y + .5) / SIZE
            if scene == 'C01':
                values = [quantize(srgb_encode(srgb_decode(c / 255) * u)) for c in (128, 192, 64)]
            elif scene == 'C02':
                alpha = .25 + .5 * u
                values = [quantize(c * alpha + quantize(b) / 255 * (1 - alpha))
                          for c, b in zip((.8, .4, .2), (.1, .2, .3))]
                if math.hypot(u - .5, v - .5) < .25:
                    values = [quantize(c * .5 + b / 255 * .5) for c, b in zip((.2, .6, 1.), values)]
            elif scene == 'C03':
                values = [quantize(half(c * u) / (1 + half(c * u))) for c in (8., 2., .5)]
            elif scene == 'C04':
                values = []
                for factor in (1., .5, .25):
                    scene_value = quantize(u * factor)
                    def bright(column):
                        coord = (max(0, min(SIZE - 1, column)) + .5) / SIZE
                        return quantize(max(quantize(coord * factor) / 255 - .4, 0))
                    blurred = quantize((bright(x - 1) + 2 * bright(x) + bright(x + 1)) / (4 * 255))
                    values.append(quantize(scene_value / 255 + .5 * blurred / 255))
            elif scene == 'C05':
                values = [quantize(base * sample / 255 * .8 + .05)
                          for base, sample in zip((.8, .4, .2), (128, 192, 255))]
            else:
                values = [quantize((quantize(src + quantize(dst) / 255 * .5) / 255) / (1 + quantize(src + quantize(dst) / 255 * .5) / 255))
                          for src, dst in zip((.4, .1, .2), (.25, .5, .75))]
            pixels.extend(values)
    return bytes(pixels)


def write_references(folder):
    folder.mkdir(parents=True, exist_ok=True)
    entries = {}
    for scene, (description, tolerance) in SCENES.items():
        path = folder / (scene + '.ppm')
        visual.write_ppm(path, SIZE, SIZE, reference(scene))
        entries[scene] = {'file': path.name, 'sha256': digest(path), 'description': description,
                          'max_channel_error_u8': tolerance, 'origin': 'independent CPU analytic oracle'}
    manifest = {'schema_version': 1, 'size': [SIZE, SIZE], 'orientation': 'top-to-bottom',
                'color_space': 'RGB8 encoded or explicitly tone-mapped numerical output; not display calibration',
                'images': entries}
    (folder / 'manifest.json').write_text(json.dumps(manifest, indent=2) + '\n')


def validate_references(folder):
    manifest = json.loads((folder / 'manifest.json').read_text())
    if set(manifest['images']) != set(SCENES) or manifest['size'] != [SIZE, SIZE]:
        raise ValueError('Reference inventory/size mismatch')
    for scene, (_, tolerance) in SCENES.items():
        entry = manifest['images'][scene]
        if entry['file'] != scene + '.ppm' or entry['max_channel_error_u8'] != tolerance:
            raise ValueError('Reference path/tolerance mismatch')
        path = folder / entry['file']
        if digest(path) != entry['sha256']:
            raise ValueError('Reference hash mismatch')
        width, height, pixels = visual.read_ppm(path)
        if (width, height) != (SIZE, SIZE) or bytes(pixels) != reference(scene):
            raise ValueError('Reference differs from independent analytic oracle')
    return manifest


def compare_pixels(actual, expected, tolerance):
    if len(actual) != len(expected) or len(actual) != SIZE * SIZE * 3:
        raise ValueError('Pixel size mismatch')
    errors = [abs(a - b) for a, b in zip(actual, expected)]
    return {'max_channel_error_u8': max(errors), 'mae_u8': sum(errors) / len(errors),
            'tolerance_u8': tolerance, 'pass': max(errors) <= tolerance}


def execute(binary, scene, output, mode):
    command = [str(binary), scene, str(output), mode]
    proc = subprocess.run(command, text=True, capture_output=True, timeout=60)
    if proc.returncode:
        raise RuntimeError(f'{scene}/{mode}: exit {proc.returncode}: {proc.stderr}')
    row = json.loads(proc.stdout)
    if (row.get('scene'), row.get('mode'), row.get('status')) != (scene, mode, 'PASS'):
        raise ValueError('Runtime identity/status mismatch')
    if not row.get('renderer') or not row.get('version'):
        raise ValueError('Missing runtime driver identity')
    width, height, pixels = visual.read_ppm(output)
    if (width, height) != (SIZE, SIZE):
        raise ValueError('Capture dimensions mismatch')
    row.update(command=command, stderr=proc.stderr, image_sha256=digest(output))
    return row, pixels


def run(binary, output, golden):
    validate_references(golden)
    output.mkdir(parents=True, exist_ok=True)
    rows, failures = [], []
    material_spec = importlib.util.spec_from_file_location('pipeline_material_validation', HERE / 'material.py')
    material = importlib.util.module_from_spec(material_spec)
    material_spec.loader.exec_module(material)
    material_manifest = json.loads((HERE / 'manifests/pbr-material.json').read_text())
    for scene in SCENARIO_REFERENCE:
        for mode in ('baseline', 'injected'):
            try:
                row, pixels = execute(binary, scene, output / f'{scene}-{mode}.ppm', mode)
                if scene in ('S03', 'S09'):
                    reflection = {'blocks': [{'name': 'Material', 'size': row['block_size'],
                                             'binding': row['block_binding'],
                                             'members': [{'name': name, 'offset': offset,
                                                          'type': {0x1406: 'float', 0x8B52: 'vec4'}.get(kind, 'unknown'),
                                                          'array': count, 'row_major': bool(major)}
                                                         for name, offset, kind, count, major in
                                                         zip(('baseColor', 'roughness', 'metallic'), row['offsets'],
                                                             row['member_types'], row['member_sizes'], row['member_row_major'])]}],
                                  'samplers': [{'name': 'baseColorTex', 'unit': row['sampler_unit'],
                                                'type': row['sampler_type']}]}
                    row['manifest_reflection_errors'] = material.validate(material_manifest, reflection=reflection)
                    if row['manifest_reflection_errors']:
                        failures.append(scene + '/manifest-reflection')
                ref = SCENARIO_REFERENCE[scene]
                expected = reference(ref) if ref else bytes([64, 128, 191] * SIZE * SIZE)
                if scene == 'S09':
                    expected = bytearray(expected)
                    second = [quantize(base * sample / 255 * .8 + .05)
                              for base, sample in zip((.2, .8, .6), (128, 192, 255))]
                    for y in range(SIZE):
                        for x in range(SIZE // 2, SIZE):
                            expected[(y * SIZE + x) * 3:(y * SIZE + x) * 3 + 3] = bytes(second)
                tolerance = SCENES[ref][1] if ref else 1
                row['comparison'] = compare_pixels(pixels, expected, tolerance)
                # These injected faults deliberately render a regression, all others
                # are rejected BEFORE unsafe use and then corrected for rendering.
                expect_difference = mode == 'injected' and scene in ('S04', 'S07', 'S08')
                row['acceptance_pass'] = row['comparison']['pass'] != expect_difference
                if not row['acceptance_pass']:
                    failures.append(scene + '/' + mode)
                rows.append(row)
            except (RuntimeError, ValueError, OSError, subprocess.TimeoutExpired) as exc:
                failures.append(str(exc))
    for scene, (_, tolerance) in SCENES.items():
        for mode in ('baseline', 'injected'):
            try:
                row, pixels = execute(binary, scene, output / f'{scene}-{mode}.ppm', mode)
                row['comparison'] = compare_pixels(pixels, reference(scene), tolerance)
                row['acceptance_pass'] = row['comparison']['pass'] == (mode == 'baseline')
                if not row['acceptance_pass']:
                    failures.append(scene + '/' + mode)
                rows.append(row)
            except (RuntimeError, ValueError, OSError, subprocess.TimeoutExpired) as exc:
                failures.append(str(exc))
    report = {'schema_version': 1, 'status': 'FAIL' if failures else 'PASS',
              'generated_at': datetime.now(timezone.utc).isoformat(),
              'scope': 'Actual EGL/GLES software correctness and host wall-clock measurements; no physical GPU performance claim',
              'physical_gpu_performance': 'NOT_RUN', 'display_calibration': 'NOT_RUN',
              'MSAA_edge_coverage_cross_backend': 'NOT_RUN',
              'binary_sha256': digest(binary), 'source_sha256': digest(ROOT / 'examples/pipeline/pipeline_lab.cpp'),
              'reference_manifest_sha256': digest(golden / 'manifest.json'),
              'results': rows, 'failures': failures}
    (output / 'runtime-report.json').write_text(json.dumps(report, indent=2) + '\n')
    return report


def version_matrix(binary, output):
    """Mesa capability overrides are not a substitute for separate target drivers."""
    output.mkdir(parents=True, exist_ok=True)
    rows = []
    for version in ('3.0', '3.1', '3.2'):
        for scene in ('S01', 'S03', 'S05', 'S06', 'C01', 'C03'):
            command = [str(binary), scene, str(output / f'version-{version}-{scene}.ppm'), 'baseline']
            env = dict(os.environ, MESA_GLES_VERSION_OVERRIDE=version)
            proc = subprocess.run(command, env=env, text=True, capture_output=True, timeout=60)
            blocked = version == '3.0' and scene == 'S05'
            passed = (proc.returncode != 0 and 'BLOCKED_BY_CAPABILITY' in proc.stderr) if blocked else proc.returncode == 0
            if not blocked and passed:
                actual = json.loads(proc.stdout)['version']
                passed = actual.startswith('OpenGL ES ' + version)
            rows.append({'gles_override': version, 'scene': scene, 'pass': passed,
                         'expected_blocked': blocked, 'returncode': proc.returncode,
                         'command': command, 'stdout': proc.stdout, 'stderr': proc.stderr})
    report = {'status': 'PASS' if all(r['pass'] for r in rows) else 'FAIL',
              'scope': 'Mesa GLES version override exercises API fallback, not independent physical 3.0/3.1/3.2 devices',
              'binary_sha256': digest(binary), 'source_sha256': digest(ROOT / 'examples/pipeline/pipeline_lab.cpp'),
              'results': rows}
    (output / 'runtime-version-matrix.json').write_text(json.dumps(report, indent=2) + '\n')
    return report


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--binary', type=Path, default=Path('/tmp/gles-pipeline-lab/pipeline-lab'))
    parser.add_argument('--output', type=Path, default=Path('/tmp/gles-pipeline-runtime'))
    parser.add_argument('--goldens', type=Path, default=HERE / 'goldens')
    parser.add_argument('--write-analytic-references', action='store_true')
    parser.add_argument('--mesa-version-matrix', action='store_true')
    args = parser.parse_args()
    if args.write_analytic_references:
        write_references(args.goldens)
        return 0
    if args.mesa_version_matrix:
        report = version_matrix(args.binary, args.output)
        print(report['status'])
        return int(report['status'] != 'PASS')
    report = run(args.binary, args.output, args.goldens)
    print(json.dumps({'status': report['status'], 'captures': len(report['results']), 'failures': report['failures']}))
    return int(report['status'] != 'PASS')


if __name__ == '__main__':
    raise SystemExit(main())
