#!/usr/bin/env python3
"""Deterministic workload triage. Labels are hypotheses, not causal findings.
Existing exported traces are validated by benchmarks/traces/analyze.py before
adaptation; this standalone contract never treats utilization alone as a cause.
"""
import argparse
import hashlib
import re
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

def frame_distribution(times):
    """Nearest-rank empirical quantiles, not a latency confidence interval."""
    ordered=sorted(number(x,'frame_times_ms') for x in times)
    n=len(ordered)
    return {'sample_count':n,'unit':'ms','method':'nearest-rank',
            'min':ordered[0] if n else None,'max':ordered[-1] if n else None,
            'p50':ordered[math.ceil(.50*n)-1] if n else None,
            'p95':ordered[math.ceil(.95*n)-1] if n else None,
            'p99':ordered[math.ceil(.99*n)-1] if n else None,
            'mean':math.fsum(x/n for x in ordered) if n else None,
            'measurement_scope':'supplied frame samples, not GPU duration'}

def frame_source(data, times, root):
    """Bind supplied real frame samples to an archived export, not its authenticity."""
    if data['provenance'] != 'real-export' or not times:
        return {'status':'SYNTHETIC' if data['provenance']=='synthetic' else 'NO_SAMPLES'}
    source=data.get('frame_source')
    if not isinstance(source,dict): raise ValueError('real-export frame_source required')
    for field in ('tool','clock_domain','raw_trace','sha256'):
        if not isinstance(source.get(field),str) or not source[field].strip():
            raise ValueError('frame_source '+field+' required')
    if type(source.get('sample_count')) is not int or source['sample_count']!=len(times):
        raise ValueError('frame_source sample_count mismatch')
    if not re.fullmatch('[0-9a-f]{64}',source['sha256']):raise ValueError('frame_source sha256 invalid')
    root=Path(root).resolve(); relative=Path(source['raw_trace'])
    path=(root/relative).resolve()
    if relative.is_absolute() or not path.is_relative_to(root) or not path.is_file():
        raise ValueError('frame_source must reference an existing relative export')
    raw=path.read_bytes()
    if hashlib.sha256(raw).hexdigest()!=source['sha256']:raise ValueError('frame_source hash mismatch')
    try: payload=json.loads(raw)
    except (ValueError,UnicodeError):raise ValueError('frame_source must be JSON export')
    if not isinstance(payload,dict) or not isinstance(payload.get('frame_times_ms'),list):
        raise ValueError('frame_source JSON frame_times_ms array required')
    for value in payload['frame_times_ms']:number(value,'export frame_times_ms')
    expected={'workload_id':data['workload_id'],'unit':'ms','frame_times_ms':times,
              'tool':source['tool'],'clock_domain':source['clock_domain']}
    if not isinstance(payload,dict) or any(payload.get(k)!=v for k,v in expected.items()):
        raise ValueError('frame_source does not bind declared samples/tool/clock/workload')
    return {'status':'HASH_BOUND_EXPORT','authenticity':'NOT_AUTHENTICATED','sample_count':len(times)}


def fingerprint(data, root=Path('.')):
    if data.get('provenance') not in ('synthetic','real-export') or not data.get('workload_id'):
        raise ValueError('workload_id and explicit provenance required')
    if not isinstance(data['workload_id'],str) or not data['workload_id'].strip():
        raise ValueError('workload_id must be nonempty string')
    if 'sampling_formats' in data and (not isinstance(data['sampling_formats'],list) or
        any(not isinstance(x,str) or not x.strip() for x in data['sampling_formats'])):
        raise ValueError('sampling_formats must be array of nonempty strings')
    if 'thermal_state' in data and (not isinstance(data['thermal_state'],str) or not data['thermal_state'].strip()):
        raise ValueError('thermal_state must be nonempty string')
    if 'trace_available' in data and type(data['trace_available']) is not bool:
        raise ValueError('trace_available must be boolean')
    resolution=data.get('resolution')
    if not isinstance(resolution,list) or len(resolution)!=2 or any(type(x)!=int or not 0<x<=65536 for x in resolution):
        raise ValueError('resolution must be two positive bounded integers')
    times=data.get('frame_times_ms',[])
    if not isinstance(times,list): raise ValueError('frame_times_ms must be array')
    for value in times: number(value,'frame_times_ms')
    source=frame_source(data,times,root)
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
            'frame_time_distribution':frame_distribution(times),'frame_source_validation':source,
            'performance_improvement':'NOT_MEASURED','input':data}

def main():
    p=argparse.ArgumentParser();p.add_argument('input',type=Path);p.add_argument('--output',type=Path);a=p.parse_args()
    try: result=fingerprint(json.loads(a.input.read_text()),a.input.parent); code=0
    except (ValueError,TypeError,KeyError,OSError) as e: result={'status':'INVALID','error':str(e)};code=2
    out=json.dumps(result,indent=2,allow_nan=False)+'\n'
    if a.output: a.output.write_text(out)
    else: print(out,end='')
    return code
if __name__=='__main__': raise SystemExit(main())
