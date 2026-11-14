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

V3_STAGES=('diagnose','reproduce','minimize','patch','compile_run','differential','report')
V3_CONTROLS=('valid_baseline_must_remain_valid','unavailable_evidence_is_not_pass','fixtures_are_not_model_results')

def score_v3(corpus, manifest, adjudications, artifacts):
    """Strict, evidence-bound paired review metrics, not automatic truth inference.

    `artifacts` maps SHA256 to UTF-8 artifact/log text, supplied by the caller.
    No files, credentials, commands or provider APIs are accessed here. All
    declared evidence is checked against actual supplied bytes. Authenticity of
    provider identity and independent review remains an external audit boundary.
    """
    import re
    sha_pattern=re.compile(r'^[0-9a-f]{64}$')
    def text(value,name):
        if not isinstance(value,str) or not value.strip():raise ValueError(name+' must be nonempty text')
        return value
    def boolean(value,name):
        if type(value) is not bool:raise ValueError(name+' must be boolean')
        return value
    def hashes(value,name):
        if not isinstance(value,list) or not value or any(not isinstance(h,str) for h in value) or len(value)!=len(set(value)):
            raise ValueError(name+' requires unique artifact hashes')
        for h in value:
            if not isinstance(h,str) or not sha_pattern.fullmatch(h) or h not in artifacts:raise ValueError(name+' missing/invalid hash')
        return value
    if not isinstance(artifacts,dict) or len(artifacts)>2048:raise ValueError('bounded artifact map required')
    total=0
    for h,body in artifacts.items():
        if not isinstance(h,str) or not sha_pattern.fullmatch(h) or not isinstance(body,str):raise ValueError('invalid artifact entry')
        raw=body.encode();total+=len(raw)
        if len(raw)>2**20 or total>16*2**20:raise ValueError('artifact quota exceeded')
        if hashlib.sha256(raw).hexdigest()!=h:raise ValueError('artifact content hash mismatch')
    if manifest.get('schema_version')!=3 or manifest.get('corpus_sha256')!=digest(corpus):raise ValueError('v3 frozen corpus binding required')
    text(manifest.get('provider'),'provider')
    if manifest.get('synthetic_infrastructure_test') is not False:raise ValueError('explicit non-synthetic provider record required')
    cases=corpus.get('cases',[])
    if not cases or len({c['case_id'] for c in cases})!=len(cases):raise ValueError('nonempty unique corpus required')
    # Retain the legacy pair, capture hash, regression and reviewer checks.
    legacy=score_provider(corpus,manifest,adjudications)
    by_id={c['case_id']:c for c in cases}
    metrics={mode:dict(reviewed=0,diagnosis_correct=0,true_positives=0,false_negatives=0,false_positives=0,
        legal_controls=0,rejected_legal_controls=0,repair_attempted=0,false_repairs=0,
        minimization_applicable=0,minimization_measured=0,minimization_faithful=0,
        evidence_required=0,evidence_present=0,unmeasured_stages=0,not_applicable_stages=0)
        for mode in ('no_skill','with_skill')}
    def unique_ids(value,allowed,name):
        if not isinstance(value,list) or any(not isinstance(x,str) for x in value) or len(value)!=len(set(value)):
            raise ValueError(name+' must be unique string IDs')
        if allowed is not None and not set(value)<=set(allowed):raise ValueError(name+' has unknown ID')
        return set(value)
    for a in adjudications:
        case=by_id[a['case_id']];m=metrics[a['condition']];m['reviewed']+=1
        for stage in ('baseline','patched'):
            e=a[stage]
            hashes([e['artifact_sha256'],e['log_sha256']],stage)
            hashes([e['suite_sha256']],stage+' suite')
            text(e['command'],stage+' command');text(e['environment'],stage+' environment')
        d=a.get('diagnosis',{})
        if set(d)!={'true_positive_ids','unsupported_findings','rejected_legal_controls','rationale','evidence_sha256'}:raise ValueError('exact diagnosis fields required')
        expected={case['oracle']['failure']}
        tp=unique_ids(d['true_positive_ids'],expected,'true positives')
        unsupported=unique_ids(d['unsupported_findings'],None,'unsupported findings')
        rejected=unique_ids(d['rejected_legal_controls'],V3_CONTROLS,'rejected legal controls')
        if unsupported & (expected|set(V3_CONTROLS)):raise ValueError('unsupported finding overlaps known ID')
        text(d['rationale'],'diagnosis rationale');hashes(d['evidence_sha256'],'diagnosis')
        m['true_positives']+=len(tp);m['false_negatives']+=len(expected-tp);m['false_positives']+=len(unsupported)+len(rejected)
        m['diagnosis_correct']+=tp==expected and not unsupported and not rejected
        m['legal_controls']+=len(V3_CONTROLS);m['rejected_legal_controls']+=len(rejected)
        attempted=boolean(a.get('repair_attempted'),'repair_attempted')
        if a['correct_fix'] and not attempted:raise ValueError('correct fix requires attempted repair')
        m['repair_attempted']+=attempted;m['false_repairs']+=attempted and not a['correct_fix']
        stages=a.get('stage_evidence',{})
        if set(stages)!=set(V3_STAGES):raise ValueError('all named evidence stages required, even when not run')
        for name,e in stages.items():
            if set(e)!={'status','artifact_sha256','rationale'}:raise ValueError('exact stage evidence fields required')
            status=e['status'];text(e['rationale'],name+' rationale')
            if status not in ('PASS','FAIL','NOT_RUN','NOT_APPLICABLE'):raise ValueError('invalid stage status')
            if status in ('PASS','FAIL'):
                hashes(e['artifact_sha256'],name);m['evidence_present']+=1
            elif e['artifact_sha256']!=[]:raise ValueError('unmeasured stage cannot cite measurement artifacts')
            if status=='NOT_APPLICABLE':m['not_applicable_stages']+=1
            else:m['evidence_required']+=1
            if status=='NOT_RUN':m['unmeasured_stages']+=1
        # A correct-fix assertion needs run and report evidence; missing stages
        # remain measurable incompleteness, never silently become a pass.
        if a['correct_fix'] and any(stages[k]['status']!='PASS' for k in ('reproduce','patch','compile_run','differential','report')):
            raise ValueError('correct fix requires successful complete execution evidence')
        z=a.get('minimization',{})
        if set(z)!={'status','original_failure_id','reduced_failure_id','original_sha256','reduced_sha256','replay_log_sha256','rationale'}:raise ValueError('exact minimization fields required')
        text(z['rationale'],'minimization rationale');status=z['status']
        if status not in ('PASS','FAIL','NOT_RUN','NOT_APPLICABLE') or status!=stages['minimize']['status']:raise ValueError('minimization stage mismatch')
        if status!='NOT_APPLICABLE':m['minimization_applicable']+=1
        if status in ('PASS','FAIL'):
            if z['original_failure_id']!=case['oracle']['failure']:raise ValueError('original failure identity mismatch')
            text(z['reduced_failure_id'],'reduced failure ID')
            hashes([z['original_sha256']],'original reproducer');hashes([z['reduced_sha256']],'reduced reproducer');hashes([z['replay_log_sha256']],'replay log')
            if z['original_sha256']!=digest(case['input']):raise ValueError('original reproducer must match frozen case input')
            faithful=z['original_failure_id']==z['reduced_failure_id']
            if (status=='PASS')!=faithful:raise ValueError('minimization status contradicts failure fidelity')
            m['minimization_measured']+=1;m['minimization_faithful']+=faithful
        elif any(z[k] is not None for k in ('original_failure_id','reduced_failure_id','original_sha256','reduced_sha256','replay_log_sha256')):
            raise ValueError('unmeasured minimization fields must be null')
    def ratio(n,d):return n/d if d else None
    for m in metrics.values():
        m.update(diagnosis_accuracy=ratio(m['diagnosis_correct'],m['reviewed']),
            diagnosis_recall=ratio(m['true_positives'],m['true_positives']+m['false_negatives']),
            false_repair_rate=ratio(m['false_repairs'],m['repair_attempted']),
            false_positive_control_rate=ratio(m['rejected_legal_controls'],m['legal_controls']),
            false_discovery_rate=ratio(m['false_positives'],m['true_positives']+m['false_positives']),
            minimization_fidelity=ratio(m['minimization_faithful'],m['minimization_measured']),
            minimization_coverage=ratio(m['minimization_measured'],m['minimization_applicable']),
            evidence_completeness=ratio(m['evidence_present'],m['evidence_required']))
    rates=('diagnosis_accuracy','diagnosis_recall','false_repair_rate','false_positive_control_rate',
           'false_discovery_rate','minimization_fidelity','minimization_coverage','evidence_completeness')
    delta={k:None if any(metrics[c][k] is None for c in metrics) else metrics['with_skill'][k]-metrics['no_skill'][k] for k in rates}
    return dict(schema_version=3,provider=manifest['provider'],evidence='HASH_BOUND_EXTERNAL_REVIEW',
        metrics=metrics,paired_delta_with_minus_without=delta,legacy=legacy,
        authenticity='PROVIDER_AND_REVIEW_IDENTITY_REQUIRE_EXTERNAL_AUDIT')

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--output',type=Path,required=True);a=p.parse_args()
    a.output.write_text(json.dumps(build(),indent=2)+'\n')
