#!/usr/bin/env python3
"""Aggregate independently adjudicated responses, not keyword similarity."""
import argparse
import hashlib
import json
from pathlib import Path
from run import digest, validate_cases, HERE


def ratio(a,b):
    return a/b if b else None


def score(summary, adjudications, cases):
    if summary.get('synthetic_infrastructure_test'):
        raise ValueError('Synthetic fixture responses cannot yield model quality metrics')
    actual={(r['case_id'],r['condition']):r for r in summary['results']}
    labels={c['case_id']:c for c in validate_cases(cases)}
    results={}
    seen=set()
    for row in adjudications:
        key=(row['case_id'],row['condition'])
        if key in seen or key not in actual:
            raise ValueError('Duplicate or unknown adjudication')
        seen.add(key)
        response=actual[key]
        if response['status']!='RESPONSE_CAPTURED' or row['response_sha256']!=response['response_sha256']:
            raise ValueError('Adjudication does not match a captured response hash')
        if not row.get('reviewer') or not row.get('rationale'):
            raise ValueError('Independent reviewer and rationale required')
        expected=set(labels[key[0]]['expected_findings'])
        tp=set(row['true_positive_findings'])
        if not tp<=expected:
            raise ValueError('True positives must use expected finding IDs')
        legal=set(labels[key[0]]['legal_controls'])
        rejected=set(row['rejected_legal_controls'])
        if not rejected<=legal:
            raise ValueError('Unknown legal control')
        unsupported=row['unsupported_findings']
        if not isinstance(unsupported,list):
            raise ValueError('unsupported_findings must be a list')
        group=results.setdefault(key[1],{'reviewed':0,'tp':0,'fn':0,'fp':0,'legal_controls':0,'rejected_legal_controls':0,'compile_pass':0,'compile_tested':0,'debug_complete':0,'debug_reviewed':0,'performance_complete':0,'performance_reviewed':0})
        group['reviewed']+=1; group['tp']+=len(tp); group['fn']+=len(expected-tp)
        group['fp']+=len(rejected)+len(unsupported)
        group['legal_controls']+=len(legal); group['rejected_legal_controls']+=len(rejected)
        compile_result=row.get('compile',{'status':'NOT_RUN'})
        if compile_result['status'] not in ('PASS','FAIL','NOT_RUN','NOT_APPLICABLE'):
            raise ValueError('Invalid compile status')
        if compile_result['status'] in ('PASS','FAIL'):
            if not all(compile_result.get(k) for k in ('command','artifact_sha256','log_sha256','environment')):
                raise ValueError('Compile result requires command/artifact/log hashes and environment')
            group['compile_tested']+=1; group['compile_pass']+=compile_result['status']=='PASS'
        if labels[key[0]].get('repair') or labels[key[0]].get('v105'):
            for metric in ('root_cause_hit','unsupported_performance_claim'):
                value=row.get(metric)
                if value is not None and not isinstance(value,bool):
                    raise ValueError(metric+' must be boolean or null')
                group.setdefault(metric+'_reviewed',0);group.setdefault(metric+'_count',0)
                if value is not None:
                    group[metric+'_reviewed']+=1;group[metric+'_count']+=value
        if labels[key[0]].get('repair'):
            regression=row.get('repair_regression',{'status':'NOT_RUN'})
            if regression.get('status') not in ('PASS','FAIL','NOT_RUN','NOT_APPLICABLE'):
                raise ValueError('Invalid repair regression status')
            group.setdefault('repair_regression_tested',0);group.setdefault('repair_regression_pass',0)
            if regression['status'] in ('PASS','FAIL'):
                if not all(regression.get(k) for k in ('command','artifact_sha256','log_sha256','environment')):
                    raise ValueError('Repair regression requires actual artifact/log evidence')
                group['repair_regression_tested']+=1;group['repair_regression_pass']+=regression['status']=='PASS'
        if labels[key[0]].get('v105'):
            for metric in ('evidence_sufficient','visual_safe','wrong_advice'):
                value=row.get(metric)
                if value is not None and type(value) is not bool:raise ValueError(metric+' must be boolean or null')
                group.setdefault(metric+'_reviewed',0);group.setdefault(metric+'_count',0)
                if value is not None:
                    if not row.get(metric+'_rationale'):raise ValueError(metric+' needs independent review rationale')
                    if metric=='visual_safe' and not row.get('visual_criteria_reference'):raise ValueError('Visual safety needs independently defined criteria reference')
                    group[metric+'_reviewed']+=1;group[metric+'_count']+=value
        mode=labels[key[0]]['mode']
        for label,mode_name in (('debug','Diagnose'),('performance','Optimize')):
            if mode==mode_name:
                value=row.get(label+'_complete')
                if not isinstance(value,bool):
                    raise ValueError(f'{label}_complete boolean required')
                group[label+'_reviewed']+=1; group[label+'_complete']+=value
    for group in results.values():
        group.update({'finding_recall':ratio(group['tp'],group['tp']+group['fn']), 'finding_precision':ratio(group['tp'],group['tp']+group['fp']), 'legal_control_false_positive_rate':ratio(group['rejected_legal_controls'],group['legal_controls']), 'compile_success_rate':ratio(group['compile_pass'],group['compile_tested']), 'debug_completeness_rate':ratio(group['debug_complete'],group['debug_reviewed']), 'performance_completeness_rate':ratio(group['performance_complete'],group['performance_reviewed'])})
    for group in results.values():
        if 'root_cause_hit_reviewed' in group:
            group['root_cause_hit_rate']=ratio(group['root_cause_hit_count'],group['root_cause_hit_reviewed'])
            group['unsupported_performance_claim_rate']=ratio(group['unsupported_performance_claim_count'],group['unsupported_performance_claim_reviewed'])
            group['repair_regression_success_rate']=ratio(group.get('repair_regression_pass',0),group.get('repair_regression_tested',0))
    for group in results.values():
        for metric in ('evidence_sufficient','visual_safe','wrong_advice'):
            if metric+'_reviewed' in group:group[metric+'_rate']=ratio(group[metric+'_count'],group[metric+'_reviewed'])
    paired=sum((case_id,'no_skill') in seen and (case_id,'with_skill') in seen for case_id in labels)
    return {'status':'REVIEWED' if len(seen)==len(actual) and actual else 'PARTIAL_REVIEW','adjudicated_responses':len(seen),'paired_cases':paired,'metrics':results,'limitations':'Human-adjudicated rubric; not automatic semantic truth. Compile, hardware runtime and performance are independent. Null means no evidence, not zero.'}

if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--run',type=Path,required=True)
    parser.add_argument('--adjudications',type=Path,required=True)
    parser.add_argument('--cases',type=Path,default=HERE/'cases.json')
    parser.add_argument('--output',type=Path,required=True)
    parser.add_argument('--evidence-root',type=Path,help='Required when adjudications claim compile PASS/FAIL; contains artifact_file and log_file.')
    args=parser.parse_args()
    summary=json.loads((args.run/'summary.json').read_text())
    if digest(args.cases.read_text())!=summary['case_source_sha256']:
        raise ValueError('Corpus changed since response capture; use the original corpus')
    adjudications=json.loads(args.adjudications.read_text())
    for row in adjudications:
        for evidence_kind in ('compile','repair_regression'):
            compilation=row.get(evidence_kind,{})
            if compilation.get('status') not in ('PASS','FAIL'):
                continue
            if compilation.get('status') in ('PASS','FAIL'):
                if not args.evidence_root:
                    raise ValueError('Compile claim requires --evidence-root')
                root=args.evidence_root.resolve()
                for kind in ('artifact','log'):
                    evidence=(root/compilation[kind+'_file']).resolve()
                    if not evidence.is_relative_to(root) or hashlib.sha256(evidence.read_bytes()).hexdigest()!=compilation[kind+'_sha256']:
                        raise ValueError('Compile evidence missing, outside root, or hash mismatched')
    for result in summary['results']:
        path=args.run/result['response_file']
        if path.resolve().parent!=args.run.resolve() or digest(path.read_text())!=result['response_sha256']:
            raise ValueError('Response path or content changed')
    report=score(summary,adjudications,json.loads(args.cases.read_text()))
    args.output.write_text(json.dumps(report,indent=2)+'\n')
