#!/usr/bin/env python3
"""Connect policy recommendations to measured scale-only scene controls, fail closed."""
import argparse,hashlib,json
from pathlib import Path
from policy import QualityPolicy
ROOT=Path(__file__).resolve().parents[2]

def bind_report(report):
    paths={'source_sha256':'examples/precision/precision_lab.cpp','shared_renderer_sha256':'examples/scenes/scene_lab.cpp','comparator_sha256':'benchmarks/visual_quality/compare.py','thresholds_sha256':'benchmarks/visual_quality/thresholds.json','runner_sha256':'benchmarks/visual_quality/run.py'}
    if report.get('status')!='PASS':raise ValueError('visual suite not accepted')
    for key,path in paths.items():
        if report.get(key)!=hashlib.sha256((ROOT/path).read_bytes()).hexdigest():raise ValueError('visual evidence source changed: '+path)

def gate_scale(decision,scene,report):
    bind_report(report)
    if scene not in report['policy_level_visual_approval']:raise ValueError('unmeasured scene')
    level=decision['level']
    approved=level==0 or report['policy_level_visual_approval'][scene].get(str(level)) is True
    return {'scene':scene,'recommended_level':level,'scale_only_visual_pass':approved,
            'safe_scale_recommendation':decision['recommendation']['render_scale'] if approved else 1.0,
            'full_preset_may_apply':False,'reason':'scale-only host reference accepted; full preset/device evidence still required' if approved else 'reject measured visual regression; retain baseline',
            'physical_performance':'NOT_MEASURED'}

def main():
    p=argparse.ArgumentParser();p.add_argument('--visual-report',type=Path,default=ROOT/'benchmarks/visual_quality/software-validation.json');p.add_argument('--output',type=Path,required=True);a=p.parse_args();report=json.loads(a.visual_report.read_text());rows=[]
    for scene in sorted(report['policy_level_visual_approval']):
        for enabled in (False,True):
            policy=QualityPolicy()
            for t in range(25):decision=policy.step(dict(t_s=t,p95_ms=30,budget_ms=16.667,backend='software'),enabled=enabled)
            rows.append(dict(policy_enabled=enabled,decision=decision,visual_gate=gate_scale(decision,scene,report)))
    payload={'scope':'actual software scale-only comparisons combined with deterministic policy replay; not new device measurements','report_sha256':hashlib.sha256(a.visual_report.read_bytes()).hexdigest(),'decisions':rows}
    a.output.parent.mkdir(parents=True,exist_ok=True);a.output.write_text(json.dumps(payload,indent=2)+'\n')
if __name__=='__main__':main()
