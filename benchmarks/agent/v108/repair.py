#!/usr/bin/env python3
"""Bounded structured-repair corpus. Fixtures are never model evaluations.

The deliberately narrow oracle accepts a single named repair field. It never
executes model-supplied code and does not assert general patch equivalence.
"""
import argparse, copy, hashlib, importlib.util, json, math, os
from pathlib import Path
import shutil, sys, tempfile
ROOT=Path(__file__).resolve().parents[3]

def module(name, path):
    spec=importlib.util.spec_from_file_location(name,ROOT/path)
    m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m);return m
adv=module('v108_adversarial','benchmarks/pipeline/adversarial/check.py')
state=module('v108_state','benchmarks/state_machine/model.py')
policy=module('v108_policy','benchmarks/robustness/policy.py')
fuzz=module('v108_shader_fuzz','tools/shader_fuzz.py')
diff=module('v108_differential','benchmarks/differential/run.py')

def digest(value):return hashlib.sha256(json.dumps(value,sort_keys=True,allow_nan=False).encode()).hexdigest()

def build():
    result=[]
    def add(domain, name, artifact, fix, failure, ceiling=4096):
        result.append(dict(case_id='V108-R%02d'%(len(result)+1),domain=domain,name=name,input=artifact,
            oracle=dict(expected=fix,failure=failure,kind='bounded structured repair fixture'),
            patch_ceiling_bytes=ceiling,scope='HOST_FIXTURE_ONLY',provider_status='BLOCKED_BY_PROVIDER',
            workflow=['Diagnose','Reproduce','Minimize','Patch','Compile/Run','Differential Verify','Report']))
    # Preserve graph resources/workload; the agent may only repair the alias policy.
    for c in adv.graph_cases()[1:7]:
        add('graph',c['name'],dict(graph=c['graph'],aliases=c['aliases']),{'aliases':[]},c['expected_rule'])
    # Captured ABI differences must cause a recompile/rebind decision, not fabricated reflection.
    for c in adv.abi_cases()[1:7]:
        add('abi',c['name'],{k:c[k] for k in ('manifest','reflection','capability','active_uniforms','required_uniforms')},
            {'action':'reject_cached_program_and_recompile'},c['expected_rule'])
    for domain in state.DOMAINS[:6]:
        seq=['create:'+domain,'bind:'+domain,'delete:'+domain,'audit:'+domain]
        add('lifecycle','invalidate '+domain+' application cache',{'sequence':seq,'injected_fault':domain},
            {'cache_invalidation':'on_delete'},'HARNESS_FAILURE')
    for name,args in [('zero-width',[0,4,4]),('negative-width',[-1,4,4]),('channels',[4,4,5]),
                      ('oversized-dimension',[4097,1,4]),('byte-budget',[1024,1024,4]),('boolean-width',[True,4,4])]:
        add('resource',name,{'texture_args':args}, {'action':'reject_before_allocation'},'EXPECTED_ERROR')
    # Compiler-invalid source is immutable evidence; only the repaired shader is submitted.
    invalid=[c for c in fuzz.corpus(7) if c['expected']=='reject' and c['version']==300][:6]
    for c in invalid:
        add('shader',c['id'],c,{'action':'repair_source'},'compile_or_link_error',16384)
    for c in [x for x in diff.cases() if x['kind']=='fbo_pixels']:
        a={'status':'EXECUTED','pixels':c['expected']*16,'harness_gl_error':0}
        b=copy.deepcopy(a);b['pixels'][0]=(b['pixels'][0]+17)%256
        add('differential',c['id'],{'case':c,'observations':[a,b]},
            {'classification':'FAIL','driver_bug_proven':False},'numeric_mismatch')
    assert len(result)==36
    return {'schema_version':1,'model_quality':'NOT_EVALUATED','provider_status':'BLOCKED_BY_PROVIDER','cases':result}

def request(case):
    # Hidden oracle is not included in model-facing requests.
    return {k:copy.deepcopy(case[k]) for k in ('case_id','domain','name','input','patch_ceiling_bytes','workflow')}

def evaluate(case, patch, compiler=None):
    encoded=json.dumps(patch,sort_keys=True,allow_nan=False).encode()
    if len(encoded)>case['patch_ceiling_bytes']:raise ValueError('patch budget exceeded')
    domain=case['domain'];data=case['input'];expected=case['oracle']['expected']
    if domain=='shader':
        if set(patch)!={'sources'} or not isinstance(patch['sources'],dict):return {'status':'FAIL'}
        if set(patch['sources'])!=set(data['sources']):return {'status':'FAIL'}
        if any(not isinstance(s,str) or not s.startswith('#version 300 es\n') for s in patch['sources'].values()):return {'status':'FAIL'}
        if patch['sources']==data['sources']:return {'status':'FAIL'}
        compiler=compiler or os.environ.get('GLSLANG_VALIDATOR') or shutil.which('glslangValidator')
        if not compiler or not shutil.which(str(compiler)):return {'status':'BLOCKED_BY_TOOLCHAIN'}
        with tempfile.TemporaryDirectory() as d:
            fixed=dict(data,sources=patch['sources'],expected='accept')
            before=fuzz.run_case(data,compiler,Path(d)/'before',3,512,16384)
            after=fuzz.run_case(fixed,compiler,Path(d)/'after',3,512,16384)
        # Source acceptance alone cannot prove preservation of rendering semantics.
        ok=before['status']=='EXPECTED_ERROR' and after['status']=='PASS'
        return {'status':'COMPILE_ONLY_PASS' if ok else 'FAIL','before':before['status'],'after':after['status'],'runtime':'NOT_RUN','semantic_preservation':'REVIEW_REQUIRED'}
    if patch!=expected:return {'status':'FAIL'}
    if domain=='graph':
        before=adv.graph_check(data['graph'],data['aliases']);after=adv.graph_check(data['graph'],patch['aliases'])
        ok=not before['valid'] and after['valid']
    elif domain=='abi':
        errors=adv.abi_check(data['manifest'],reflection=data['reflection'],capability=data['capability'],active_uniforms=data['active_uniforms'],required_uniforms=data['required_uniforms'])
        ok=any(case['oracle']['failure'] in e for e in errors)
    elif domain=='lifecycle':
        before=state.replay(data['sequence'],data['injected_fault']);after=state.replay(data['sequence'])
        ok=before[-1]=='HARNESS_FAILURE' and all(x=='PASS' for x in after)
    elif domain=='resource':
        try:policy.texture(*data['texture_args']);ok=False
        except policy.Rejected:ok=True
    elif domain=='differential':ok=diff.compare(data['case'],*data['observations'])=='FAIL'
    else:raise ValueError('unknown domain')
    return {'status':'FIXTURE_PASS' if ok else 'FAIL','evidence':'AUTHORED_HOST_FIXTURE','model_quality':'NOT_EVALUATED'}

def score_provider(corpus, manifest, adjudications):
    """Reject incomplete/unpaired/synthetic evidence, then count independent reviews.

    Executable fixture results are separate and never converted to provider scores.
    This adapter ingests already captured provider results; it makes no network calls.
    """
    if manifest.get('synthetic_infrastructure_test') or not manifest.get('provider'):
        raise ValueError('real provider identity required; fixtures prohibited')
    cases={c['case_id']:c for c in corpus['cases']};expected={(k,c) for k in cases for c in ('no_skill','with_skill')}
    rows=manifest.get('results',[]);keys=[(r['case_id'],r['condition']) for r in rows]
    if len(keys)!=len(set(keys)) or set(keys)!=expected:raise ValueError('complete unique paired run required')
    captured={}
    for r in rows:
        if r.get('status')!='RESPONSE_CAPTURED' or not isinstance(r.get('response'),str) or not r['response'].strip():raise ValueError('uncaptured response')
        h=hashlib.sha256(r['response'].encode()).hexdigest()
        if h!=r.get('response_sha256'):raise ValueError('response hash mismatch')
        captured[(r['case_id'],r['condition'])]=h
    metrics={c:{'reviewed':0,'correct_fix':0,'introduced_regressions':0} for c in ('no_skill','with_skill')};seen=set()
    for a in adjudications:
        key=(a['case_id'],a['condition'])
        if key not in expected or key in seen:raise ValueError('duplicate/unknown review')
        seen.add(key)
        if a.get('response_sha256')!=captured[key] or not a.get('reviewer') or not a.get('rationale'):raise ValueError('independent bound review required')
        for k in ('correct_fix','introduced_regression'):
            if type(a.get(k)) is not bool:raise ValueError('explicit review outcome required')
        for stage in ('baseline','patched'):
            e=a.get(stage,{})
            if e.get('status') not in ('PASS','FAIL') or any(not e.get(k) for k in ('artifact_sha256','log_sha256','suite_sha256','environment','command')):raise ValueError('actual stage evidence required')
        if any(a['baseline'][k]!=a['patched'][k] for k in ('suite_sha256','environment')):raise ValueError('same regression suite/environment required')
        if a['correct_fix'] and (a['patched']['status']!='PASS' or a['introduced_regression']):raise ValueError('failing/regressing repair cannot pass')
        m=metrics[a['condition']];m['reviewed']+=1;m['correct_fix']+=a['correct_fix'];m['introduced_regressions']+=a['introduced_regression']
    if seen!=expected:raise ValueError('complete paired independent review required')
    return {'provider':manifest['provider'],'evidence':'EXTERNAL_PROVIDER_REVIEWED','metrics':metrics}

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--output',type=Path,required=True);a=p.parse_args()
    a.output.write_text(json.dumps(build(),indent=2)+'\n')
