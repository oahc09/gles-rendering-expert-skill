"""Offline paired-run protocol. Valid records are reviewable, not authenticated hardware evidence."""
import argparse, hashlib, json, math, statistics
from pathlib import Path
IDENTITY = ('model', 'gpu', 'driver', 'backend', 'api_version', 'os')
def validate(record, artifact_root):
    if record.get('schema_version') != 1: raise ValueError('schema_version')
    device = record.get('device', {})
    if any(not isinstance(device.get(k), str) or not device[k].strip() for k in IDENTITY): raise ValueError('device identity')
    if record.get('hardware_kind') != 'physical': raise ValueError('physical GPU required; software not performance evidence')
    if record.get('warmup_frames', 0) < 60: raise ValueError('warmup')
    if record.get('quality_pass') is not True: raise ValueError('quality gate')
    if not record.get('workload_id') or not record.get('baseline_sha') or not record.get('candidate_sha'): raise ValueError('fixed builds/workload')
    root = Path(artifact_root).resolve()
    artifact = record.get('trace', {})
    file = (root / artifact.get('path', '')).resolve()
    if not file.is_relative_to(root) or not file.is_file(): raise ValueError('trace path')
    if hashlib.sha256(file.read_bytes()).hexdigest() != artifact.get('sha256'): raise ValueError('trace hash')
    runs = record.get('runs', [])
    if len(runs) < 8 or len(runs) % 2: raise ValueError('four or more interleaved pairs required')
    temperatures=[]
    for i, run in enumerate(runs):
        if run.get('variant') != ('A' if i % 2 == 0 else 'B'): raise ValueError('interleaving')
        samples=run.get('gpu_ms', [])
        if len(samples)<30 or any(type(v) not in (float,int) or not math.isfinite(v) or v <= 0 for v in samples): raise ValueError('GPU timer samples')
        if run.get('timer_disjoint') is not False: raise ValueError('timer disjoint/unknown')
        if run.get('clock_domain') != 'gpu_elapsed': raise ValueError('clock domain')
        if run.get('thermal_state') != 'stable' or not run.get('frequency_state'): raise ValueError('thermal/frequency state')
        t=run.get('temperature_c')
        if type(t) not in (int,float) or not math.isfinite(t): raise ValueError('temperature')
        temperatures.append(t)
    if max(temperatures)-min(temperatures)>2: raise ValueError('thermal drift')
    return record

def summarize(record, artifact_root):
    validate(record,artifact_root)
    def stats(label):
        values=sorted(v for r in record['runs'] if r['variant']==label for v in r['gpu_ms'])
        return {'p50_ms':statistics.median(values), 'p95_ms':values[math.ceil(.95*len(values))-1], 'sample_count':len(values)}
    a,b=stats('A'),stats('B')
    deltas=[statistics.median(record['runs'][i]['gpu_ms'])-statistics.median(record['runs'][i+1]['gpu_ms']) for i in range(0,len(record['runs']),2)]
    return {'status':'PAIRED_CAPTURE_REVIEW_REQUIRED','device':record['device'],'A':a,'B':b,'paired_delta_ms':deltas,'release_acceptance':False,'generalization':'exact device/driver/backend only','limitation':'Record and hash validation do not authenticate a physical capture or independently prove improvement.'}
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('record',type=Path);p.add_argument('--artifact-root',type=Path,required=True);a=p.parse_args()
    try: print(json.dumps(summarize(json.loads(a.record.read_text()),a.artifact_root),indent=2))
    except (ValueError,KeyError,OSError,TypeError) as e: p.exit(2,str(e)+'\n')
