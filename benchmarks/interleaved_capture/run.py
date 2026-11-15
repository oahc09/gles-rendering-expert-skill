#!/usr/bin/env python3
"""Fixed-function interleaved software GLES coordinator, not physical capture."""
import argparse,hashlib,importlib.util,json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
spec=importlib.util.spec_from_file_location('capture_pairs',ROOT/'benchmarks/shader_ab/optimization_pairs.py');pairs=importlib.util.module_from_spec(spec);spec.loader.exec_module(pairs)
def sha(data):return hashlib.sha256(data).hexdigest()
def golden(family):return pairs.texture_pixels('ramp') if family=='sampling' else pairs.pure_golden(1)
def source_hashes(family,arm):
 return dict(vertex=sha(pairs.VERT.encode()),fragment=sha(pairs.fragment(family,arm).encode()),compute=sha(pairs.COMPUTE.encode()) if family=='fusion' and arm=='baseline' else None)
def judge(track):
 family=track['family'];negative=track['candidate']=='negative'
 if family not in ('sampling','fusion') or track['candidate'] not in ('optimized','negative'):raise ValueError('unregistered experiment')
 gold=golden(family);runs=track['runs']
 if track['cpu_golden']!=gold or track['input']!=('ramp' if family=='sampling' else 1):raise ValueError('workload/golden mismatch')
 if len(runs)!=8:raise ValueError('four interleaved pairs required')
 quality=[]
 for index,row in enumerate(runs):
  variant='A' if index%2==0 else 'B';arm='baseline' if variant=='A' else track['candidate']
  if row['order']!=index or row['variant']!=variant or row['source_hashes']!=source_hashes(family,arm):raise ValueError('order/source mismatch')
  if row['gpu_ms'] is not None or row['clock_domain']!='NOT_MEASURED':raise ValueError('unexpected timing claim')
  if len(row['samples'])!=3:raise ValueError('sample count')
  for sample_index,sample in enumerate(row['samples']):
   if sample['index']!=sample_index:raise ValueError('sample order')
   if sample['status']!='EXECUTED':raise ValueError('execution failure')
   result=pairs.compare(sample['pixels'],gold)
   if result['status']=='INVALID' or result!=sample['cpu_quality']:raise ValueError('quality evidence mismatch')
   quality.append((variant,result['status']))
 if any(q!='PASS' for variant,q in quality if variant=='A'):raise ValueError('baseline quality failure')
 candidate_pass=all(q=='PASS' for variant,q in quality if variant=='B')
 return dict(harness_status='HOST_PASS' if all(q==('FAIL' if negative else 'PASS') for variant,q in quality if variant=='B') else 'FAIL',quality_pass=candidate_pass,optimization_status='INSUFFICIENT_EVIDENCE' if candidate_pass else 'REJECTED_BY_QUALITY',performance_acceptance=False,physical_protocol_eligible=False)

def run(config,output):
 h=pairs.Host(config);tracks=[]
 try:
  for family in ('sampling','fusion'):
   input_='ramp' if family=='sampling' else 1
   for candidate in ('optimized','negative'):
    track=dict(family=family,input=input_,candidate=candidate,cpu_golden=golden(family),warmup=[],runs=[])
    # Warmup is correctness infrastructure only, not physical protocol's60frames.
    for arm in ('baseline',candidate):
     d=h.draw(family,arm,input_)
     if d['status']!='EXECUTED':raise RuntimeError('unsupported or failed warmup')
     track['warmup'].append(dict(arm=arm,source_hashes=source_hashes(family,arm),cpu_quality=pairs.compare(d['pixels'],golden(family))))
    for index in range(8):
     arm='baseline' if index%2==0 else candidate;samples=[]
     for n in range(3):
      d=h.draw(family,arm,input_)
      if d['status']!='EXECUTED':raise RuntimeError('unsupported or failed run')
      samples.append(dict(index=n,status=d['status'],pixels=d['pixels'],cpu_quality=pairs.compare(d['pixels'],golden(family))))
     track['runs'].append(dict(order=index,variant='A' if index%2==0 else 'B',source_hashes=source_hashes(family,arm),samples=samples,gpu_ms=None,clock_domain='NOT_MEASURED'))
    track['decision']=judge(track);tracks.append(track)
 finally:h.close()
 report=dict(status='HOST_PASS' if all(t['decision']['harness_status']=='HOST_PASS' for t in tracks) else 'FAIL',schema_version=1,hardware_kind='software',performance_status='NOT_MEASURED',gpu_timer_status='NOT_COLLECTED',physical_gpu='BLOCKED_BY_HARDWARE',tracks=tracks,coordinator_sha256=sha(Path(__file__).read_bytes()),experiment_source_sha256=sha((ROOT/'benchmarks/shader_ab/optimization_pairs.py').read_bytes()),scope='Four fixed paired experiments, ABABABAB order,3 draw/readback samples each arm-run,2 warmup draws per track. No CPU time used as GPU timing; not device_portability physical capture schema.')
 out=Path(output);out.parent.mkdir(parents=True,exist_ok=True);out.write_text(json.dumps(report,indent=2)+'\n');return report
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--config',required=True);p.add_argument('--output',required=True);a=p.parse_args();r=run(json.loads(Path(a.config).read_text()),a.output);print(r['status']);raise SystemExit(r['status']!='HOST_PASS')
