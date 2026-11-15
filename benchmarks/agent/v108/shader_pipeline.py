#!/usr/bin/env python3
"""Narrow real shader-repair pipeline: compiler, reducer, two GLES readbacks.

Only a bounded arithmetic expression in a frozen single-invocation SSBO shader
may change. No adapter commands, downloads, network calls or arbitrary code runs.
"""
import argparse, copy, hashlib, json, os, re, shutil, sys, time
from pathlib import Path
import repair as base
fuzz=base.fuzz; diff=base.diff
MAX_SOURCE=4096

def sha(raw):return hashlib.sha256(raw).hexdigest()
def inventory():return {c['id']:c for c in diff.cases() if c['kind']=='ssbo_numeric'}
def fixture(case_id):
    case=copy.deepcopy(inventory()[case_id]);key='shader.comp';source=case['sources'][key]
    broken=source.replace('value=', 'value=undefined_input + ')
    return case, dict(case,sources={key:broken},expected='reject')
def validate_patch(case, source):
    if not isinstance(source,str) or len(source.encode())>MAX_SOURCE:raise ValueError('source quota/type')
    prefix,suffix=case['sources']['shader.comp'].split('value=',1)[0]+'value=', '; }\n'
    if not source.startswith(prefix) or not source.endswith(suffix):raise ValueError('fixed shader interface/envelope required')
    expression=source[len(prefix):-len(suffix)]
    if len(expression)>256 or not expression.strip():raise ValueError('expression quota')
    # No statements, declarations, accesses, loops or additional invocations.
    tokens=re.findall(r'sqrt|\d+(?:\.\d*)?(?:[eE][+-]?\d+)?|[+*/().\-]|\s+',expression)
    if ''.join(tokens)!=expression:raise ValueError('only bounded numeric arithmetic and sqrt allowed')
    if expression.count('(')>16:raise ValueError('nesting quota')
    return dict(case,sources={'shader.comp':source},expected='accept')
def validate_configs(configs):
    if not isinstance(configs,list) or len(configs)!=2 or {c.get('kind') for c in configs}!={'mesa','angle'}:
        raise ValueError('exactly Mesa and ANGLE configurations required')
    for c in configs:
        allowed={'kind','egl','gles'}|({'icd'} if c['kind']=='angle' else set())
        if set(c)!=allowed:raise ValueError('unexpected driver configuration fields')
        for key in allowed-{'kind'}:
            if not isinstance(c[key],str) or not Path(c[key]).is_file():raise FileNotFoundError('missing driver file: '+str(c.get(key)))
    if configs[0]['egl']==configs[1]['egl'] or configs[0]['gles']==configs[1]['gles']:raise ValueError('distinct implementation libraries required')

def minimize_same_failure(broken, compiler, out):
    """Reuse W5's existing ddmin; an out-of-domain deletion is not a timeout."""
    name, source=next(iter(broken['sources'].items()))
    initial=fuzz.isolated([compiler,str((out/name).resolve())],2,512)
    signature=next((re.sub(r'^ERROR: [^:]+:[0-9]+: ', '', line) for line in initial['log'].splitlines() if line.startswith('ERROR:') and 'compilation errors' not in line),None)
    if not signature or initial['exit_code'] not in (2,3):return {'status':'INCONCLUSIVE'}
    deadline=time.monotonic()+15
    def oracle(candidate):
        if not candidate.startswith(source.splitlines()[0]+'\n'):
            return {'matches':False,'diagnostic':'outside fixed version domain'}
        if time.monotonic()>=deadline:return {'matches':False,'error_type':'BudgetExhausted'}
        trial=out/'reducer-candidate.comp';trial.write_text(candidate)
        result=fuzz.isolated([compiler,str(trial.resolve())],min(2,max(.01,deadline-time.monotonic())),512)
        matches=result['status']=='EXITED' and result['exit_code'] in (2,3) and signature in result['log']
        return {'matches':matches,'exit_code':result['exit_code'],'diagnostic':result['log'],
          **({'error_type':result['status']} if result['status']!='EXITED' else {}),
          'compiler_crash':result['exit_code'] is not None and result['exit_code']<0}
    reduced=diff.reducer.minimize(source,oracle,max_attempts=40)
    (out/'reduced.comp').write_text(reduced.pop('source'))
    return dict(reduced,predicate=signature,minimality_domain='line deletion preserving exact version and original first diagnostic',budget_seconds=15,max_attempts=40)

def run(case_id,source,compiler,configs,out):
    case,broken=fixture(case_id);patched=validate_patch(case,source)
    out=Path(out);out.mkdir(parents=True,exist_ok=False)
    report=dict(schema_version=1,case_id=case_id,host_status='INCOMPLETE',provider_status='BLOCKED_BY_PROVIDER',model_quality='NOT_EVALUATED',
      scope='authored bounded arithmetic shader repair; real host readback, not physical GPU or agent performance',
      source_sha256=sha(Path(__file__).read_bytes()),patch_sha256=sha(source.encode()),stages={})
    def finish(status):
        report['host_status']=status
        (out/'report.json').write_text(json.dumps(report,indent=2)+'\n')
        (out/'report.md').write_text('# Shader repair pipeline\n\nHost: '+status+'\nProvider: BLOCKED_BY_PROVIDER\nModel quality: NOT_EVALUATED\n\n'+ '\n'.join('- '+k+': '+str(v.get('status','recorded')) for k,v in report['stages'].items())+'\n')
        return report
    compiler=shutil.which(str(compiler)) if compiler else None
    if not compiler:return finish('BLOCKED_BY_TOOLCHAIN')
    report['compiler_sha256']=sha(Path(compiler).read_bytes())
    before=fuzz.run_case(broken,compiler,out/'before',3,512,MAX_SOURCE)
    after=fuzz.run_case(patched,compiler,out/'patched',3,512,MAX_SOURCE)
    report['stages']['compile']={'status':'PASS' if before['status']=='EXPECTED_ERROR' and after['status']=='PASS' else 'FAIL','before':before,'after':after}
    if report['stages']['compile']['status']!='PASS':return finish('FAIL')
    reduced=minimize_same_failure(broken,compiler,out/'before')
    report['stages']['minimize']=reduced
    # Independently repeat the reduced failing source; exact original diagnostic
    # must persist. A crash, timeout or unrelated error cannot satisfy this.
    reduced_path=out/'before/reduced.comp'
    if reduced.get('status')!='REPRODUCED' or not reduced_path.exists():return finish('INCOMPLETE')
    repeats=[]
    for i in range(3):
        observed=fuzz.isolated([compiler,str(reduced_path.resolve())],2,512)
        ok=observed['status']=='EXITED' and observed['exit_code'] in (2,3) and reduced['predicate'] in observed['log']
        repeats.append({'matches':ok,**observed})
    report['stages']['repeat']={'status':'PASS' if all(r['matches'] for r in repeats) else 'FAIL','observations':repeats}
    if report['stages']['repeat']['status']!='PASS':return finish('FAIL')
    try:validate_configs(configs)
    except (ValueError,FileNotFoundError) as e:
        report['stages']['differential']={'status':'BLOCKED_BY_DRIVER','reason':str(e)};return finish('BLOCKED_BY_DRIVER')
    # Reuse W5 isolated software-driver processes; verify baseline remains valid,
    # original remains compiler-rejected, and candidate produces CPU oracle value.
    original=dict(broken,kind='shader',expected_compile=False,expected_link=False)
    selected=[dict(case,id=case_id+'-control'),dict(original,id=case_id+'-broken'),dict(patched,id=case_id+'-patch',expected=case['expected'])]
    runs=[diff.isolated(c,selected) for c in configs]
    report['stages']['differential']={'status':'INCOMPLETE','runs':runs}
    if any(r.get('status')!='EXECUTED' or len(r.get('cases',[]))!=3 for r in runs):return finish('BLOCKED_BY_DRIVER')
    metadata=[r.get('metadata',{}) for r in runs]
    if {m.get('implementation') for m in metadata}!={'mesa','angle'} or any(not m.get('libraries') or not m.get('renderer') for m in metadata):
        return finish('BLOCKED_BY_DRIVER')
    comparisons=[{'id':c['id'],'status':diff.compare(c,runs[0]['cases'][i],runs[1]['cases'][i])} for i,c in enumerate(selected)]
    report['stages']['differential']['comparisons']=comparisons
    passed=all(c['status']=='PASS' for c in comparisons)
    report['stages']['differential']['status']='PASS' if passed else 'FAIL'
    if not passed:return finish('FAIL')
    # A domain-limited reducer may exhaust its one-minimal proof; do not promote.
    return finish('HOST_PASS' if reduced.get('one_minimal') else 'INCOMPLETE_MINIMALITY')

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--case',choices=list(inventory()),required=True)
    p.add_argument('--patch',type=Path,required=True);p.add_argument('--compiler',default=os.environ.get('GLSLANG_VALIDATOR','glslangValidator'))
    p.add_argument('--config',type=Path,required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args()
    if a.patch.stat().st_size>MAX_SOURCE:p.error('patch exceeds quota')
    if a.config.stat().st_size>16384:p.error('config exceeds quota')
    r=run(a.case,a.patch.read_text(),a.compiler,json.loads(a.config.read_text()),a.output)
    print(json.dumps({'host_status':r['host_status'],'provider_status':r['provider_status']}))
    raise SystemExit(0 if r['host_status']=='HOST_PASS' else 2)
