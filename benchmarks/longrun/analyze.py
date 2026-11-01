#!/usr/bin/env python3
"""LongRunCapture conservative sampled statistics and falsifiable hypotheses."""
import argparse,hashlib,json,math,statistics
from pathlib import Path
REQUIRED_DEVICE={'device','soc','gpu','driver','os','api','backend','refresh_hz','resolution','power_mode'}

def numeric(v,name,minimum=None):
    if isinstance(v,bool) or not isinstance(v,(int,float)) or not math.isfinite(v) or (minimum is not None and v<minimum):raise ValueError(name)
    return float(v)
def validate(d):
    if d.get('schema_version')!=1 or d.get('provenance') not in ('synthetic_fixture','host_workload_iterations','device_capture'):raise ValueError('schema/provenance')
    if not REQUIRED_DEVICE.issubset(d.get('device',{})):raise ValueError('device metadata')
    if d['device']['backend'] not in ('native_gles','angle','vulkan','software','unknown'):raise ValueError('backend')
    if d.get('clock')!='monotonic_ns':raise ValueError('clock must define monotonic domain')
    if d['provenance']=='device_capture':
        device=d['device']
        for field in ('device','soc','gpu','driver','os','api','power_mode'):
            if not isinstance(device.get(field),str) or not device[field].strip() or device[field].lower()=='unknown':raise ValueError('device capture missing '+field)
        numeric(device.get('refresh_hz'),'device refresh',.001)
        resolution=device.get('resolution')
        if not isinstance(resolution,list) or len(resolution)!=2 or any(type(x)is not int or x<=0 for x in resolution):raise ValueError('device resolution')
        if d.get('status')!='COMPLETE':raise ValueError('device capture not complete')
        actual=numeric(d.get('actual_wall_duration_s'),'actual wall duration',.001)
        requested=numeric(d.get('requested_duration_s'),'requested duration',.001)
        if actual<requested:raise ValueError('device capture shorter than requested')
        raw=d.get('raw_trace_sha256','')
        if len(raw)!=64 or any(x not in '0123456789abcdef' for x in raw):raise ValueError('device raw trace identity missing')

    h=d.get('scene_sha256','')
    if len(h)!=64 or any(c not in '0123456789abcdef' for c in h):raise ValueError('scene hash')
    if d.get('status')=='FAILED':raise ValueError('failed capture cannot be accepted')
    rows=d.get('samples');last=-1
    if not isinstance(rows,list) or not rows:raise ValueError('empty capture')
    for r in rows:
        t=numeric(r['t_s'],'timestamp',0)
        if t<=last:raise ValueError('nonmonotonic samples')
        last=t
        for name in ('frame_ms','budget_ms','iteration_ms','cpu_submit_ms','gpu_ms','gpu_hz','cpu_hz','power_mw','bandwidth_utilization','refresh_hz'):
            if r.get(name) is not None:numeric(r[name],name,0)
        if r.get('frame_ms') is not None and not r.get('budget_ms'):raise ValueError('frame requires positive budget')
        if r.get('bandwidth_utilization') is not None and r['bandwidth_utilization']>1:raise ValueError('bandwidth range')
        if r.get('temperature_c') is not None:numeric(r['temperature_c'],'temperature')
        if type(r.get('foreground')) is not bool:raise ValueError('foreground flag')
        if type(r.get('quality_level')) is not int or r['quality_level']<0:raise ValueError('quality level')
        if r.get('thermal_status') is not None and (type(r['thermal_status'])is not int or r['thermal_status'] not in range(7)):raise ValueError('thermal status')
    return rows

def percentile(values,p):
    v=sorted(values);i=(len(v)-1)*p;lo=int(i);hi=min(lo+1,len(v)-1);return v[lo]+(v[hi]-v[lo])*(i-lo)
def distribution(v):return {f'p{int(p*100)}':percentile(v,p) for p in (.5,.9,.95,.99)} if v else None
def pearson(x,y):
    if len(x)<3:return None
    mx=statistics.mean(x);my=statistics.mean(y);dx=[v-mx for v in x];dy=[v-my for v in y];den=math.sqrt(sum(v*v for v in dx)*sum(v*v for v in dy));return sum(a*b for a,b in zip(dx,dy))/den if den else None
def slope(rows):
    if len(rows)<2:return None
    x=[r['t_s']/60 for r in rows];y=[r['frame_ms'] for r in rows];mx=statistics.mean(x);den=sum((v-mx)**2 for v in x);return sum((a-mx)*(b-statistics.mean(y)) for a,b in zip(x,y))/den if den else None

def analyze(d, power_evidence=None):
    rows=validate(d);frames=[r for r in rows if r['foreground'] and r.get('frame_ms') is not None]
    result={'acquisition_status':d.get('status','not supplied by fixture'), 'measured_duration_complete':(d.get('actual_wall_duration_s',0)>=d.get('requested_duration_s',float('inf'))) if d.get('actual_wall_duration_s')is not None else None,'evidence_level':d['provenance'],'coverage':d.get('coverage','unspecified sampling coverage'),'sample_count':len(rows),'observed_duration_s':rows[-1]['t_s']-rows[0]['t_s'],'actual_wall_duration_s':d.get('actual_wall_duration_s'),
      'frame_ms_distribution':distribution([r['frame_ms'] for r in frames]),'iteration_ms_distribution':distribution([r['iteration_ms'] for r in rows if r.get('iteration_ms')is not None]),
      'sampled_jank_ratio':sum(r['frame_ms']>r['budget_ms'] for r in frames)/len(frames) if frames else None,'frame_slope_ms_per_min':slope(frames) if len({(r.get('refresh_hz'),r['quality_level']) for r in frames})==1 else None,
      'power_mw':None,'energy_saving_percent':None,'hypotheses':[],'status':'INSUFFICIENT_EVIDENCE','missing':[],'segments':[]}
    # Never combine a refresh/quality change into a within-configuration causal claim.
    segments=[]
    for r in rows:
        key=(r['foreground'],r.get('refresh_hz'),r['quality_level'])
        if not segments or segments[-1][0]!=key:segments.append((key,[]))
        segments[-1][1].append(r)
    for key,rs in segments:
        fs=[r for r in rs if r['foreground'] and r.get('frame_ms')is not None]
        segment={'frame_slope_ms_per_min':slope(fs),'foreground':key[0],'refresh_hz':key[1],'quality_level':key[2],'start_s':rs[0]['t_s'],'end_s':rs[-1]['t_s'],'sample_count':len(rs),'frame_ms':distribution([r['frame_ms'] for r in fs]),'hypotheses':[]}
        if len(fs)>=30:
            freq=[r for r in fs if r.get('gpu_hz')is not None];corr=pearson([r['gpu_hz'] for r in freq],[r['frame_ms'] for r in freq]);segment['frequency_frame_correlation']=corr
            hot=[r for r in fs if r.get('thermal_status') is not None and r['thermal_status']>=3]
            if hot and len(freq)>=30 and corr is not None and corr<-.7 and (slope(fs) or 0)>0:
                segment['hypotheses'].append('thermal_frequency_pressure')
            cpu=[r for r in fs if r.get('cpu_submit_ms') is not None and r.get('gpu_ms')is not None]
            if len(cpu)>=30 and statistics.mean(r['cpu_submit_ms']/max(r['frame_ms'],.001) for r in cpu)>.8 and statistics.mean(r['gpu_ms']/r['budget_ms'] for r in cpu)<.6:
                segment['hypotheses'].append('cpu_submission_pressure')
            bw=[r for r in fs if r.get('bandwidth_utilization') is not None and r.get('gpu_ms')is not None]
            if len(bw)>=30 and statistics.mean(r['bandwidth_utilization'] for r in bw)>.85 and statistics.mean(r['gpu_ms']/r['budget_ms'] for r in bw)>1.1:
                segment['hypotheses'].append('gpu_bandwidth_pressure')
        result['segments'].append(segment)
        result['hypotheses']+=segment['hypotheses']
    result['hypotheses']=sorted(set(result['hypotheses']))
    if result['hypotheses']:result['status']='INFERRED_HYPOTHESES_NOT_CAUSAL_PROOF'
    if d.get('status')=='RUNNING':
        result['status']='INCOMPLETE_CAPTURE';result['hypotheses']=[]
        for segment in result['segments']:segment['hypotheses']=[]
    if not frames:result['missing'].append('actual frame telemetry; iteration latency is not frame time')
    for field in ('thermal_status','gpu_hz','cpu_submit_ms','gpu_ms','bandwidth_utilization'):
        if not any(r.get(field)is not None for r in rows):result['missing'].append(field)
    source=d.get('power_source')
    if source and power_evidence and power_evidence.get('validated_raw_sha256')==source.get('raw_sha256') and source.get('kind')=='calibrated_instrument' and source.get('units')=='mW' and source.get('raw_sha256') and d['provenance']=='device_capture':
        power=[r['power_mw'] for r in rows if r.get('power_mw')is not None]
        if power:result['power_mw']={'mean':statistics.mean(power),'source':source}
    result['required_experiment']='Repeat controlled workload at matched resolution/quality/refresh and thermal state; inspect independent counters; retain null unmeasured power.'
    return result

def bind_power_artifact(d, path):
    source=d.get('power_source') or {}
    raw=Path(path).read_bytes();digest=hashlib.sha256(raw).hexdigest()
    if source.get('raw_sha256')!=digest or source.get('units')!='mW' or source.get('kind')!='calibrated_instrument':raise ValueError('power provenance/hash/units')
    raw_data=json.loads(raw)
    if not raw_data.get('instrument_id') or not raw_data.get('calibration_reference') or raw_data.get('units')!='mW':raise ValueError('instrument identity/calibration absent')
    measured={numeric(r['t_s'],'power timestamp',0):numeric(r['power_mw'],'power',0) for r in raw_data['samples']}
    if len(measured)!=len(raw_data['samples']):raise ValueError('duplicate power timestamps')
    supplied=[r for r in d['samples'] if r.get('power_mw')is not None]
    if not supplied or any(measured.get(r['t_s'])!=r['power_mw'] for r in supplied):raise ValueError('power values differ from raw artifact')
    return {'validated_raw_sha256':digest,'calibration_authenticity':'operator-supplied, not independently certified'}

def main():
    p=argparse.ArgumentParser();p.add_argument('input',type=Path);p.add_argument('--output',type=Path,required=True);p.add_argument('--power-file',type=Path);a=p.parse_args();d=json.loads(a.input.read_text());r=analyze(d,bind_power_artifact(d,a.power_file) if a.power_file else None);r['source_sha256']=hashlib.sha256(a.input.read_bytes()).hexdigest();a.output.parent.mkdir(parents=True,exist_ok=True);a.output.write_text(json.dumps(r,indent=2)+'\n')
if __name__=='__main__':main()
