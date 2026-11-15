#!/usr/bin/env python3
"""Finite texture-resolution-loss oracle reused for PostFX advice, not arbitrary PostFX proof."""
import argparse
import hashlib
import importlib.util
import json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
spec=importlib.util.spec_from_file_location('postfx_texture_controls',ROOT/'benchmarks/texture_access/run.py')
texture=importlib.util.module_from_spec(spec);spec.loader.exec_module(texture)
EXPERIMENT_ID='postfx-resolution-loss-v1'

def run(config):
    host=texture.ExperimentHost(config);rows=[]
    try:
        for case in texture.cases():
            if case['id'] not in ('coordinate-hoist','resolution-loss-negative'):continue
            draws=[host.draw(case['id'],case[arm],texture=case['texture']) for arm in ('a','b')]
            # Independent nearest 2x2 texture -> 4x4 framebuffer expected image.
            golden=[value for y in range(4) for x in range(4) for value in case['texture']['pixels'][((y//2)*2+x//2)*4:((y//2)*2+x//2)*4+4]]
            ok=all(d.get('status')=='EXECUTED' and d.get('compile') and d.get('link') and not d.get('harness_gl_error') for d in draws)
            error=max(abs(a-b) for a,b in zip(draws[0].get('pixels',[]),golden)) if len(draws[0].get('pixels',[]))==64 else None
            observed=texture.quality(*draws)
            rows.append({'id':case['id'],'expected':case['expected'],'observed':observed,'baseline_cpu_error':error,'pass':ok and error is not None and error<=1 and observed==case['expected'],'draws':draws,'source_sha256':{arm:hashlib.sha256(case[arm].encode()).hexdigest() for arm in ('a','b')}})
    finally:host.close()
    return {'experiment_id':EXPERIMENT_ID,'status':'HOST_PASS' if len(rows)==2 and all(r['pass'] for r in rows) else 'FAIL','cases':rows,'scope':'2x2 RGBA8 nearest texture to 4x4 framebuffer; resolution-collapse negative control only','postfx_semantic_proof':'NOT_PROVEN','performance':'NOT_MEASURED','dynamic_camera':'NOT_RUN'}

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--config',type=Path,required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args()
    report=run(json.loads(a.config.read_text()));a.output.write_text(json.dumps(report,indent=2)+'\n');print(report['status']);raise SystemExit(report['status']!='HOST_PASS')
