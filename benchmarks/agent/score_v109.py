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
