#!/usr/bin/env python3
"""Shared host/Android/Windows/GBM capture contract, with explicit backend provenance."""
import argparse
import hashlib
import json
import math
from pathlib import Path
import subprocess

FIELDS={'build','platform','os','os_build','api_level','device','backend','backend_evidence','hardware_kind','egl_vendor','egl_version','egl_extensions','gl_vendor','gl_renderer','gl_version','glsl_version','gl_extensions','precision','limits','formats','function_entries','runtime_import_probes','context_generation','surface_generation'}
BACKENDS={'native','angle_vulkan','angle_d3d','software','unknown'}
def digest(value):return hashlib.sha256(json.dumps(value,sort_keys=True,separators=(',',':')).encode()).hexdigest()
def validate(record,requested):
    if record.get('status')=='BLOCKED_BY_HARDWARE':return record
    if record.get('status')!='CAPTURED' or not isinstance(record.get('snapshot'),dict):raise ValueError('Malformed adapter capture')
    s=record['snapshot']
    if FIELDS-set(s):raise ValueError('Missing snapshot fields: '+','.join(sorted(FIELDS-set(s))))
    if s['backend'] not in BACKENDS or s['backend']!=requested['backend'] or s['platform']!=requested['platform']:raise ValueError('Backend/platform mismatch; never silently label fallback as requested backend')
    if s['backend_evidence'].get('kind') not in ('controlled_creation','implementation_query','unknown'):raise ValueError('Renderer substring is not backend proof')
    if s['backend']!='unknown' and s['backend_evidence']['kind']=='unknown':raise ValueError('Backend claim requires provenance')
    if s['hardware_kind'] not in ('physical','software','unknown'):raise ValueError('Unknown hardware kind')
    if s['backend']=='software' and s['hardware_kind']!='software':raise ValueError('Software backend cannot be a physical measurement')
    for key in ('egl_extensions','gl_extensions'):
        if not isinstance(s[key],list) or any(not isinstance(x,str) or not x for x in s[key]):raise ValueError('Exact extension token list required')
    for key in ('precision','limits','formats','function_entries','runtime_import_probes'):
        if not isinstance(s[key],dict):raise ValueError('Capability maps required')
    for key,value in s['limits'].items():
        if value is not None and (type(value) not in (int,float) or not math.isfinite(value) or value<0):raise ValueError('Invalid numeric limit')
    for value in s['formats'].values():
        if value is not None and type(value) is not bool:raise ValueError('Runtime format probes are true/false/unknown')
    for value in s['function_entries'].values():
        if value is not None and type(value) is not bool:raise ValueError('Entry point availability is boolean/unknown')
    events=record.get('correctness_events',[])
    if not events or any(e.get('status')!='PASS' or not e.get('case') for e in events):raise ValueError('Correctness failures/empty event list cannot be PASS')
    # Operator-supplied identity is not cryptographically authenticated device telemetry.
    record['fingerprint']=digest({k:v for k,v in s.items() if k not in ('context_generation','surface_generation')})
    record['acceptance']='SOFTWARE_CORRECTNESS_ONLY' if s['hardware_kind']=='software' else 'REVIEW_REQUIRED'
    record['performance_claim']='NOT_MEASURED'
    return record

def run(args):
    args.output.mkdir(parents=True,exist_ok=False)
    request={'platform':args.platform,'backend':args.backend,'schema_version':1}
    if not args.adapter:
        report={'status':'BLOCKED_BY_HARDWARE','request':request,'captures':[],'target_backend_pair_acceptance':False}
        (args.output/'summary.json').write_text(json.dumps(report,indent=2)+'\n');return 3
    command=json.loads(args.adapter)
    if not isinstance(command,list) or not command or not all(isinstance(x,str) for x in command):raise ValueError('Adapter must be JSON argv array')
    captures=[]
    for i in range(args.repeat):
        p=subprocess.run(command,input=json.dumps(request),capture_output=True,text=True,timeout=args.timeout)
        (args.output/f'{i}.stdout').write_text(p.stdout);(args.output/f'{i}.stderr').write_text(p.stderr)
        if p.returncode==3:
            record=json.loads(p.stdout)
            if record.get('status')!='BLOCKED_BY_HARDWARE':raise ValueError('Adapter exit3 without blocked status')
        elif p.returncode!=0:raise ValueError('Adapter failed, exit '+str(p.returncode))
        else:record=validate(json.loads(p.stdout),request)
        record['raw_sha256']=hashlib.sha256(p.stdout.encode()).hexdigest();captures.append(record)
        (args.output/f'{i}.json').write_text(json.dumps(record,indent=2)+'\n')
    captured=all(c.get('status')=='CAPTURED' for c in captures)
    stable=captured and len({c['fingerprint'] for c in captures})==1
    report={'status':'REPEATABLE_CAPTURE' if stable else ('BLOCKED_BY_HARDWARE' if not captured else 'FINGERPRINT_CHANGED'), 'request':request,'capture_count':len(captures),'fingerprints':[c.get('fingerprint') for c in captures], 'target_backend_pair_acceptance':False,'note':'Compare independently captured native and ANGLE reports on the same physical device; one backend never satisfies dual-backend acceptance.'}
    (args.output/'summary.json').write_text(json.dumps(report,indent=2)+'\n')
    return 0 if stable else (3 if not captured else 2)

def main():
    p=argparse.ArgumentParser();p.add_argument('--platform',choices=['host','Android','Windows','EmbeddedLinux'],required=True);p.add_argument('--backend',choices=sorted(BACKENDS),required=True);p.add_argument('--adapter');p.add_argument('--output',type=Path,required=True);p.add_argument('--repeat',type=int,default=2);p.add_argument('--timeout',type=float,default=180);a=p.parse_args()
    if a.repeat<2 or a.repeat>20:p.error('repeat must be 2..20')
    try:return run(a)
    except (ValueError,KeyError,TypeError,OSError,subprocess.TimeoutExpired) as e:print(json.dumps({'status':'FAILED','error':str(e)}));return 2
if __name__=='__main__':raise SystemExit(main())
