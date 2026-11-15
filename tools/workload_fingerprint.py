#!/usr/bin/env python3
"""Deterministic workload triage. Labels are hypotheses, not causal findings.
Existing exported traces are validated by benchmarks/traces/analyze.py before
adaptation; this standalone contract never treats utilization alone as a cause.
"""
import argparse
import json
import math
from pathlib import Path

LABELS = ('CPU_SUBMIT','BANDWIDTH','FRAGMENT_ALU','OVERDRAW_BLEND','VERTEX_GEOMETRY','COMPUTE','SYNC','UPLOAD','THERMAL','UNKNOWN')
RULES = {
 'CPU_SUBMIT': [('cpu_submit_ms',8),('draw_count',500)],
 'BANDWIDTH': [('bandwidth_pct_peak',80),('gpu_ms',8)],
 'FRAGMENT_ALU': [('fragment_alu_pct',80),('gpu_ms',8)],
 'OVERDRAW_BLEND': [('blend_layers',4),('coverage_ratio',2)],
 'VERTEX_GEOMETRY': [('vertex_busy_pct',80),('vertex_count',100000)],
 'COMPUTE': [('compute_ms',8),('dispatch_count',0)],
 'SYNC': [('sync_wait_ms',4),('frame_p95_ms',16)],
 'UPLOAD': [('upload_ms',4),('upload_bytes',0)],
 'THERMAL': [('temperature_c',75),('clock_drop_pct',20)],
}
UNITS = {k: ('ms' if k.endswith('_ms') else 'percent' if k.endswith('_pct') or k=='bandwidth_pct_peak' else 'bytes' if k.endswith('_bytes') else 'C' if k=='temperature_c' else 'ratio' if k=='coverage_ratio' else 'count') for pairs in RULES.values() for k,_ in pairs}
UNITS.update({'gpu_utilization_pct':'percent','texture_read_bytes':'bytes','texture_write_bytes':'bytes','resource_bytes':'bytes','fbo_switches':'count'})

def number(value, name, minimum=0):
    if type(value) not in (int,float) or not math.isfinite(value) or value<minimum:
        raise ValueError(f'{name}: finite number >= {minimum} required')
    return value

def fingerprint(data):
    if data.get('provenance') not in ('synthetic','real-export') or not data.get('workload_id'):
        raise ValueError('workload_id and explicit provenance required')
    resolution=data.get('resolution')
    if not isinstance(resolution,list) or len(resolution)!=2 or any(type(x)!=int or not 0<x<=65536 for x in resolution):
        raise ValueError('resolution must be two positive bounded integers')
    times=data.get('frame_times_ms',[])
    if not isinstance(times,list): raise ValueError('frame_times_ms must be array')
    for value in times: number(value,'frame_times_ms')
    metrics=data.get('metrics',{}); values={}
    for name, metric in metrics.items():
        if name not in UNITS: raise ValueError('unknown metric '+name)
        if metric is None: continue
        if not isinstance(metric,dict) or metric.get('unit')!=UNITS[name]: raise ValueError('unit mismatch '+name)
        value=number(metric.get('value'),name,-273.15 if name=='temperature_c' else 0)
        if UNITS[name]=='percent' and value>100: raise ValueError('percentage exceeds 100')
        if type(metric.get('sample_count'))!=int or metric['sample_count']<1 or not metric.get('tool') or not metric.get('raw_trace'):
            raise ValueError('sample_count/tool/raw_trace required')
        values[name]=value
    intervals=data.get('intervals',[]); overlap=None; interval_warning=[]
    checked=[]
    for item in intervals:
        if item.get('stage') not in ('cpu','gpu') or not item.get('clock'): raise ValueError('interval stage/clock required')
        start=number(item.get('start_ms'),'start'); end=number(item.get('end_ms'),'end')
        if end<start: raise ValueError('negative interval')
        checked.append(item)
    cpu=[x for x in checked if x['stage']=='cpu']; gpu=[x for x in checked if x['stage']=='gpu']
    if cpu and gpu:
        if len({x['clock'] for x in checked})!=1: interval_warning=['CLOCK_DOMAIN_MISMATCH']; overlap=None
        else:
            # Union intersections so overlapping ranges cannot double-count.
            intersections=sorted((max(a['start_ms'],b['start_ms']),min(a['end_ms'],b['end_ms'])) for a in cpu for b in gpu if max(a['start_ms'],b['start_ms'])<min(a['end_ms'],b['end_ms']))
            merged=[]
            for start,end in intersections:
                if merged and start<=merged[-1][1]: merged[-1][1]=max(end,merged[-1][1])
                else: merged.append([start,end])
            overlap=sum(b-a for a,b in merged)
    hypotheses=[]
    for label,pairs in RULES.items():
        if all(name in values and values[name]>limit for name,limit in pairs):
            hypotheses.append({'label':label,'confidence':'HYPOTHESIS_ONLY','evidence_keys':[name for name,_ in pairs]})
    missing=sorted(set(name for pairs in RULES.values() for name,_ in pairs)-values.keys())
    return {'schema_version':'1.0','workload_id':data['workload_id'],'provenance':data['provenance'],
            'labels':[x['label'] for x in hypotheses] or ['UNKNOWN'],'hypotheses':hypotheses,
            'missing_metrics':missing,'next_collection':missing or ['controlled interleaved A/B and visual oracle'],
            'cpu_gpu_overlap_ms':overlap,'warnings':interval_warning,
            'performance_improvement':'NOT_MEASURED','input':data}

def main():
    p=argparse.ArgumentParser();p.add_argument('input',type=Path);p.add_argument('--output',type=Path);a=p.parse_args()
    try: result=fingerprint(json.loads(a.input.read_text())); code=0
    except (ValueError,TypeError,KeyError) as e: result={'status':'INVALID','error':str(e)};code=2
    out=json.dumps(result,indent=2,allow_nan=False)+'\n'
    if a.output: a.output.write_text(out)
    else: print(out,end='')
    return code
if __name__=='__main__': raise SystemExit(main())
