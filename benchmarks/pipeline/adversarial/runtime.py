#!/usr/bin/env python3
"""Replay adversarial contracts against captured, actually linked GL reflection."""
import argparse
import copy
import hashlib
import importlib.util
import json
from pathlib import Path
from check import abi_cases,abi_check,base_material,reflection_for

HERE=Path(__file__).resolve().parent
spec=importlib.util.spec_from_file_location('v107_runtime',HERE.parent/'runtime.py')
runtime=importlib.util.module_from_spec(spec);spec.loader.exec_module(runtime)

def apply_delta(actual,before,after):
    """Keep captured fields unless the authored case explicitly mutates them."""
    if before==after:return copy.deepcopy(actual)
    if isinstance(before,dict) and isinstance(after,dict):
        result=copy.deepcopy(actual)
        for key in set(before)-set(after):result.pop(key,None)
        for key,value in after.items():
            if key not in before:result[key]=copy.deepcopy(value)
            elif before[key]!=value:result[key]=apply_delta(result.get(key),before[key],value)
        return result
    if isinstance(before,list) and isinstance(after,list) and len(before)==len(after):
        return [apply_delta(actual[i],b,a) for i,(b,a) in enumerate(zip(before,after))]
    return copy.deepcopy(after)

def run(binary,output):
    output.mkdir(parents=True,exist_ok=True)
    captures=[];image_checks=[]
    for mode in ('baseline','injected'):
        capture,pixels=runtime.execute(binary,'S03',output/('material-'+mode+'.ppm'),mode)
        pixel_check=runtime.compare_pixels(pixels,runtime.reference('C05'),2)
        if not pixel_check['pass']:raise ValueError('Actual linked material image failed independent oracle')
        if len(capture.get('checked_faults',[]))!=2:raise ValueError('Missing runtime offset/sampler injection assertions')
        image_checks.append(pixel_check)
        captures.append(capture)
    base=captures[0]
    reflection={'blocks':[dict(name='Material',size=base['block_size'],binding=base['block_binding'],members=[
        dict(name=n,offset=o,type={0x1406:'float',0x8B52:'vec4'}.get(t,'unknown'),array=a,row_major=bool(r))
        for n,o,t,a,r in zip(('baseColor','roughness','metallic'),base['offsets'],base['member_types'],base['member_sizes'],base['member_row_major'])])],
        'samplers':[dict(name='baseColorTex',unit=base['sampler_unit'],type=base['sampler_type'])]}
    baseline_errors=abi_check(base_material(),reflection=reflection)
    if baseline_errors:raise ValueError('Actual linked baseline reflection failed: '+str(baseline_errors))
    authored_baseline=reflection_for(base_material())
    rows=[]
    for c in abi_cases():
        # Mutation overlays are applied to an actual captured reflection baseline.
        # Negative metadata isn't described as a separate driver execution.
        r=apply_delta(reflection,authored_baseline,c['reflection'])
        errors=abi_check(c['manifest'],reflection=r,capability=c['capability'],active_uniforms=c['active_uniforms'],required_uniforms=c['required_uniforms'])
        ok=not errors if c['expected_rule'] is None else any(c['expected_rule'] in e for e in errors)
        rows.append(dict(id=c['id'],status='PASS' if ok else 'FAIL',errors=errors,expected_rule=c['expected_rule'],evidence='authored negative metadata replay against host-captured linked-program contract'))
    result=dict(schema_version=1,status='PASS' if all(x['status']=='PASS' for x in rows) else 'FAIL',
        actual_driver_invocations=len(captures),driver_captures=captures,image_checks=image_checks,captured_reflection=reflection,adversarial_replays=rows,
        driver_injected_path='Actual wrong sampler unit and mismatching offset contract are detected, repaired before safe draw',
        limitations='Not24 independent driver faults. Required-extension/version controls are declared capability contracts.',
        binary_sha256=hashlib.sha256(binary.read_bytes()).hexdigest())
    (output/'report.json').write_text(json.dumps(result,indent=2)+'\n')
    return result

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--binary',type=Path,default=Path('/tmp/gles-pipeline-lab/pipeline-lab'));p.add_argument('--output',type=Path,required=True);a=p.parse_args();r=run(a.binary,a.output);print(r['status']);raise SystemExit(r['status']!='PASS')
