#!/usr/bin/env python3
"""Actual GLES captures and frozen-reference comparisons. No fake device timing."""
import argparse
from datetime import datetime, timezone
import hashlib
import json
import math
from pathlib import Path
import struct
import subprocess
import sys
from compare import compare, temporal, read_ppm
ROOT=Path(__file__).resolve().parents[2]
HERE=Path(__file__).resolve().parent
GOLDEN=HERE/'golden'
SCENES={f'P{i:02}':name for i,name in enumerate(('long accumulation','normal specular','water highlight','smooth gradient','HDR tone mapping','transparent layers','linear to sRGB','RGBA16F vs RGBA8'),1)}
TIMES=[10000.,10000.125,10000.25]
def digest(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def oracle(fmt):
    quant=lambda x:struct.unpack(fmt,struct.pack(fmt,x))[0]
    x=16.
    for _ in range(1024):x=quant(x+quant(.001))
    return x

def execute(binary,scene,path,scale,time,mode):
    command=[str(binary),scene,str(path),'96',str(scale),str(time),mode]
    proc=subprocess.run(command,capture_output=True,text=True,timeout=60)
    if proc.returncode:raise RuntimeError(f'{command}: exit {proc.returncode}: {proc.stderr}')
    row=json.loads(proc.stdout)
    if row['scene']!=scene or row['mode']!=mode or row['time_seconds']!=time or not math.isclose(row['scale'],scale,abs_tol=1e-6):raise ValueError('Capture identity mismatch')
    row.update(command=command,stderr=proc.stderr,image_sha256=digest(path))
    return row

def validate_manifest(manifest, folder=GOLDEN):
    expected={f'{scene}-{frame}.ppm' for scene in SCENES for frame in range(len(TIMES))}
    if set(manifest.get('images',{}))!=expected:raise ValueError('Golden inventory must contain exactly24 scene/time images')
    if manifest.get('times_seconds')!=TIMES or manifest.get('seed')!=1337:raise ValueError('Golden time/seed contract')
    if manifest.get('compression')!='none' or manifest.get('orientation')!='top-to-bottom':raise ValueError('Golden storage contract')
    if manifest.get('color_space')!='encoded RGB8; HDR scene tone mapped to SDR; no WCG/display certification':raise ValueError('Golden color-space contract')
    if manifest.get('resource_hashes',{}).get('thresholds')!=digest(HERE/'thresholds.json'):raise ValueError('Golden threshold configuration changed')
    for key,value in manifest['images'].items():
        scene,frame=key.removesuffix('.ppm').split('-');capture=value.get('capture',{})
        if (capture.get('scene'),capture.get('mode'),capture.get('scale'),capture.get('time_seconds'),capture.get('seed'),capture.get('output_size'),capture.get('internal_size'))!=(scene,'baseline',1,TIMES[int(frame)],1337,96,96):raise ValueError('Golden capture identity '+key)
        if not capture.get('renderer') or not capture.get('version'):raise ValueError('Golden backend/driver identity '+key)
        if digest(folder/key)!=value.get('sha256') or capture.get('image_sha256')!=value.get('sha256'):raise ValueError('Golden hash mismatch '+key)
        width,height,_=read_ppm(folder/key)
        if (width,height)!=(96,96):raise ValueError('Golden actual dimensions '+key)

def main():
    p=argparse.ArgumentParser();p.add_argument('--binary',type=Path,default=Path('/tmp/gles-precision-lab/precision-lab'));p.add_argument('--output',type=Path,default=Path('/tmp/gles-visual-quality'));p.add_argument('--accept-goldens',action='store_true');p.add_argument('--scale',type=float,action='append',help='Policy render scale, repeatable; default .85,.7')
    args=p.parse_args();args.output.mkdir(parents=True,exist_ok=True)
    scales=args.scale if args.scale else [.85,.7]
    if any(not .25<=s<=1 for s in scales):p.error('Scale outside [.25,1]')
    config=json.loads((HERE/'thresholds.json').read_text());manifest={'images':{}}
    if not args.accept_goldens:
        manifest=json.loads((GOLDEN/'manifest.json').read_text())
        validate_manifest(manifest)
    results=[];failures=[];pareto=[]
    for scene in SCENES:
        refs=[];baseline=[]
        for frame,time in enumerate(TIMES):
            name=f'{scene}-{frame}.ppm';path=args.output/name;row=execute(args.binary,scene,path,1,time,'baseline');baseline.append(path);ref=GOLDEN/name;refs.append(ref)
            if args.accept_goldens:
                ref.write_bytes(path.read_bytes());manifest['images'][name]={'sha256':digest(ref),'capture':row}
            else:
                row['comparison']=compare(ref,path,config,scene)
                if not row['comparison']['pass']:failures.append(name+' baseline regression')
            results.append(row)
        if args.accept_goldens:continue
        for mode,scale in [('degraded',1),('mediump',1)]+[('baseline',s) for s in scales]:
            frames=[];quality=True
            for frame,time in enumerate(TIMES):
                name=f'{scene}-{mode}-{scale}-{frame}';path=args.output/(name+'.ppm');frames.append(path)
                row=execute(args.binary,scene,path,scale,time,mode)
                row['comparison']=compare(refs[frame],path,config,scene,args.output/(name+'-heat.ppm'))
                quality &= row['comparison']['pass'];results.append(row)
            timing=temporal(refs,frames,config['temporal_delta_mae_max']);quality &= timing['pass']
            if mode=='degraded' and quality:failures.append(scene+' injected regression not detected')
            # Flicker control alternates reference and known degraded frame, distinct from constant bias.
            if mode=='degraded':
                flicker=temporal(refs,[refs[0],frames[1],refs[2]],config['temporal_delta_mae_max'])
                if flicker['pass']:failures.append(scene+' flicker injection not detected')
            else:flicker=None
            pareto.append({'scene':scene,'mode':mode,'scale':scale,'visual_safe':quality,'temporal':timing,'injected_flicker':flicker,'p95_frame_ms':None,'power_mw':None,'memory_budget_bytes':None,'thermal_stability':'NOT_MEASURED','pareto_status':'INSUFFICIENT_PERFORMANCE_EVIDENCE','recommendation':'REJECT_VISUAL_REGRESSION' if not quality else 'NEEDS_DEVICE_PERFORMANCE_AND_ART_REVIEW'})
    if args.accept_goldens:
        manifest.update(created_at=datetime.now(timezone.utc).isoformat(),scope='Mesa software reference, not universal driver goldens',scene_source_sha256=digest(ROOT/'examples/precision/precision_lab.cpp'),shared_renderer_sha256=digest(ROOT/'examples/scenes/scene_lab.cpp'),seed=1337,times_seconds=TIMES,color_space='encoded RGB8; HDR scene tone mapped to SDR; no WCG/display certification',compression='none',orientation='top-to-bottom',resource_hashes={'thresholds':digest(HERE/'thresholds.json')})
        (GOLDEN/'manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')
    numeric=results[0];expected32=oracle('f');expected16=oracle('e')
    numeric_ok=abs(numeric['numeric_highp']-expected32)<=.002 and numeric['numeric_binary16']==expected16
    if not numeric_ok:failures.append('GPU numerical probe differs from CPU oracle')
    report={'status':'BASELINES_CREATED_NOT_VALIDATED' if args.accept_goldens else ('FAIL' if failures else 'PASS'),'layer':'L1_ACTUAL_SOFTWARE_GLES','physical_gpu':'NOT_RUN_DEVICE','binary_sha256':digest(args.binary),'runner_sha256':digest(__file__),'source_sha256':digest(ROOT/'examples/precision/precision_lab.cpp'),'shared_renderer_sha256':digest(ROOT/'examples/scenes/scene_lab.cpp'),'comparator_sha256':digest(HERE/'compare.py'),'thresholds_sha256':digest(HERE/'thresholds.json'),'numeric':{'cpu_binary32':expected32,'cpu_binary16':expected16,'gpu_highp':numeric['numeric_highp'],'gpu_binary16':numeric['numeric_binary16'],'gpu_mediump':numeric['numeric_mediump'],'pass':numeric_ok,'note':'mediump is measured separately, not assumed binary16'},'golden_count':len(manifest['images']),'capture_count':len(results),'failures':failures,'captures':results,'quality_and_pareto':pareto,'policy_level_visual_approval':{scene:{str(level):next((r['visual_safe'] for r in pareto if r['scene']==scene and r['mode']=='baseline' and math.isclose(r['scale'],scale)),None) for level,scale in ((1,.85),(2,.7))} for scene in SCENES}}
    (args.output/'report.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps({k:report[k] for k in ('status','capture_count','golden_count','failures','numeric')}));return bool(failures)
if __name__=='__main__':sys.exit(main())
