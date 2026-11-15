"""Extend existing independent paired scoring; never manufacture provider evidence."""
import hashlib
from pathlib import Path
from score import score as base_score

METRICS=('diagnosis_correct','false_positive','compile_pass','run_pass','quality_pass','measured_improvement','unsupported_gain_claim')


def score(summary, reviews, cases, evidence_root=None):
    base=base_score(summary,reviews,cases)
    if any(c.get('v109') for c in cases['cases']):
        ids={c['case_id'] for c in cases['cases'] if c.get('v109')}
        groups={}
        for row in reviews:
            if row['case_id'] not in ids: continue
            data=row.get('v109_metrics',{})
            group=groups.setdefault(row['condition'],{k:{'positive':0,'reviewed':0,'ratio':None} for k in METRICS})
            for metric in METRICS:
                value=data.get(metric)
                if value is not None and type(value) is not bool:
                    raise ValueError('v109 metric must be boolean or null')
                if value is None: continue
                if metric in ('compile_pass','run_pass','quality_pass','measured_improvement'):
                    evidence=row.get('v109_evidence',{}).get(metric,{})
                    if not all(evidence.get(k) for k in ('artifact_sha256','log_sha256','command','environment')):
                        raise ValueError('Execution/quality/performance requires raw evidence identity')
                    if evidence_root is None:
                        raise ValueError('Evidence root required; declared hashes alone are not evidence')
                    root=Path(evidence_root).resolve()
                    for kind in ('artifact','log') + (('raw_trace',) if metric=='measured_improvement' else ()):
                        path=(root/evidence.get(kind+'_file','')).resolve()
                        if not path.is_relative_to(root) or not path.is_file() or hashlib.sha256(path.read_bytes()).hexdigest()!=evidence.get(kind+'_sha256'):
                            raise ValueError('Missing, escaped or hash-mismatched evidence')
                    if metric=='measured_improvement' and not all(evidence.get(k) for k in ('device','driver','raw_trace_sha256','thermal_state','interleaved_rounds')):
                        raise ValueError('Physical device comparison evidence required')
                    if metric=='measured_improvement' and (evidence.get('execution_class')!='PHYSICAL_DEVICE' or type(evidence['interleaved_rounds']) is not int or evidence['interleaved_rounds']<2):
                        raise ValueError('Software or single-shot evidence cannot establish device gain')
                group[metric]['reviewed']+=1; group[metric]['positive']+=int(value)
        for group in groups.values():
            for m in group.values(): m['ratio']=m['positive']/m['reviewed'] if m['reviewed'] else None
        base['v109_metrics']=groups
    return base


def score_files(run_dir, adjudications_file, cases_file, evidence_root=None):
    """CLI boundary checks captured corpus/responses and all old/new evidence paths."""
    import json
    from run import digest
    root=Path(run_dir).resolve(); cases_path=Path(cases_file)
    summary=json.loads((root/'summary.json').read_text())
    if digest(cases_path.read_text())!=summary.get('case_source_sha256'):
        raise ValueError('Corpus changed since response capture')
    reviews=json.loads(Path(adjudications_file).read_text())
    if not isinstance(reviews,list):raise ValueError('Reviews must be an array')
    for result in summary['results']:
        path=(root/result['response_file']).resolve()
        if path.parent!=root or not path.is_file() or digest(path.read_text())!=result['response_sha256']:
            raise ValueError('Response path or content changed')
    for row in reviews:
        for key in ('compile','repair_regression','baseline_regression','first_run','numeric','visual'):
            record=row.get(key,{})
            if record.get('status') not in ('PASS','FAIL'):continue
            if evidence_root is None:raise ValueError('Execution evidence root required')
            base=Path(evidence_root).resolve()
            for kind in ('artifact','log'):
                p=(base/record[kind+'_file']).resolve()
                if not p.is_relative_to(base) or not p.is_file() or hashlib.sha256(p.read_bytes()).hexdigest()!=record[kind+'_sha256']:
                    raise ValueError('Missing, escaped or hash-mismatched execution evidence')
    report=score(summary,reviews,json.loads(cases_path.read_text()),evidence_root)
    if summary.get('status')=='BLOCKED_BY_PROVIDER' and not summary['results'] and not reviews:
        report['status']='BLOCKED_BY_PROVIDER'
        report['v109_metrics']={condition:{m:{'positive':0,'reviewed':0,'ratio':None} for m in METRICS} for condition in ('no_skill','with_skill')}
    return report


def main():
    import argparse,json
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--run',type=Path,required=True);p.add_argument('--adjudications',type=Path,required=True)
    p.add_argument('--cases',type=Path,default=Path(__file__).with_name('cases-v1.0.9.json'))
    p.add_argument('--evidence-root',type=Path);p.add_argument('--output',type=Path,required=True);a=p.parse_args()
    report=score_files(a.run,a.adjudications,a.cases,a.evidence_root)
    a.output.parent.mkdir(parents=True,exist_ok=True);a.output.write_text(json.dumps(report,indent=2)+'\n')
    return 2 if report['status']=='BLOCKED_BY_PROVIDER' else 0

if __name__=='__main__':raise SystemExit(main())
