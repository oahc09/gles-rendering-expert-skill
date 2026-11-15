#!/usr/bin/env python3
"""Rule-based experiment advisor. No predictions can satisfy measurement gates."""
import argparse
import hashlib
import json
import statistics
from pathlib import Path
from workload_fingerprint import number, fingerprint


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


def decide(candidate, root):
    """Fail closed. VERIFIED is scoped to declared device and archived experiment."""
    reasons=[]; result={'id':candidate.get('id'),'experiment':candidate.get('experiment'),
        'status':'INSUFFICIENT_EVIDENCE','auto_accept':False,'gain_fraction':None,'reasons':reasons}
    if candidate.get('quality',{}).get('pass') is False:
        result['status']='REJECTED_BY_QUALITY'; reasons.append('quality failed');return result
    if not candidate.get('experiment') or not candidate.get('fallback'):
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
    fp=fingerprint(data['workload']); reports=[]
    for candidate in data.get('candidates',[]):
        score=[]
        for k in ('estimated_gain','implementation_cost','regression_risk','confidence'):
            value=number(candidate.get(k,0),k)
            if value>1:raise ValueError(k+' must be within [0,1]')
            score.append(value)
        if candidate.get('workload_id') not in (None,fp['workload_id']): raise ValueError('candidate workload mismatch')
        report=decide(candidate,root)
        relevant=bool(set(candidate.get('labels',[])) & set(fp['labels']) - {'UNKNOWN'})
        if report['status']=='RECOMMENDED_FOR_EXPERIMENT' and not relevant:
            report['status']='INSUFFICIENT_EVIDENCE';report['reasons'].append('no supporting workload hypothesis')
        report['priority_score']=round(score[0]*score[3]*(1-score[2])/(1+score[1]),6)
        report['ranking_basis']={'hypothesis_only':True,'estimated_gain':score[0],'confidence':score[3],'risk':score[2],'cost':score[1]}
        reports.append(report)
    reports.sort(key=lambda x:(-x['priority_score'],str(x['id'])))
    return {'schema_version':'1.0','workload':fp,'candidates':reports,'automatic_renderer_mutation':False}


def main():
    p=argparse.ArgumentParser();p.add_argument('input',type=Path);p.add_argument('--output',type=Path);a=p.parse_args()
    try:result=advise(json.loads(a.input.read_text()),a.input.parent);code=0
    except (ValueError,KeyError,TypeError,OSError) as e:result={'status':'INVALID','error':str(e)};code=2
    s=json.dumps(result,indent=2,allow_nan=False)+'\n'
    if a.output:a.output.write_text(s)
    else:print(s,end='')
    return code
if __name__=='__main__':raise SystemExit(main())
