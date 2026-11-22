#!/usr/bin/env python3
"""Rule-based experiment advisor. No predictions can satisfy measurement gates."""
import argparse
import hashlib
import json
import statistics
from pathlib import Path
from workload_fingerprint import number, fingerprint
from optimization_experiments import resolve
from gpu_decision_v111 import decide as assess_decision


def verify_artifacts(artifacts, root, measurement):
    if not artifacts: return False
    root=Path(root).resolve()
    bound=False
    for item in artifacts:
        path=(root/item['path']).resolve()
        if not path.is_relative_to(root) or not path.is_file(): return False
        if hashlib.sha256(path.read_bytes()).hexdigest()!=item.get('sha256'):return False
        if item.get('kind')=='paired-timing-json':
            try: payload=json.loads(path.read_text())
            except (ValueError,UnicodeError): return False
            bound = payload=={k:v for k,v in measurement.items() if k!='artifacts'}
    return bound


def valid_fallback(value):
    return isinstance(value, str) and bool(value.strip())


def decision_alignment(candidate, decision, labels):
    """Match only a known variant. Legacy profiles are not proof of device capability."""
    compute = candidate.get('experiment') == 'shader-advanced-v1' and 'COMPUTE' in labels
    if decision is None:
        return ('DECISION_CONTEXT_REQUIRED', None) if compute else ('LEGACY_HYPOTHESIS_ONLY', None)
    evaluation = decision['objective_evaluation']
    if evaluation['status'] in ('UNSUPPORTED_GOALS', 'NO_RELEVANT_CANDIDATES'):
        return evaluation['status'], None
    strategy = 'compute-to-fragment' if compute else None
    if strategy is None:
        # A registered runnable file and a relevant Decision are not enough:
        # no maintained strategy-to-experiment mapping exists for this candidate.
        return 'EXPERIMENT_MAPPING_UNAVAILABLE', None
    match = next((row for row in decision['candidates'] if row['strategy'] == strategy), None)
    if match is None:
        return 'STRATEGY_NOT_RELEVANT_TO_DECISION', None
    return match['status'], match


def decide(candidate, root):
    """Fail closed. VERIFIED is scoped to declared device and archived experiment."""
    reasons=[]; result={'id':candidate.get('id'),'experiment':candidate.get('experiment'),
        'status':'INSUFFICIENT_EVIDENCE','auto_accept':False,'gain_fraction':None,'reasons':reasons}
    if candidate.get('quality',{}).get('pass') is False:
        result['status']='REJECTED_BY_QUALITY'; reasons.append('quality failed');return result
    if not candidate.get('experiment') or not valid_fallback(candidate.get('fallback')):
        reasons.append('experiment and fallback required');return result
    if candidate.get('capability_supported') is not True:
        reasons.append('capability not verified');return result
    threshold=number(candidate.get('minimum_gain',0.03),'minimum_gain')
    if threshold>1: raise ValueError('minimum_gain must be within [0,1]')
    measured=candidate.get('measurement')
    if not measured:
        result['status']='RECOMMENDED_FOR_EXPERIMENT';reasons.append('hypothesis only, not measured');return result
    required=('device','gpu','driver','backend','build_sha','baseline_sha','thermal_state','frequency_state','tool','clock_domain')
    if any(not measured.get(k) for k in required) or measured.get('provenance')!='physical-device' or measured.get('unit')!='ms':
        reasons.append('physical device provenance, scope, units or clock missing');return result
    if measured.get('thermal_stable') is not True or measured.get('warmup_frames',0)<30:
        reasons.append('warmup/thermal control insufficient');return result
    q=candidate.get('quality',{})
    if q.get('pass') is not True or not q.get('golden_id') or not q.get('thresholds'):
        reasons.append('quality oracle incomplete');return result
    if not verify_artifacts(measured.get('artifacts'),root,measured):
        reasons.append('raw artifact missing or hash mismatch');return result
    # Self-declared physical metadata is not independent measurement evidence.
    review=candidate.get('independent_review',{})
    required_bindings={k:measured.get(k) for k in ('device','gpu','driver','backend','build_sha','baseline_sha')}
    required_bindings.update(workload_id=candidate.get('workload_id'),golden_id=q.get('golden_id'),quality_thresholds=q.get('thresholds'),trace_artifacts=measured.get('artifacts'))
    if (not candidate.get('workload_id') or not measured.get('collector_id') or
        not review.get('reviewer_id') or review.get('reviewer_id')==measured.get('collector_id') or
        review.get('decision')!='ACCEPT_MEASUREMENT_AND_QUALITY' or
        review.get('bindings')!=required_bindings or not review.get('quality_artifact')):
        reasons.append('independent capture/quality review required');return result
    root=Path(root).resolve()
    for artifact in (review.get('artifact',{}),review['quality_artifact']):
        path=(root/str(artifact.get('path',''))).resolve()
        if not path.is_relative_to(root) or not path.is_file() or hashlib.sha256(path.read_bytes()).hexdigest()!=artifact.get('sha256'):
            reasons.append('review/quality evidence missing or hash mismatch');return result
    try:review_payload=json.loads((root/review['artifact']['path']).read_text())
    except (ValueError,UnicodeError):
        reasons.append('invalid review artifact');return result
    if review_payload!={k:v for k,v in review.items() if k!='artifact'}:
        reasons.append('review not bound to captured evidence');return result
    pairs=measured.get('pairs',[])
    if len(pairs)<5:
        reasons.append('at least five interleaved pairs required');return result
    gains=[]
    for index,pair in enumerate(pairs):
        if pair.get('order') != ('AB' if index%2==0 else 'BA'):
            reasons.append('not counterbalanced interleaved A/B');return result
        a=number(pair.get('baseline_ms'),'baseline_ms');b=number(pair.get('candidate_ms'),'candidate_ms')
        if a<=0 or b<=0:raise ValueError('both times must be positive')
        gains.append((a-b)/a)
    result['gain_fraction']=statistics.median(gains)
    # Every pair must beat the threshold; noisy/contradictory runs cannot pass.
    if all(x>threshold for x in gains): result['status']='VERIFIED_IMPROVEMENT'
    elif all(x < -threshold for x in gains): result['status']='REGRESSION'
    else: result['status']='NO_GAIN'
    result['scope']={k:measured[k] for k in required};reasons.append('scoped evidence only; no GPU-family generalization')
    return result


def advise(data, root=Path('.')):
    fp=fingerprint(data['workload'],root); reports=[]
    decision=assess_decision(data['decision_request']) if 'decision_request' in data else None
    for candidate in data.get('candidates',[]):
        score=[]
        for k in ('estimated_gain','implementation_cost','regression_risk','confidence'):
            value=number(candidate.get(k,0),k)
            if value>1:raise ValueError(k+' must be within [0,1]')
            score.append(value)
        if candidate.get('workload_id') not in (None,fp['workload_id']): raise ValueError('candidate workload mismatch')
        gain_range=candidate.get('estimated_gain_range')
        if gain_range is not None:
            if not isinstance(gain_range,list) or len(gain_range)!=2:
                raise ValueError('estimated_gain_range must be [lower,upper]')
            lower,upper=[number(x,'estimated_gain_range') for x in gain_range]
            if not lower<=upper<=1:raise ValueError('estimated_gain_range must be ordered within [0,1]')
        else:
            # Backward-compatible point input does not invent a confidence interval.
            lower=upper=score[0]
        binding=resolve(candidate.get('experiment'))
        report=decide(candidate,root)
        report['experiment_binding']=binding
        if binding is None and report['status']!='REJECTED_BY_QUALITY':
            report['status']='INSUFFICIENT_EVIDENCE'
            report['reasons'].append('unknown/unavailable experiment; register a bounded runnable entry first')
        labels=set(candidate.get('labels',[]))
        relevant=bool(labels & (set(fp['labels']) - {'UNKNOWN'}))
        alignment, matched=decision_alignment(candidate, decision, labels)
        if alignment != 'LEGACY_HYPOTHESIS_ONLY':
            report['decision_alignment']={'status':alignment, 'decision_id':decision['decision_id'] if decision else None,
                'strategy':matched['strategy'] if matched else None,
                'blocked_reasons':matched['blocked_reasons'] if matched else [],
                'evidence':'DECLARED_INPUTS_ONLY', 'execution_authorized':False}
        if alignment not in ('LEGACY_HYPOTHESIS_ONLY','EXPERIMENT_REQUIRED') and report['status']!='REJECTED_BY_QUALITY':
            report['status']='INSUFFICIENT_EVIDENCE'
            report['gain_fraction']=None
            report.pop('scope',None)
            report['reasons'].append('not eligible under Decision alignment: '+alignment)
        # The bridge binds eligibility only, not native or independent measured evidence.
        # A cross-entry request must not turn an existing measurement into a verified claim.
        if matched and report['status'] in ('VERIFIED_IMPROVEMENT','REGRESSION','NO_GAIN'):
            report['status']='INSUFFICIENT_EVIDENCE'
            report['gain_fraction']=None
            report.pop('scope',None)
            report['reasons'].append('Decision inputs are not bound to the physical measurement')
        if report['status']=='RECOMMENDED_FOR_EXPERIMENT' and not relevant:
            report['status']='INSUFFICIENT_EVIDENCE';report['reasons'].append('no supporting workload hypothesis')
        # Structural completeness, not authenticity or a substitute for measurement gates.
        completeness_items={'runnable_experiment':binding is not None,
            'supported_workload':relevant,'capability':candidate.get('capability_supported') is True,
            'fallback':valid_fallback(candidate.get('fallback')),
            'quality_contract':bool(candidate.get('quality',{}).get('golden_id')) and bool(candidate.get('quality',{}).get('thresholds'))}
        completeness=sum(completeness_items.values())/len(completeness_items)
        report['priority_score']=round(lower*score[3]*(1-score[2])*completeness/(1+score[1]),6) if binding and alignment in ('LEGACY_HYPOTHESIS_ONLY','EXPERIMENT_REQUIRED') else 0
        report['ranking_basis']={'hypothesis_only':True,'estimated_gain_range':[lower,upper],
            'range_kind':'SUPPLIED_HYPOTHESIS' if gain_range is not None else 'LEGACY_POINT_NOT_INTERVAL',
            'confidence':score[3],'risk':score[2],'cost':score[1],
            'evidence_completeness':completeness,'completeness_checks':completeness_items,
            'formula':'lower_gain * confidence * (1-risk) * structural_completeness / (1+cost)',
            'acceptance_effect':'NONE'}
        reports.append(report)
    reports.sort(key=lambda x:(-x['priority_score'],str(x['id'])))
    result={'schema_version':'1.0','workload':fp,'candidates':reports,'automatic_renderer_mutation':False}
    if decision is not None:
        result['objective_evaluation']=decision['objective_evaluation']
    return result


def main():
    p=argparse.ArgumentParser();p.add_argument('input',type=Path);p.add_argument('--output',type=Path);a=p.parse_args()
    try:result=advise(json.loads(a.input.read_text()),a.input.parent);code=0
    except (ValueError,KeyError,TypeError,OSError) as e:result={'status':'INVALID','error':str(e)};code=2
    s=json.dumps(result,indent=2,allow_nan=False)+'\n'
    if a.output:a.output.write_text(s)
    else:print(s,end='')
    return code
if __name__=='__main__':raise SystemExit(main())
