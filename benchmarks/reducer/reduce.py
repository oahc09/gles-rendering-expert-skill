#!/usr/bin/env python3
"""Deterministic line ddmin preserving an exact compiler-failure predicate.
No shell, no generated-code execution, bounded attempts/timeouts, crash != match.
This is a local syntax/compiler reducer, not a GPU semantic/driver reducer.
"""
import argparse, hashlib, json, os, re, shutil, subprocess, tempfile, time
from pathlib import Path

def sha(raw): return hashlib.sha256(raw).hexdigest()

def compile_source(source, compiler, stage, signature, timeout=5):
    with tempfile.TemporaryDirectory(prefix='gles-reducer-') as directory:
        path=Path(directory)/('candidate.'+stage);path.write_text(source)
        try:
            p=subprocess.run([str(compiler),'-S',stage,str(path)],capture_output=True,text=True,timeout=timeout)
            output=p.stdout+p.stderr
            return {'exit_code':p.returncode,'diagnostic':output,'matches':p.returncode>0 and signature in output,
                    'compiler_crash':p.returncode<0,'source_sha256':sha(source.encode())}
        except (subprocess.TimeoutExpired,OSError) as error:
            return {'exit_code':None,'diagnostic':str(error),'matches':False,'compiler_crash':False,'error_type':type(error).__name__,'source_sha256':sha(source.encode())}

def minimize(source, oracle, max_attempts=200):
    lines=source.splitlines(keepends=True)
    initial=oracle(source)
    trials=[{'source_sha256':sha(source.encode()),**initial}]
    if not initial['matches']:
        return {'status':'INCONCLUSIVE' if initial.get('error_type') or initial.get('compiler_crash') else 'NOT_REPRODUCED','source':source,'trials':trials,'one_minimal':False}
    chunks=2
    while len(lines)>0 and len(trials)<max_attempts:
        size=max(1,(len(lines)+chunks-1)//chunks);changed=False
        for start in range(0,len(lines),size):
            if len(trials)>=max_attempts:break
            candidate=lines[:start]+lines[start+size:]
            result=oracle(''.join(candidate));trials.append({'source_sha256':sha(''.join(candidate).encode()),**result})
            if result['matches']:
                lines=candidate;chunks=max(2,chunks-1);changed=True;break
        if changed:continue
        if chunks>=len(lines):break
        chunks=min(len(lines),chunks*2)
    # Audit 1-minimal explicitly, even if budget ended; no false minimal claim.
    one_minimal=True
    for index in range(len(lines)):
        if len(trials)>=max_attempts:one_minimal=False;break
        test=lines[:index]+lines[index+1:];result=oracle(''.join(test));trials.append({'source_sha256':sha(''.join(test).encode()),**result})
        if result['matches'] or result.get('error_type') or result.get('compiler_crash'):one_minimal=False
    return {'status':'REPRODUCED','source':''.join(lines),'trials':trials,'one_minimal':one_minimal}

def fixture_source(directory, name, stage):
    if not isinstance(name,str) or Path(name).name!=name or Path(name).suffix!='.'+stage:
        raise ValueError('Fixture source must be a shader basename for its stage')
    root=directory.resolve();path=(root/name).resolve()
    if path.parent!=root:raise ValueError('Fixture source escapes through a link')
    return path.read_text()

def run_fixture(fixture, compiler, out):
    data=json.loads(fixture.read_text());signature=data['signature'];stage=data['stage']
    source=fixture_source(fixture.parent,data['source'],stage);patch=fixture_source(fixture.parent,data['patch'],stage)
    if stage not in ('vert','frag','comp'):raise ValueError('Unknown shader stage')
    if not signature or len(signature)>500:raise ValueError('Failure signature required')
    version=source.splitlines()[0]
    def oracle(s):
        structural=s.startswith(version+'\n') and 'void main() {' in s and s.rstrip().endswith('}') and 'precision highp float;' in s
        if stage=='comp':structural=structural and 'layout(local_size_x=1) in;' in s
        if not structural:return {'exit_code':None,'diagnostic':'outside fixed version/stage/main/precision reduction domain','matches':False,'compiler_crash':False}
        return compile_source(s,compiler,stage,signature)
    result=minimize(source,oracle);out.mkdir(parents=True,exist_ok=True)
    reduced=out/('reduced.'+stage);reduced.write_text(result.pop('source'))
    repeat=[oracle(reduced.read_text()) for _ in range(3)]
    fixed=compile_source(patch,compiler,stage,signature)
    success=result['status']=='REPRODUCED' and result['one_minimal'] and all(x['matches'] for x in repeat) and fixed['exit_code']==0
    result['reproduction_status']=result.pop('status')
    report={'schema_version':1,'case_id':data['id'],'status':'PASS' if success else 'FAIL','source_sha256':sha(source.encode()),'fixture_sha256':sha(fixture.read_bytes()),'compiler_sha256':sha(Path(compiler).read_bytes()),'reducer_sha256':sha(Path(__file__).read_bytes()),'predicate':signature,'minimality_domain':'line deletion preserving original version, precision, stage layout and main envelope','original_bytes':len(source.encode()),'reduced_bytes':reduced.stat().st_size,'reduced_sha256':sha(reduced.read_bytes()),'patch_sha256':sha(patch.encode()),'repeat':repeat,'patch_validation':fixed,**result}
    (out/'report.json').write_text(json.dumps(report,indent=2)+'\n');return report

def main():
    p=argparse.ArgumentParser();p.add_argument('--compiler',default=shutil.which('glslangValidator'));p.add_argument('--output',type=Path,required=True);a=p.parse_args()
    if not a.compiler:print('BLOCKED_BY_TOOLCHAIN');return 2
    compiler=Path(a.compiler).resolve();a.output.mkdir(parents=True,exist_ok=True)
    results=[run_fixture(f,compiler,a.output/f.stem) for f in sorted((Path(__file__).parent/'fixtures').glob('*.json'))]
    try:
        v=subprocess.run([str(compiler),'--version'],capture_output=True,text=True,timeout=5)
        version_result={'exit_code':v.returncode,'stdout':v.stdout,'stderr':v.stderr}
    except (OSError,subprocess.TimeoutExpired) as error:
        version_result={'exit_code':None,'error_type':type(error).__name__,'stderr':str(error)}
    report={'schema_version':1,'scope':'real glslang compile failures; authored fixtures, not driver defects','compiler_version':version_result,'cases':results,'status':'PASS' if version_result['exit_code']==0 and len(results)==10 and all(x['status']=='PASS' for x in results) else 'FAIL'}
    (a.output/'summary.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps({'status':report['status'],'cases':len(results)}));return 0 if report['status']=='PASS' else 1
if __name__=='__main__':raise SystemExit(main())
