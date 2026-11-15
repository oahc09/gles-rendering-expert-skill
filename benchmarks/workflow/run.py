#!/usr/bin/env python3
"""Closed end-to-end software workflow; no user-supplied code or shell commands."""
import argparse,hashlib,importlib.util,json,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2];sys.path.insert(0,str(ROOT/'tools'))
from workload_fingerprint import fingerprint
from estimate_gpu_cost import estimate
from optimization_advisor import advise
from optimization_experiments import resolve
spec=importlib.util.spec_from_file_location('workflow_collector',ROOT/'benchmarks/device_portability/scene_collector.py')
collector=importlib.util.module_from_spec(spec);spec.loader.exec_module(collector)
EXPERIMENT='rgba8-graph-scale-replay-v1'
REGISTRY={EXPERIMENT:collector.collect}

def preflight(request):
    if not isinstance(request,dict) or set(request)!={'schema_version','experiment_id','workload'}:raise ValueError('Only schema_version, experiment_id, workload are accepted; no commands')
    if type(request['schema_version']) is not int or request['schema_version']!=1:raise ValueError('schema_version')
    if not isinstance(request['experiment_id'],str) or request['experiment_id'] not in REGISTRY:raise ValueError('unregistered experiment')
    w=request['workload']
    # This finite scene is authored, not a profile of a supplied app or a measured device trace.
    if not isinstance(w,dict) or set(w)!={'workload_id','provenance','resolution','sampling_formats','thermal_state','trace_available'}:raise ValueError('closed finite-scene workload descriptor required')
    if w!={'workload_id':collector.WORKLOAD,'provenance':'synthetic','resolution':[4,4], 'sampling_formats':['RGBA8'],'thermal_state':'UNKNOWN','trace_available':False}:raise ValueError('descriptor does not bind registered scene')
    return fingerprint(w)

def cost(graph):
    return estimate({'attachments':[{'id':name,'format':r['format'],'width':r['size'][0],'height':r['size'][1],
        'samples':1,'passes':1,'clear':False,'invalidate':False,'resolve':False,'external_consumer':name=='screen'} for name,r in graph['resources'].items()],
        'texture_samples':sum(graph['resources'][p['writes'][0]]['size'][0]*graph['resources'][p['writes'][0]]['size'][1] for p in graph['passes'] if p.get('reads')),'bytes_per_sample':4})

def run(request,config,backend,output):
    fp=preflight(request)
    # Validate before any output/GPU work. Driver config is local trusted operator input, not workload content.
    if backend not in ('mesa-software','angle-software'):raise ValueError('physical provider not implemented')
    output=Path(output);change=collector.scene.transform(collector.scene.baseline())
    estimates={'baseline':cost(change['fallback']),'candidate':cost(change['candidate'])}
    source=ROOT/'benchmarks/pipeline/candidate_replay.py'
    binding={'registered_advisor_experiment':resolve(EXPERIMENT),'id':EXPERIMENT,'entrypoint':'benchmarks/device_portability/scene_collector.py:collect',
        'scene_source':'benchmarks/pipeline/candidate_replay.py','scene_source_sha256':hashlib.sha256(source.read_bytes()).hexdigest(),
        'dispatch':'closed Python callable registry; no shell/exec/eval','scope':'constant and checkerboard three-pass 4x4 RGBA8 scene only'}
    record=REGISTRY[request['experiment_id']](config,backend,output)
    groups=collector.grouped([record],output) # Re-read archived bytes, hash and independent CPU oracle.
    if record['baseline_graph_sha256']!=change['baseline_sha256'] or record['candidate_graph_sha256']!=change['candidate_sha256']:raise ValueError('executed graph differs from costed graph')
    candidates=[]
    for row in record['quality']['cases']:
        candidates.append({'id':row['pattern'],'workload_id':collector.WORKLOAD,
            'experiment':EXPERIMENT,'fallback':'baseline','capability_supported':True,
            'labels':[], 'confidence':0,'estimated_gain_range':[0,0],
            'quality':{'pass':row['candidate_quality']=='PASS',
                'golden_id':collector.WORKLOAD+'-'+row['pattern']+'-cpu',
                'thresholds':{'max_rgba8_error':1}},
            # Real SOFTWARE output, explicitly not a physical timing record.
            # Nonempty measurement makes decide enforce the physical provenance gate.
            'measurement':{'provenance':'software','quality_artifact':record['scene'],
                'timing':'NOT_COLLECTED'}})
    advice=advise({'workload':request['workload'],'candidates':candidates},output)
    decisions={r['id']:r for r in advice['candidates']};outcomes=[]
    for row in record['quality']['cases']:
        decision=decisions[row['pattern']]
        outcomes.append({**row,'experiment_selection':row['selected'],
            'production_selection':'candidate' if decision['status']=='VERIFIED_IMPROVEMENT' else 'baseline',
            'performance_state':decision['status'],'advisor_decision':decision})
    result={'schema_version':1,'status':'HOST_WORKFLOW_PASS','workload_fingerprint':fp,'cost_estimates':estimates,
        'hypothesis':'Smaller private intermediate may reduce logical work; not a measured bandwidth or speed gain',
        'experiment_binding':binding,'advisor_input_candidates':candidates,'advisor_result':advice,'executed_capture':record,'grouped_quality':groups,'decisions':outcomes,
        'production_renderer_mutated':False,'release_acceptance':False,'physical_performance':'BLOCKED_BY_HARDWARE',
        'agent_provider':'NOT_RUN','performance_improvement':'NOT_VERIFIED',
        'stages':['descriptor binding','fingerprint','logical cost estimate','closed registry dispatch','actual GLES replay','archived artifact revalidation','CPU quality gate','optimization_advisor.advise/decide','explicit baseline fallback']}
    (output/'workflow-result.json').write_text(json.dumps(result,indent=2,allow_nan=False)+'\n');return result

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('request',type=Path);p.add_argument('--config',type=Path,required=True);p.add_argument('--backend',required=True);p.add_argument('--output-dir',type=Path,required=True);a=p.parse_args()
    try:r=run(json.loads(a.request.read_text()),json.loads(a.config.read_text()),a.backend,a.output_dir);print(r['status'])
    except (ValueError,KeyError,TypeError,OSError,RuntimeError) as e:p.exit(2,str(e)+'\n')
