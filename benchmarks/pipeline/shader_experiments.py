#!/usr/bin/env python3
"""Compile/link complete GLSL A/B experiments; never claims GPU execution/timing."""
import argparse
import hashlib
import json
from pathlib import Path
import shutil
import subprocess

HERE = Path(__file__).resolve().parent

def sha256(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()

def source_path(relative):
    if not isinstance(relative, str): raise ValueError('source path must be string')
    path = (HERE / relative).resolve()
    if not path.is_relative_to((HERE / 'experiments/shader-risks').resolve()):
        raise ValueError('source path outside shader experiment directory')
    if not path.is_file(): raise ValueError('missing shader source: ' + relative)
    return path

def run(compiler, output):
    rows = json.loads((HERE / 'cases/shader-risk-experiments.json').read_text())
    executable = shutil.which(str(compiler))
    report = dict(schema_version=1, scope='Static GLSL ES compile/link only',
                  device_measurement_status='NOT_RUN', status='FAIL', compiler=None, experiments=[], failures=[])
    try:
        if executable is None: raise ValueError('compiler not found: ' + str(compiler))
        executable = Path(executable).resolve()
        version = subprocess.run([str(executable), '--version'], capture_output=True, text=True, timeout=15)
        if version.returncode != 0: raise ValueError('compiler --version failed: ' + version.stderr)
        report['compiler'] = dict(path=str(executable), sha256=sha256(executable), version=version.stdout.strip())
        for row in rows:
            vertex = source_path(row['sources']['vertex'])
            result = dict(id=row['id'], input_equivalence=row['input_equivalence'],
                          device_measurement_status='NOT_RUN', arms={})
            for arm in ('a','b'):
                fragment = source_path(row['sources'][arm])
                command = [str(executable), '-l', str(vertex), str(fragment)]
                item = dict(expected=row['expected_compile'][arm], command=command,
                            vertex_sha256=sha256(vertex), fragment_sha256=sha256(fragment),
                            compiler_sha256=report['compiler']['sha256'], status='FAIL')
                try:
                    proc = subprocess.run(command, capture_output=True, text=True, timeout=30)
                    item.update(returncode=proc.returncode, stdout=proc.stdout, stderr=proc.stderr)
                    if item['expected'] == 'ACCEPT':
                        item['status'] = 'PASS' if proc.returncode == 0 else 'FAIL'
                    elif item['expected'] == 'REJECT':
                        # Reject must be the intended sampler legality diagnostic, not a crash,
                        # missing executable, link interface failure or unrelated syntax error.
                        diagnostics = proc.stdout + proc.stderr
                        intended = 'variable indexing sampler array' in diagnostics and 'not supported' in diagnostics
                        item['status'] = 'PASS' if proc.returncode == 2 and intended else 'FAIL'
                    else: raise ValueError('unknown expected compile result')
                except (OSError, subprocess.TimeoutExpired) as exc:
                    item['error'] = str(exc)
                result['arms'][arm] = item
                if item['status'] != 'PASS': report['failures'].append(row['id'] + '-' + arm)
            report['experiments'].append(result)
        report['status'] = 'PASS' if not report['failures'] else 'FAIL'
    except (OSError, ValueError, subprocess.TimeoutExpired) as exc:
        report['failures'].append(str(exc))
    output = Path(output); output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, indent=2) + '\n')
    return report

if __name__ == '__main__':
    parser=argparse.ArgumentParser()
    parser.add_argument('--compiler', default='glslangValidator')
    parser.add_argument('--output', type=Path, default=HERE/'reports/shader-experiments.json')
    args=parser.parse_args(); report=run(args.compiler,args.output)
    print(json.dumps(dict(status=report['status'],pairs=len(report['experiments']),failures=report['failures'])))
    raise SystemExit(report['status'] != 'PASS')
