#!/usr/bin/env python3
"""Execute actual scene binary; compare frozen goldens, never silently regenerate."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import statistics
import subprocess
import time

ROOT = Path(__file__).resolve().parents[2]
GOLDEN = Path(__file__).parent / 'golden'
SCENES = [f'S{i:02}' for i in range(1,9)]


class CapabilityBlocked(RuntimeError):
    pass

def read_ppm(path):
    with Path(path).open('rb') as f:
        if f.readline() != b'P6\n': raise ValueError('Expected binary P6')
        dimensions = f.readline().split()
        if len(dimensions) != 2: raise ValueError('Invalid dimensions')
        w,h = map(int, dimensions)
        if not (1 <= w <= 2048 and 1 <= h <= 2048): raise ValueError('Invalid dimensions')
        if f.readline() != b'255\n': raise ValueError('Expected 8-bit RGB')
        data = f.read()
        if len(data) != w*h*3: raise ValueError('Pixel payload length differs')
        return w,h,data


def compare(reference, actual):
    w,h,a = read_ppm(reference)
    x,y,b = read_ppm(actual)
    if (w,h)!=(x,y): raise ValueError('Image dimensions differ')
    diffs=[abs(x-y) for x,y in zip(a,b)]
    mae=sum(diffs)/len(diffs)
    fraction=sum(x>8 for x in diffs)/len(diffs)
    return {'mae_8bit':mae,'max_error_8bit':max(diffs),'fraction_channels_over_8':fraction,
            'pass':mae<=1.5 and fraction<=.02 and max(diffs)<=48}


def digest(path): return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def execute(binary, scene, path, size, count, variant):
    command=[str(binary),scene,str(path),str(size),str(count),variant]
    result=subprocess.run(command,capture_output=True,text=True,timeout=120)
    if result.returncode == 3: raise CapabilityBlocked(result.stderr.strip())
    if result.returncode: raise RuntimeError(f'{scene}/{variant} exit {result.returncode}: {result.stderr}')
    report=json.loads(result.stdout)
    if report['scene']!=scene or report['variant']!=variant: raise ValueError('Mismatched scene response')
    report.update(command=command,image_sha256=digest(path),stderr=result.stderr)
    return report


def main():
    p=argparse.ArgumentParser()
    p.add_argument('--binary',type=Path,default=Path('/tmp/gles-scene-lab/scene-lab'))
    p.add_argument('--output',type=Path,default=ROOT/'reports/scenes')
    p.add_argument('--accept-goldens',action='store_true',help='Explicit initial/reviewed baseline replacement; not a test pass')
    p.add_argument('--sweep',action='store_true',help='Run additional resolution/count correctness cases')
    a=p.parse_args();a.output.mkdir(parents=True,exist_ok=True)
    results=[];failures=[]
    if not a.accept_goldens:
        manifest=json.loads((GOLDEN/'manifest.json').read_text())
        for scene in SCENES:
            if digest(GOLDEN/(scene+'.ppm'))!=manifest['images'][scene]['sha256']:
                raise ValueError(f'Golden hash mismatch: {scene}')
    for scene in SCENES:
        baseline=a.output/(scene+'-baseline.ppm')
        run=execute(a.binary,scene,baseline,96,64,'baseline')
        if a.accept_goldens:
            (GOLDEN/(scene+'.ppm')).write_bytes(baseline.read_bytes())
            run['golden']='CREATED_NOT_VALIDATED'
        else:
            run['golden']=compare(GOLDEN/(scene+'.ppm'),baseline)
            if not run['golden']['pass']: failures.append(scene+' baseline image regression')
        results.append(run)
        for variant in ('control','degraded'):
            path=a.output/(scene+'-'+variant+'.ppm')
            row=execute(a.binary,scene,path,96,64,variant)
            row['baseline_difference']=compare(baseline,path)
            # S04 intentionally tests a failed blur-elimination optimization.
            expected_match=variant=='control' and scene!='S04'
            row['expected_visual_match']=expected_match
            row['expectation_met']=row['baseline_difference']['pass']==expected_match
            if not row['expectation_met']: failures.append(scene+' '+variant+' unexpected visual outcome')
            results.append(row)
        if a.sweep:
            for size,count in ((64,32),(128,128)):
                path=a.output/f'{scene}-{size}-{count}.ppm'
                row=execute(a.binary,scene,path,size,count,'baseline')
                row['validation']='executed/readback only; no golden at this size'
                results.append(row)
    report={'status':'BASELINES_CREATED' if a.accept_goldens else ('FAIL' if failures else 'PASS'),
            'scope':'actual software-driver correctness, not physical GPU performance',
            'seed':1337,'color_contract':'RGB8 top-to-bottom; explicit shader color/gamma, not display HDR/WCG certification',
            'tolerance':{'mae_max':1.5,'fraction_channels_over_8_max':.02,'max_error_max':48},
            'source_sha256':digest(ROOT/'examples/scenes/scene_lab.cpp'),'runner_sha256':digest(__file__),
            'binary_sha256':digest(a.binary),'failures':failures,'runs':results,
            'hardware_performance':'BLOCKED_BY_HARDWARE','gpu_timing':'NOT_COLLECTED','bandwidth_counters':'NOT_COLLECTED'}
    if a.accept_goldens:
        manifest={'origin':'actual Mesa software EGL rendering; explicitly generated, not an independent artistic oracle',
                  'source_sha256':report['source_sha256'],'color_contract':report['color_contract'],'tolerance':report['tolerance'],
                  'images':{r['scene']:{'sha256':r['image_sha256'],'renderer':r['renderer'],'version':r['version'],'size':96,'instances':64,'seed':1337} for r in results if r['variant']=='baseline' and r['size']==96}}
        (GOLDEN/'manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')
    (a.output/'report.json').write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps({'status':report['status'],'runs':len(results),'failures':failures,'report':str(a.output/'report.json')}))
    return bool(failures)

if __name__=='__main__':
    try:
        raise SystemExit(main())
    except CapabilityBlocked as error:
        print(json.dumps({'status':'BLOCKED_BY_CAPABILITY','reason':str(error),'hardware_performance':'NOT_MEASURED'}))
        raise SystemExit(3)
