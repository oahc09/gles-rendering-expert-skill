#!/usr/bin/env python3
"""Actual finite-scene software capture and hash-bound grouped quality ingestion.
No physical-device adapter is implemented here; software never enters GPU timing protocol.
"""
import argparse,hashlib,importlib.util,json,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
spec=importlib.util.spec_from_file_location('portability_scene',ROOT/'benchmarks/pipeline/candidate_replay.py')
scene=importlib.util.module_from_spec(spec);spec.loader.exec_module(scene)
WORKLOAD='rgba8-three-pass-scale-v1'

def quality_gate(report):
    """Recalculate CPU and A/B oracle, do not trust report pass/observed booleans."""
    change=scene.transform(scene.baseline())
    if report.get('transformation')!=change:raise ValueError('scene transformation binding mismatch')
    cases=report.get('cases')
    if not isinstance(cases,list) or len(cases)!=2:raise ValueError('two source patterns required')
    results=[]
    for row,pattern in zip(cases,('constant','checkerboard')):
        if row.get('pattern')!=pattern:raise ValueError('pattern mismatch')
        outputs=[]
        for arm,scaled in (('baseline',False),('candidate',True)):
            draw=row.get(arm,{})
            graph=change['candidate'] if scaled else change['fallback']
            if draw.get('graph_sha256')!=scene.digest(graph) or draw.get('gl_error')!=0:raise ValueError('graph or GL error')
            expected_passes=[]
            for p in graph['passes']:
                sources={'shader.vert':scene.VERT,'shader.frag':scene.fragment(pattern,not p.get('reads'))}
                expected_passes.append({'pass':p['id'],'extent':graph['resources'][p['writes'][0]]['size'],'compile':True,'link':True,'source_sha256':{k:hashlib.sha256(v.encode()).hexdigest() for k,v in sources.items()}})
            if draw.get('passes')!=expected_passes or draw.get('synchronization')!=scene.validate(graph):raise ValueError('shader/pass/synchronization binding mismatch')
            pixels=draw.get('pixels')
            if not isinstance(pixels,list) or len(pixels)!=64 or any(type(x)!=int or not 0<=x<=255 for x in pixels):raise ValueError('RGBA8 pixels required')
            err=max(abs(x-y) for x,y in zip(pixels,scene.golden(pattern,scaled)))
            if err>1:raise ValueError('independent CPU oracle failed')
            outputs.append(pixels)
        error=max(abs(x-y) for x,y in zip(*outputs))
        accepted=error<=1
        if accepted!=(pattern=='constant'):raise ValueError('positive/negative quality sensitivity failed')
        results.append({'pattern':pattern,'max_abs_error':error,'candidate_quality':'PASS' if accepted else 'REJECTED_BY_QUALITY','selected':'candidate' if accepted else 'baseline'})
    return {'status':'FINITE_QUALITY_CONTROLS_PASS','cases':results,'general_quality_equivalence':False,'physical_quality_evidence':False}

def collect(config,backend,output_dir):
    if backend not in ('mesa-software','angle-software'):raise ValueError('Only explicitly labelled software collectors are supported')
    if (config.get('kind')=='angle')!=(backend=='angle-software'):raise ValueError('backend/config mismatch')
    output=Path(output_dir);output.mkdir(parents=True,exist_ok=True)
    report=scene.run(config);quality=quality_gate(report)
    if report.get('status')!='HOST_PASS':raise ValueError('scene harness failed')
    artifact=output/(backend+'-scene.json');artifact.write_text(json.dumps(report,indent=2)+'\n')
    record={'schema_version':1,'hardware_kind':'software','backend':backend,'workload_id':WORKLOAD,
        'baseline_graph_sha256':report['transformation']['baseline_sha256'],'candidate_graph_sha256':report['transformation']['candidate_sha256'],
        'scene':{'path':artifact.name,'sha256':hashlib.sha256(artifact.read_bytes()).hexdigest()},
        'quality':quality,'timing':'NOT_COLLECTED','physical_provider':'BLOCKED_BY_HARDWARE',
        'release_acceptance':False,'collector_scope':'host software correctness, no physical-device identity claim'}
    (output/(backend+'-record.json')).write_text(json.dumps(record,indent=2)+'\n');return record

def grouped(records,root):
    root=Path(root).resolve();groups={}
    for record in records:
        if record.get('hardware_kind')!='software':raise ValueError('physical capture requires real provider and physical protocol; cannot relabel software')
        if record.get('backend') not in ('mesa-software','angle-software') or record.get('workload_id')!=WORKLOAD:raise ValueError('unsupported group')
        ref=record.get('scene',{});relative=Path(ref.get('path',''));p=(root/relative).resolve()
        if relative.is_absolute() or not p.is_relative_to(root) or not p.is_file():raise ValueError('scene path')
        raw=p.read_bytes()
        if hashlib.sha256(raw).hexdigest()!=ref.get('sha256'):raise ValueError('scene hash')
        report=json.loads(raw);quality=quality_gate(report)
        if record.get('quality')!=quality:raise ValueError('detached quality summary')
        for k in ('baseline','candidate'):
            if record.get(k+'_graph_sha256')!=report['transformation'][k+'_sha256']:raise ValueError('detached graph')
        key=(record['backend'],WORKLOAD,record['baseline_graph_sha256'],record['candidate_graph_sha256'])
        g=groups.setdefault(key,{'backend':key[0],'workload_id':key[1],'baseline_graph_sha256':key[2],'candidate_graph_sha256':key[3],'capture_count':0,'quality':quality})
        g['capture_count']+=1
    return {'status':'SOFTWARE_QUALITY_ONLY','groups':list(groups.values()),'physical_provider':'BLOCKED_BY_HARDWARE','performance':'NOT_MEASURED','release_acceptance':False,'cross_group_comparison':'PROHIBITED','integrity_not_authenticity':True}

if __name__=='__main__':
    p=argparse.ArgumentParser();sub=p.add_subparsers(dest='command',required=True)
    c=sub.add_parser('collect');c.add_argument('--config',type=Path,required=True);c.add_argument('--backend',required=True);c.add_argument('--output-dir',type=Path,required=True)
    g=sub.add_parser('group');g.add_argument('records',type=Path,nargs='+');g.add_argument('--artifact-root',type=Path,required=True);g.add_argument('--output',type=Path,required=True)
    a=p.parse_args()
    try:
        if a.command=='collect':r=collect(json.loads(a.config.read_text()),a.backend,a.output_dir)
        else:r=grouped([json.loads(x.read_text()) for x in a.records],a.artifact_root);a.output.write_text(json.dumps(r,indent=2)+'\n')
        print(r.get('status','CAPTURED_SOFTWARE'))
    except (ValueError,KeyError,TypeError,OSError) as e:p.exit(2,str(e)+'\n')
