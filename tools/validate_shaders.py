#!/usr/bin/env python3
"""Compile/link positive ESSL programs and require compiler rejection of negatives."""
import argparse
import hashlib
import json
import shutil
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

def expected_result(returncode, expected_accept, output):
    if expected_accept:
        return returncode == 0
    # glslang's compile/link failure codes, not crashes or missing-input/tool failures.
    return returncode in (2, 3) and 'ERROR:' in output

def main():
    p = argparse.ArgumentParser()
    p.add_argument('--compiler', default='glslangValidator')
    p.add_argument('--output', type=Path, default=Path('reports/shaders.json'))
    args = p.parse_args()
    compiler = shutil.which(args.compiler)
    if not compiler:
        result = {'status':'BLOCKED_BY_TOOLCHAIN','compiler':args.compiler,'cases':[]}
        code = 2
    else:
        cases = []
        directory = ROOT / 'examples/validation/shaders'
        specs = []
        for version in ('300', '310', '320'):
            specs.extend([(version+'-link',[version+'.vert',version+'.frag'],True),
                          (version+'-negative',[version+'-invalid.frag'],False)])
        specs.extend((name,[name],'-invalid' not in name) for name in (
            '300-binding-invalid.frag','310-binding.frag',
            '300-compute-invalid.comp','310-compute.comp',
            '300-ssbo-invalid.frag','310-ssbo.frag',
            '310-geometry-invalid.geom','320-geometry.geom'))
        specs.extend([
            ('varying-precision-difference-legal',['300-precision.vert','300-precision.frag'],True),
            ('varying-type-mismatch-illegal',['300-precision.vert','300-interface-type-mismatch.frag'],False)])
        for name, names, expected in specs:
            files = [directory / name for name in names]
            command = [compiler] + (['-l'] if len(files)>1 else []) + list(map(str,files))
            process = subprocess.run(command, capture_output=True, text=True, timeout=60)
            passed = expected_result(process.returncode, expected, process.stdout + process.stderr)
            cases.append({'case':name,'expected':'accept' if expected else 'reject','status':'PASS' if passed else 'FAIL','exit_code':process.returncode,'stdout':process.stdout,'stderr':process.stderr,'sha256':{str(f.relative_to(ROOT)):hashlib.sha256(f.read_bytes()).hexdigest() for f in files}})
        code = int(any(c['status'] != 'PASS' for c in cases))
        result = {'status':'PASS' if code==0 else 'FAIL','scope':'glslang standalone compile/link; not driver or hardware validation','compiler_version':subprocess.check_output([compiler,'--version'],text=True),'cases':cases}
    args.output.parent.mkdir(parents=True,exist_ok=True)
    args.output.write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps(result,indent=2))
    return code

if __name__ == '__main__':
    raise SystemExit(main())
