#!/usr/bin/env python3
"""Paired external-model benchmark. Never substitutes fixture answers for live calls."""
import argparse
import hashlib
import json
from pathlib import Path
import shlex
import subprocess
import sys
import time

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[1]
MODES={'Generate','Review','Diagnose','Optimize'}

def digest(data):
    return hashlib.sha256(data.encode('utf-8')).hexdigest()

def validate_cases(payload):
    cases=payload['cases']
    if len(cases)<60:
        raise ValueError('At least 60 cases required')
    ids=set()
    for case in cases:
        required={'case_id','mode','prompt','device_capabilities','core_case','severity','expected_findings','legal_controls','forbidden_advice','fallback','evidence_sources','compile_evidence','rubric'}
        if required-set(case):
            raise ValueError(f'Missing fields: {required-set(case)}')
        if case['case_id'] in ids or case['mode'] not in MODES:
            raise ValueError('Duplicate ID or invalid mode')
        ids.add(case['case_id'])
        for key in ('expected_findings','legal_controls','forbidden_advice','evidence_sources'):
            if not case[key] or len(case[key])!=len(set(case[key])):
                raise ValueError(f'{case["case_id"]}: empty/duplicate {key}')
        if not case['fallback'] or not case['prompt']:
            raise ValueError('Missing prompt/fallback')
    if {c['mode'] for c in cases}!=MODES:
        raise ValueError('All four modes required')
    return cases

def request_for(case, skill, enabled):
    # Never expose ground truth, rubric, legal controls, or fallback to the model.
    return {'schema_version':1,'case_id':case['case_id'],'condition':'with_skill' if enabled else 'no_skill',
        'system':'You are a GLES rendering engineer. Distinguish API correctness from unverified performance. Explain evidence and limitations.' + ('\n\nAttached Skill:\n'+skill if enabled else ''),
        'prompt':case['prompt'], 'capabilities':case['device_capabilities']}

def run(args):
    payload=json.loads(args.cases.read_text())
    cases=validate_cases(payload)
    if args.case:
        cases=[case for case in cases if case['case_id'] in args.case]
        if {case['case_id'] for case in cases}!=set(args.case):
            raise ValueError('Unknown case ID')
    args.output.mkdir(parents=True,exist_ok=False)
    skill=args.skill.read_text()
    summary={'schema_version':1,'status':'BLOCKED_BY_PROVIDER','case_count':len(cases),'case_source_sha256':digest(args.cases.read_text()),'skill_sha256':digest(skill),'provider_label':args.provider_label,'synthetic_infrastructure_test':args.synthetic_fixture,'results':[], 'model_quality':'NOT_EVALUATED','started_unix':time.time()}
    if not args.adapter:
        (args.output/'summary.json').write_text(json.dumps(summary,indent=2)+'\n')
        return 2
    if not args.provider_label:
        raise ValueError('--provider-label required to identify actual provider/model configuration')
    command=shlex.split(args.adapter)
    if not command:
        raise ValueError('Empty adapter command')
    for case in cases:
        for enabled in (False, True):
            request=request_for(case,skill,enabled)
            stem=f'{case["case_id"]}-{request["condition"]}'
            raw_request=json.dumps(request,ensure_ascii=False)
            (args.output/(stem+'.request.json')).write_text(raw_request+'\n')
            started=time.monotonic()
            try:
                result=subprocess.run(command,input=raw_request,text=True,capture_output=True,timeout=args.timeout,check=False)
                output=result.stdout
                error=result.stderr
                status='RESPONSE_CAPTURED' if result.returncode==0 and output.strip() else 'ADAPTER_FAILED'
                code=result.returncode
            except (OSError, subprocess.TimeoutExpired) as exc:
                output=''
                error=str(exc)
                status='ADAPTER_FAILED'
                code=None
            (args.output/(stem+'.response.txt')).write_text(output)
            (args.output/(stem+'.stderr.txt')).write_text(error)
            summary['results'].append({'case_id':case['case_id'],'condition':request['condition'],'status':status,'exit_code':code,'elapsed_seconds':time.monotonic()-started,'request_sha256':digest(raw_request),'response_sha256':digest(output),'response_file':stem+'.response.txt','adjudication':'PENDING'})
            # Incremental checkpoint survives interrupted long runs.
            summary['status']='RUNNING'
            (args.output/'summary.json').write_text(json.dumps(summary,indent=2)+'\n')
    summary['status']='CAPTURED_PENDING_REVIEW' if all(r['status']=='RESPONSE_CAPTURED' for r in summary['results']) else 'INCOMPLETE_ADAPTER_FAILURE'
    (args.output/'summary.json').write_text(json.dumps(summary,indent=2)+'\n')
    return 0 if summary['status']=='CAPTURED_PENDING_REVIEW' else 1

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--cases',type=Path,default=HERE/'cases.json')
    parser.add_argument('--skill',type=Path,default=ROOT/'SKILL.md')
    parser.add_argument('--adapter',help='Executable command; stdin JSON request -> stdout raw model response. No shell expansion.')
    parser.add_argument('--provider-label',default=None,help='Provider/model/version/configuration identifier; must not contain secrets')
    parser.add_argument('--output',type=Path,required=True,help='NEW directory; existing directories are never overwritten')
    parser.add_argument('--timeout',type=float,default=180)
    parser.add_argument('--case',action='append')
    parser.add_argument('--synthetic-fixture',action='store_true',help='Mark infrastructure-only fixture calls; never real model measurements')
    args=parser.parse_args()
    if args.timeout<=0:
        parser.error('timeout must be positive')
    try:
        return run(args)
    except (ValueError, KeyError, OSError, json.JSONDecodeError) as exc:
        print(f'benchmark error: {exc}',file=sys.stderr)
        return 1
if __name__=='__main__':
    sys.exit(main())
