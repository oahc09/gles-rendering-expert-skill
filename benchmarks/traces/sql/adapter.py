#!/usr/bin/env python3
"""Schema-probed SQL evidence; shares v1.0.4 metric schema/analyzer, never invents counters."""
import argparse
import bisect
import csv
import hashlib
import importlib.util
import io
import json
import math
from pathlib import Path
import sqlite3
import subprocess

HERE=Path(__file__).resolve().parent
QUERIES=json.loads((HERE/'templates/queries.json').read_text())
for query in QUERIES.values():
    query['sql']=(HERE/'templates'/query['file']).read_text().strip()
METRICS={'gpu_work':'gpu_ms','swap_wait':'swap_wait_ms','shader_compile':'shader_compile_ms','frame':'frame_ms','cpu_submit':'cpu_submit_ms','frequency':'clock_mhz','temperature':'temperature_c'}
spec=importlib.util.spec_from_file_location('legacy_trace_analysis',HERE.parent/'analyze.py')
legacy=importlib.util.module_from_spec(spec);spec.loader.exec_module(legacy)

def sha(path): return hashlib.sha256(path.read_bytes()).hexdigest()
class SqliteBackend:
    kind='NORMALIZED_SQLITE_FIXTURE'
    def __init__(self,path):
        self.connection=sqlite3.connect(path.resolve().as_uri()+'?mode=ro',uri=True)
        self.connection.row_factory=sqlite3.Row
        self.connection.set_progress_handler(self._budget,1000)
        self.steps=0
    def _budget(self):
        self.steps+=1
        return int(self.steps>10000)
    def query(self,sql):
        self.steps=0
        return [dict(row) for row in self.connection.execute(sql)]
    def close(self):self.connection.close()
class PerfettoBackend:
    kind='REAL_TRACE_PROCESSOR'
    def __init__(self,path,processor):self.path=path;self.processor=processor
    def query(self,sql):
        result=subprocess.run([self.processor,'query','--format','csv','--no-agent','--no-progress',str(self.path),sql],capture_output=True,text=True,timeout=90)
        if result.returncode:raise ValueError('Trace Processor failed: '+result.stderr[-1500:])
        rows=list(csv.DictReader(io.StringIO(result.stdout)))
        if rows and None in rows[0]:raise ValueError('Malformed Trace Processor CSV')
        return rows
    def close(self):pass

def number(value):
    if isinstance(value,bool):raise ValueError('Boolean sample')
    result=float(value)
    if not math.isfinite(result):raise ValueError('Nonfinite sample')
    return result

def inspect(backend,meta,raw,out):
    if not isinstance(meta,dict):raise ValueError('Metadata must be an object')
    report={'status':'UNKNOWN','provenance':meta.get('provenance'),'execution':backend.kind,'raw_trace_sha256':sha(raw),'raw_trace_bytes':raw.stat().st_size,
            'time_domain':meta.get('time_domain'),'metadata':meta,'schema':{},'queries':{},'observed':[], 'inferred':[],
            'not_measurable':['Private GPU bandwidth/GMEM percentages, watts and energy savings are not derived from these traces.'],'missing_fields':[], 'invalid':[]}
    required={'source','license','device','gpu','driver','backend','build','time_range','provenance','time_domain','capture_complete','raw_sha256'}
    if required-set(meta):raise ValueError('Missing metadata fields: '+','.join(sorted(required-set(meta))))
    if meta['raw_sha256']!=report['raw_trace_sha256']:raise ValueError('Trace hash mismatch')
    if meta['provenance'] not in ('synthetic','real-export') or not meta['license']:raise ValueError('Explicit license/provenance required')
    if backend.kind=='NORMALIZED_SQLITE_FIXTURE' and meta['provenance']!='synthetic':raise ValueError('SQLite fixtures cannot claim real trace provenance')
    if meta['time_domain']!='trace_processor_ns':raise ValueError('Unknown clock mapping; expected explicitly normalized trace_processor_ns')
    bounds=meta['time_range']
    if not isinstance(bounds,list) or len(bounds)!=2 or not all(math.isfinite(number(v)) for v in bounds) or number(bounds[0])>number(bounds[1]):raise ValueError('Invalid time range in ns')
    if meta['capture_complete'] is not True:raise ValueError('Capture incomplete/truncated or completeness unknown')
    report['schema_probe_sql']="SELECT name FROM sqlite_master WHERE type IN ('table','view')"
    tables=backend.query(report['schema_probe_sql'])
    names={r['name'] for r in tables}
    report['available_tables']=sorted(names)
    report['column_probe_sql']={}
    for table in sorted({t for q in QUERIES.values() for t in q['requires']}|{'stats'}):
        if table in names:
            report['column_probe_sql'][table]='PRAGMA table_info('+table+')'
            report['schema'][table]=[r['name'] for r in backend.query(report['column_probe_sql'][table])]
    if {'name','severity','value'}<=set(report['schema'].get('stats',[])):
        report['integrity_sql']="SELECT name,severity,value FROM stats WHERE value>0 AND (severity='error' OR name LIKE '%lost%' OR name LIKE '%overrun%' OR name LIKE '%parse_error%')"
        stats=backend.query(report['integrity_sql'])
        report['parser_stats']=stats
        if stats:raise ValueError('Trace parser reports loss/error: '+json.dumps(stats))
    elif backend.kind=='REAL_TRACE_PROCESSOR':raise ValueError('Parser integrity stats unavailable')
    all_records=[]
    for name,q in QUERIES.items():
        missing=[table+'.'+column for table,columns in q['requires'].items() for column in columns if column not in report['schema'].get(table,[])]
        entry={'sql':q['sql'],'sql_sha256':hashlib.sha256(q['sql'].encode()).hexdigest(),'meaning':q['meaning'],'missing':missing,'status':'UNKNOWN','rows':[]}
        report['queries'][name]=entry
        if missing:report['missing_fields']+=missing;continue
        rows=backend.query(q['sql']);entry['rows']=rows
        if not rows:entry['reason']='No matching samples';continue
        if len(rows)>10000:report['invalid'].append(name+': result truncated by row budget');continue
        invalid=False
        for row in rows:
            ts=number(row['ts']);end=ts
            if 'dur' in row:
                duration=number(row['dur']);end+=duration
                if duration<0:report['invalid'].append(name+': unfinished/negative slice');invalid=True
            if ts<number(bounds[0]) or end>number(bounds[1]):report['invalid'].append(name+': sample outside declared time domain');invalid=True
            if 'value' in row:
                value=number(row['value'])
                unit='MHz' if name=='frequency' else 'C'
                if row.get('unit')!=unit:report['invalid'].append(name+': unit unknown/mismatch');invalid=True
                if name=='frequency' and value<0:report['invalid'].append(name+': negative frequency');invalid=True
        if invalid:continue
        entry['status']='OBSERVED';report['observed'].append({'category':name,'classification':'observed','row_ids':[r['id'] for r in rows],'query':name})
        if name in METRICS:
            for row in rows:
                metric=METRICS[name];value=number(row['dur'])/1e6 if 'dur' in row else number(row['value'])
                all_records.append({'metric':metric,'value':value,'timestamp_ms':number(row['ts'])/1e6,'unit':legacy.UNITS[metric]})
    if report['invalid']:
        report['observed']=[];report['inferred']=[];return report
    if not report['observed']:report['invalid'].append('Empty/unusable trace');return report
    # Export the existing v1.0.4 metric contract, not a new diagnostic rule engine.
    out.mkdir(parents=True,exist_ok=True)
    metrics=out/'normalized-metrics.json';metrics.write_text(json.dumps(all_records,indent=2)+'\n')
    manifest={k:meta[k] for k in ('license','device','gpu','driver','backend','build','provenance')}
    manifest.update(source='synthetic-fixture' if meta['provenance']=='synthetic' else 'Perfetto',time_range=[number(x)/1e6 for x in bounds],aggregation='individual_samples',
                    metrics={row['metric']:{'unit':row['unit'],'sample_method':'SQL query evidence; inspect source track semantics'} for row in all_records},
                    raw_artifacts=[{'path':metrics.name,'sha256':sha(metrics),'format':'json'}],missing=report['missing_fields'])
    (out/'normalized-manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')
    if all_records:
        analysis=legacy.analyze(manifest,out)
        report['legacy_analysis']=analysis
        # Re-evaluate the SAME legacy thresholds on complete temporal windows, not
        # capture-wide means blessed by one unrelated overlapping sample. A window
        # spans at most 16.667ms (not +/-16.667ms). First qualifying witness only;
        # this is coarse triage, not a frame join or causal diagnosis.
        records=legacy.load_metrics(manifest,out)
        report['temporal_checks']={}
        accepted=[]
        for category,conditions in legacy.RULES.items():
            groups={metric:sorted((r for r in records if r['metric']==metric),key=lambda r:r['timestamp_ms']) for metric,_,_ in conditions}
            times={metric:[r['timestamp_ms'] for r in rows] for metric,rows in groups.items()}
            sums={}
            for metric,rows in groups.items():
                sums[metric]=[0.0]
                for row in rows:sums[metric].append(sums[metric][-1]+row['value'])
            check={'window_ms':16.667,'complete_windows_checked':0,'matched_window':None}
            report['temporal_checks'][category]=check
            if not all(groups.values()):continue
            anchors=sorted({r['timestamp_ms'] for rows in groups.values() for r in rows})
            for anchor in anchors:
                ranges={metric:(bisect.bisect_left(ts,anchor),bisect.bisect_right(ts,anchor+16.667)) for metric,ts in times.items()}
                if any(lo==hi for lo,hi in ranges.values()):continue
                check['complete_windows_checked']+=1
                means={metric:(sums[metric][hi]-sums[metric][lo])/(hi-lo) for metric,(lo,hi) in ranges.items()}
                if not all(means[metric]>threshold if op=='gt' else means[metric]<threshold for metric,op,threshold in conditions):continue
                evidence=[r for metric,(lo,hi) in ranges.items() for r in groups[metric][lo:hi]]
                matched={'start_ms':anchor,'end_ms':anchor+16.667,'means':means,'evidence':evidence}
                check['matched_window']=matched
                report['inferred'].append({'category':category,'classification':'inferred','confidence':'HYPOTHESIS_ONLY','experiment':legacy.AB[category],
                    'alignment_window_ms':16.667,'matched_window':matched,'caveat':'Thresholds re-evaluated only within this coarse timestamp window; not a causal conclusion.'})
                accepted.append({'category':category,'confidence':'HYPOTHESIS_ONLY','evidence':evidence,'ab_test':legacy.AB[category],
                    'matched_window':matched,'required_next':['time-aligned repeated samples','target-specific counter definitions','thermal/power state','visual correctness comparison']})
                break
            if check['matched_window'] is None:
                report['not_measurable'].append(category+': no complete time-aligned window satisfies every threshold; hypothesis withheld.')
        report['legacy_analysis']['hypotheses']=accepted
        report['legacy_analysis']['status']='HYPOTHESES' if accepted else 'INSUFFICIENT_EVIDENCE'
    report['status']='PARTIAL_EVIDENCE' if report['missing_fields'] else 'EVIDENCE_AVAILABLE'
    return report

def run(raw,meta,output,processor=None):
    backend=None
    try:
        backend=PerfettoBackend(raw,processor) if processor else SqliteBackend(raw)
        result=inspect(backend,meta,raw,output)
    except (ValueError,KeyError,TypeError,sqlite3.Error,OSError,subprocess.SubprocessError) as e:
        result={'status':'UNKNOWN','execution':'REAL_TRACE_PROCESSOR' if processor else 'NORMALIZED_SQLITE_FIXTURE',
                'raw_trace_sha256':sha(raw) if raw.is_file() else None,'invalid':[str(e)],'observed':[],'inferred':[],
                'not_measurable':['No root cause or performance win may be asserted from rejected evidence.']}
    finally:
        if backend:backend.close()
    output.mkdir(parents=True,exist_ok=True);(output/'evidence.json').write_text(json.dumps(result,indent=2)+'\n')
    lines=['# Trace SQL diagnosis','', 'Status: '+result['status'], '', '## Observed']
    lines += ['- '+r['category']+' (query '+r['query']+')' for r in result.get('observed',[])] or ['- UNKNOWN']
    lines += ['', '## Inferred hypotheses (not causes)']+[('- '+h['category']+': '+h['experiment']) for h in result.get('inferred',[])]
    lines += ['', '## Unknown / excluded claims']+['- '+x for x in result.get('invalid',[])+result.get('missing_fields',[])+result.get('not_measurable',[])]
    lines+=['','## Next experiment','Repeat matched workload with synchronized CPU/GPU/thermal capture and visual correctness; do not infer private counters or energy savings.']
    (output/'diagnosis.md').write_text('\n'.join(lines)+'\n');return result

def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('trace',type=Path);p.add_argument('--metadata',required=True,type=Path);p.add_argument('--output',required=True,type=Path);p.add_argument('--processor')
    a=p.parse_args()
    try:meta=json.loads(a.metadata.read_text())
    except (OSError,json.JSONDecodeError):meta={}
    result=run(a.trace,meta,a.output,a.processor)
    print(json.dumps({'status':result['status'],'output':str(a.output)}));return 2 if result['status']=='UNKNOWN' else 0
if __name__=='__main__':raise SystemExit(main())
