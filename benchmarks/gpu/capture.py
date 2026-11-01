#!/usr/bin/env python3
"""Collect/validate target-produced GPU evidence. Validation is not proof of truthful hardware identity."""
import argparse
import hashlib
import json
import math
from pathlib import Path
import statistics
import subprocess
import sys

ROOT = Path(__file__).parent
DEVICE_FIELDS = ('device_model','soc_gpu','os_build','driver','api_backend','resolution','refresh_rate','thermal_state','test_build_sha')

def finite(value):
    return isinstance(value,(int,float)) and not isinstance(value,bool) and math.isfinite(value) and value >= 0

def validate(data, base):
    errors=[]
    if not isinstance(data,dict): return ['capture must be an object']
    if data.get('status')=='BLOCKED_BY_HARDWARE':
        if data.get('conclusion') not in (None,'UNMEASURED'):
            errors.append('blocked record must not claim a conclusion')
        return errors
    if data.get('status')!='MEASURED': errors.append('status must be MEASURED or BLOCKED_BY_HARDWARE')
    if data.get('hardware_kind')!='physical': errors.append('mobile performance acceptance requires physical hardware')
    if data.get('evidence_origin')!='target_device': errors.append('evidence_origin must be target_device; synthetic fixtures are not measurements')
    for field in DEVICE_FIELDS:
        if not data.get(field): errors.append('missing '+field)
    if data.get('scenario_id') not in {x['id'] for x in json.loads((ROOT/'scenarios.json').read_text())['scenarios']}:
        errors.append('unknown scenario_id')
    if not isinstance(data.get('correctness',{}),dict): return ['correctness must be an object']
    if data.get('correctness',{}).get('status')!='PASS': errors.append('correctness must pass before a performance conclusion')
    if not data.get('correctness',{}).get('method'): errors.append('missing correctness method')
    if not data.get('fallback'): errors.append('missing fallback')
    if not data.get('negative_result'): errors.append('record adverse observations or explicitly none observed')
    sampling=data.get('sampling',{})
    if not isinstance(sampling,dict): return ['sampling must be an object']
    if not isinstance(sampling.get('independent_runs'),int) or sampling['independent_runs']<3:
        errors.append('at least 3 independent runs required')
    if not sampling.get('warmup_method') or not sampling.get('order'): errors.append('missing warmup_method/order')
    for arm in ('baseline','variant'):
        row=data.get(arm,{})
        if not isinstance(row,dict):
            errors.append(arm+' must be an object'); continue
        for metric in ('frame_time_ms','gpu_time_ms','cpu_time_ms'):
            values=row.get(metric,[])
            if not isinstance(values,list) or len(values)<3 or not all(finite(v) for v in values): errors.append(f'{arm}.{metric}: need >=3 finite nonnegative samples')
        counters=row.get('counters')
        if not isinstance(counters,list): errors.append(arm+'.counters must be a list (empty permitted with reason)')
        elif not counters and not row.get('counter_unavailable_reason'): errors.append(arm+': explain unavailable counters; never invent bandwidth')
        else:
            for counter in counters or []:
                if not isinstance(counter,dict):
                    errors.append(arm+': counter must be an object'); continue
                if not all(counter.get(x) for x in ('name','unit','definition_source')) or not finite(counter.get('value')):
                    errors.append(arm+': invalid counter definition/value')
        uri=row.get('raw_trace_path'); expected=row.get('raw_trace_sha256')
        if not isinstance(uri,str) or not isinstance(expected,str) or not uri or not expected:
            errors.append(arm+': missing raw trace path/hash'); continue
        path=(base/uri).resolve()
        # Keep untrusted capture files from reading arbitrary local files.
        if not path.is_relative_to(base.resolve()):
            errors.append(arm+': trace must remain inside capture directory'); continue
        if not path.is_file(): errors.append(arm+': raw trace absent')
        elif hashlib.sha256(path.read_bytes()).hexdigest()!=expected: errors.append(arm+': raw trace hash mismatch')
    return errors

def summarize(data):
    if data.get('status')=='BLOCKED_BY_HARDWARE': return {'status':'BLOCKED_BY_HARDWARE','conclusion':'UNMEASURED'}
    result={'status':'EVIDENCE_STRUCTURALLY_VALID','conclusion':'REVIEW_REQUIRED',
            'warning':'No automated claim of hardware authenticity, causality or universal speedup.', 'statistics':{}}
    for arm in ('baseline','variant'):
        result['statistics'][arm]={}
        for metric in ('frame_time_ms','gpu_time_ms','cpu_time_ms'):
            values=sorted(data[arm][metric]); n=len(values)
            result['statistics'][arm][metric]={'n':n,'mean':statistics.mean(values),'median':statistics.median(values),
                'p95':values[max(0,math.ceil(.95*n)-1)],'min':values[0],'max':values[-1],'stdev':statistics.stdev(values)}
    before=result['statistics']['baseline']['gpu_time_ms']['mean']; after=result['statistics']['variant']['gpu_time_ms']['mean']
    result['gpu_time_change_percent']=None if before==0 else (after-before)/before*100
    return result

def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--input',type=Path)
    p.add_argument('--scenario',choices=[r['id'] for r in json.loads((ROOT/'scenarios.json').read_text())['scenarios']],default='GPU01')
    p.add_argument('--adapter',help='JSON argv array; target runner receives scenario JSON on stdin and must return one capture JSON on stdout')
    p.add_argument('--output',type=Path,required=True)
    p.add_argument('--timeout',type=int,default=300)
    args=p.parse_args()
    if args.input and args.adapter: p.error('choose input or adapter, not both')
    base=args.input.parent if args.input else Path.cwd()
    if args.input: data=json.loads(args.input.read_text())
    elif args.adapter:
        command=json.loads(args.adapter)
        if not isinstance(command,list) or not command or not all(isinstance(x,str) for x in command): p.error('adapter must be nonempty JSON argv array')
        scene=next(r for r in json.loads((ROOT/'scenarios.json').read_text())['scenarios'] if r['id']==args.scenario)
        try:
            run=subprocess.run(command,input=json.dumps(scene),capture_output=True,text=True,timeout=args.timeout,check=True)
            data=json.loads(run.stdout)
        except (subprocess.SubprocessError,json.JSONDecodeError,OSError) as exc:
            args.output.parent.mkdir(parents=True,exist_ok=True)
            args.output.write_text(json.dumps({'status':'ADAPTER_FAILED','error':str(exc)},indent=2)+'\n')
            return 2
    else:
        data={'status':'BLOCKED_BY_HARDWARE','scenario_id':args.scenario,'conclusion':'UNMEASURED',
              'reason':'No target adapter or target capture supplied.'}
    errors=validate(data,base)
    report={'capture':data,'validation_errors':errors,'summary':summarize(data) if not errors else {'status':'INVALID_EVIDENCE','conclusion':'REJECTED'}}
    args.output.parent.mkdir(parents=True,exist_ok=True)
    args.output.write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps({'output':str(args.output),'status':report['summary']['status'],'errors':len(errors)}))
    return 1 if errors else (3 if data['status']=='BLOCKED_BY_HARDWARE' else 0)

if __name__=='__main__': sys.exit(main())
