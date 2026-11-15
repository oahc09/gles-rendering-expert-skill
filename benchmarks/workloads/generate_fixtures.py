"""Regenerate explicitly synthetic decision-contract fixtures (not model/GPU scores)."""
import copy,json,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2];sys.path.insert(0,str(ROOT/'tools'))
from workload_fingerprint import RULES,UNITS
from estimate_gpu_cost import estimate

def save(path,data): (ROOT/path).write_text(json.dumps(data,indent=2)+'\n')
base={'workload_id':'unknown','provenance':'synthetic','resolution':[1920,1080],'metrics':{},'sampling_formats':['RGBA8'],'thermal_state':'UNKNOWN','trace_available':False,'frame_times_ms':[]}
samples=[]
for label,pairs in RULES.items():
 d=copy.deepcopy(base);d['workload_id']=label.lower();d['metrics']={k:{'value':v+1,'unit':UNITS[k],'tool':'synthetic-generator','raw_trace':'synthetic-fixture','sample_count':10} for k,v in pairs}
 samples.append({'workload_id':d['workload_id'],'input':d,'expected_labels':[label]})
for name,metrics in [('missing',{}),('utilization-only',{'gpu_utilization_pct':99}),('one-low-counter',{'gpu_ms':3})]:
 d=copy.deepcopy(base);d['workload_id']=name;d['metrics']={k:{'value':v,'unit':UNITS[k],'tool':'synthetic-generator','raw_trace':'synthetic-fixture','sample_count':10} for k,v in metrics.items()};samples.append({'workload_id':name,'input':d,'expected_labels':['UNKNOWN']})
save(Path('benchmarks/workloads/samples.json'),samples)
a={'id':'a','format':'RGBA8','width':10,'height':10,'samples':1,'passes':1,'clear':False,'invalidate':False,'resolve':False,'external_consumer':False}
cases=[]
variants=[('base',{}),('clear',{'clear':True}),('invalidate',{'invalidate':True}),('both',{'clear':True,'invalidate':True}),('msaa',{'samples':4}),('resolve',{'samples':4,'resolve':True}),('multipass',{'passes':3}),('half-float',{'format':'RGBA16F'}),('unknown-format',{'format':'ASTC'}),('invalid-consumer',{'invalidate':True,'external_consumer':True}),('zero-width',{'width':0}),('bad-samples',{'samples':3}),('negative-passes',{'passes':-1})]
for name,change in variants:
 d={'attachments':[dict(a,**change)]};c={'id':name,'provenance':'synthetic','input':d}
 try:c['expected_upper']=estimate(d)['logical_upper_bytes']
 except ValueError:c['invalid']=True
 cases.append(c)
save(Path('benchmarks/gpu_cost/cases.json'),cases)
c={'id':'candidate','experiment':'shader_ab/synthetic','fallback':'baseline','capability_supported':True,'quality':{'pass':True,'golden_id':'fixture','thresholds':{'max_error':1}}}
m={'device':'FIXTURE_NOT_HARDWARE','gpu':'FIXTURE','driver':'FIXTURE','backend':'GLES3','build_sha':'a'*40,'baseline_sha':'b'*40,'thermal_state':'stable','frequency_state':'fixed','tool':'fixture','clock_domain':'mono','provenance':'physical-device','unit':'ms','thermal_stable':True,'warmup_frames':60,'artifacts':[{'path':'trace.json','kind':'paired-timing-json','sha256':'FIXTURE_HASH'}],'pairs':[{'order':'AB' if i%2==0 else 'BA','baseline_ms':10,'candidate_ms':8} for i in range(6)]}
cases=[]
def add(name,change,expected,measurement=True):
 d=copy.deepcopy(c)
 if measurement:d['measurement']=copy.deepcopy(m)
 change(d);cases.append({'id':name,'provenance':'synthetic-contract-test','candidate':d,'expected':expected})
add('improvement-needs-review',lambda d:None,'INSUFFICIENT_EVIDENCE')
add('regression',lambda d:[p.update(candidate_ms=12) for p in d['measurement']['pairs']],'INSUFFICIENT_EVIDENCE')
add('no-gain',lambda d:[p.update(candidate_ms=10) for p in d['measurement']['pairs']],'INSUFFICIENT_EVIDENCE')
add('noise',lambda d:d['measurement']['pairs'][0].update(candidate_ms=12),'INSUFFICIENT_EVIDENCE')
add('quality-fail',lambda d:d['quality'].update(pass_=False),'INSUFFICIENT_EVIDENCE') if False else None
add('quality-fail',lambda d:d.update(quality={'pass':False}),'REJECTED_BY_QUALITY')
add('unmeasured',lambda d:None,'RECOMMENDED_FOR_EXPERIMENT',False)
for field in ['device','gpu','driver','backend','build_sha','baseline_sha','thermal_state','frequency_state','tool','clock_domain','artifacts']:
 add('missing-'+field,lambda d,k=field:d['measurement'].pop(k),'INSUFFICIENT_EVIDENCE')
add('software',lambda d:d['measurement'].update(provenance='software'),'INSUFFICIENT_EVIDENCE')
add('unstable',lambda d:d['measurement'].update(thermal_stable=False),'INSUFFICIENT_EVIDENCE')
add('cold',lambda d:d['measurement'].update(warmup_frames=0),'INSUFFICIENT_EVIDENCE')
add('single-pair',lambda d:d['measurement'].update(pairs=d['measurement']['pairs'][:1]),'INSUFFICIENT_EVIDENCE')
add('unbalanced',lambda d:d['measurement']['pairs'][1].update(order='AB'),'INSUFFICIENT_EVIDENCE')
add('wrong-hash',lambda d:d['measurement']['artifacts'][0].update(sha256='0'*64),'INSUFFICIENT_EVIDENCE')
add('missing-experiment',lambda d:d.pop('experiment'),'INSUFFICIENT_EVIDENCE')
add('missing-fallback',lambda d:d.pop('fallback'),'INSUFFICIENT_EVIDENCE')
add('unknown-capability',lambda d:d.update(capability_supported=None),'INSUFFICIENT_EVIDENCE')
add('unknown-quality',lambda d:d.update(quality={'pass':None}),'INSUFFICIENT_EVIDENCE')
save(Path('benchmarks/optimization_advisor/cases.json'),cases)
