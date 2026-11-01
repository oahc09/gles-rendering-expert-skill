#!/usr/bin/env python3
"""Conservative analysis of licensed exported metrics; never reverse-engineers captures."""
import argparse
import csv
import hashlib
import json
import math
from pathlib import Path

UNITS = {'cpu_submit_ms':'ms','gpu_ms':'ms','frame_ms':'ms','fragment_busy_pct':'percent','tiler_busy_pct':'percent','bandwidth_pct_peak':'percent','sync_wait_ms':'ms','shader_compile_ms':'ms','temperature_c':'C','clock_mhz':'MHz','swap_wait_ms':'ms','vertex_count':'count'}
REQUIRED = {'source','license','device','gpu','driver','backend','build','time_range','aggregation','metrics','raw_artifacts','missing','provenance'}
RULES = {
 'cpu_submit_bound': [('cpu_submit_ms', 'gt', 8), ('gpu_ms', 'lt', 5)],
 'fragment_bound': [('fragment_busy_pct','gt',80), ('gpu_ms','gt',8)],
 'geometry_bound': [('tiler_busy_pct','gt',80), ('vertex_count','gt',100000)],
 'bandwidth_bound': [('bandwidth_pct_peak','gt',80), ('gpu_ms','gt',8)],
 'sync_stall': [('sync_wait_ms','gt',4), ('frame_ms','gt',16)],
 'shader_compile_hitch': [('shader_compile_ms','gt',8), ('frame_ms','gt',24)],
 'thermal_drift': [('temperature_c','gt',75), ('clock_mhz','lt',400)],
 'swap_backpressure': [('swap_wait_ms','gt',8), ('gpu_ms','lt',5)],
}
AB = {
 'cpu_submit_bound':'Keep pixels constant; batch draw submission and compare CPU submission distributions.',
 'fragment_bound':'Hold geometry fixed; halve covered pixel area or fragment ALU and compare GPU time.',
 'geometry_bound':'Hold pixel coverage fixed; reduce vertex/instance count and inspect tiler/vertex counters.',
 'bandwidth_bound':'Hold shading constant; reduce render-target byte traffic and compare memory counters.',
 'sync_stall':'Keep dependencies correct; replace broad wait with narrowly-scoped fence and compare wait traces.',
 'shader_compile_hitch':'Warm identical programs before replay; compare compile-event alignment with frame spikes.',
 'thermal_drift':'Repeat same seeded workload after cooling with fixed power mode; correlate clock/temperature over time.',
 'swap_backpressure':'Keep workload fixed; inspect compositor/frame pacing and swap queue with matched refresh rate.',
}

def finite(value):
    return type(value) in (int,float) and math.isfinite(value)

def safe_path(root, relative):
    p=(root/relative).resolve()
    if not p.is_relative_to(root.resolve()) or not p.is_file():
        raise ValueError('Artifact missing or outside capture directory')
    return p

def load_metrics(manifest, root):
    if REQUIRED-set(manifest): raise ValueError('Incomplete manifest')
    if manifest['source'] not in ('Perfetto','AGI','RenderDoc-export','Streamline','vendor-SDK','synthetic-fixture'):
        raise ValueError('Unsupported source; export documented CSV/JSON first')
    if not manifest['license']: raise ValueError('License/permission declaration required')
    if manifest['provenance'] not in ('synthetic','real-export'): raise ValueError('Explicit provenance required')
    if manifest['source']=='synthetic-fixture' and manifest['provenance']!='synthetic': raise ValueError('Synthetic source cannot be real evidence')
    if not isinstance(manifest['time_range'],list) or len(manifest['time_range'])!=2 or not all(finite(x) for x in manifest['time_range']) or manifest['time_range'][0]>manifest['time_range'][1]:
        raise ValueError('Invalid timestamp range')
    if manifest['aggregation'] not in ('individual_samples','mean','p50','p95'): raise ValueError('Unknown aggregation')
    records=[]
    if not manifest['raw_artifacts']: raise ValueError('Raw export is required')
    for artifact in manifest['raw_artifacts']:
        p=safe_path(root,artifact['path'])
        if hashlib.sha256(p.read_bytes()).hexdigest()!=artifact['sha256']: raise ValueError('Raw artifact hash mismatch')
        if artifact['format']=='json': rows=json.loads(p.read_text())
        elif artifact['format']=='csv':
            with p.open(newline='') as stream: rows=list(csv.DictReader(stream))
        else: raise ValueError('Unsupported binary capture; provide licensed CSV/JSON export')
        if not isinstance(rows,list): raise ValueError('Records must be a list')
        for index,row in enumerate(rows):
            value=float(row['value']); timestamp=float(row['timestamp_ms'])
            if not finite(value) or not finite(timestamp) or not manifest['time_range'][0]<=timestamp<=manifest['time_range'][1]: raise ValueError('Invalid sample value/time')
            if value<0 and row['metric']!='temperature_c': raise ValueError('Negative timing/counter value')
            name=row['metric']; definition=manifest['metrics'].get(name)
            if name not in UNITS or not definition or row['unit']!=UNITS[name] or definition['unit']!=UNITS[name] or not definition.get('sample_method'):
                raise ValueError('Metric unit/method missing or incompatible')
            if (name.endswith('_pct') or name=='bandwidth_pct_peak') and not 0<=value<=100: raise ValueError('Invalid percentage')
            records.append({'metric':name,'value':value,'timestamp_ms':timestamp,'artifact':artifact['path'],'row':index+1,'sha256':artifact['sha256']})
    return records

def analyze(manifest, root):
    records=load_metrics(manifest,root)
    grouped={name:[r for r in records if r['metric']==name] for name in UNITS}
    values={name:sum(r['value'] for r in rows)/len(rows) for name,rows in grouped.items() if rows}
    # Thresholds are triage hypotheses, not vendor-normalized bottleneck classifiers.
    hypotheses=[]
    for kind, conditions in RULES.items():
        missing=[name for name,_,_ in conditions if name not in values]
        match=not missing and all((values[name]>threshold if op=='gt' else values[name]<threshold) for name,op,threshold in conditions)
        if match:
            hypotheses.append({'category':kind,'confidence':'HYPOTHESIS_ONLY','evidence':[r for name,_,_ in conditions for r in grouped[name]],'ab_test':AB[kind],
                'counterfactual':'Reject this hypothesis if the matched A/B keeps correctness but fails to reduce the implicated cost.',
                'required_next':['time-aligned repeated samples','target-specific counter definitions','thermal/power state','visual correctness comparison']})
    return {'status':'HYPOTHESES' if hypotheses else 'INSUFFICIENT_EVIDENCE','provenance':manifest['provenance'],'source':manifest['source'],
        'manifest_device':{k:manifest[k] for k in ('device','gpu','driver','backend','build')},'aggregation':manifest['aggregation'],
        'hypotheses':hypotheses,'missing_metrics':sorted(set(UNITS)-set(values)), 'declared_missing':manifest['missing'],
        'performance_improvement':'NOT_MEASURED','limitations':['No causal conclusion from one trace.','Thresholds are configurable triage assumptions, not universal GPU limits.','Means of aggregates are descriptive only; do not infer p95 from p50 exports.']}

def main():
    p=argparse.ArgumentParser();p.add_argument('manifest',type=Path);p.add_argument('--output',type=Path,required=True);a=p.parse_args()
    try: result=analyze(json.loads(a.manifest.read_text()),a.manifest.parent);code=0
    except (ValueError,KeyError,TypeError,OSError,json.JSONDecodeError) as e: result={'status':'INVALID_OR_UNSUPPORTED','error':str(e)};code=2
    a.output.parent.mkdir(parents=True,exist_ok=True);a.output.write_text(json.dumps(result,indent=2)+'\n');print(json.dumps({'status':result['status'],'output':str(a.output)}));return code
if __name__=='__main__':raise SystemExit(main())
