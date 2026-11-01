#!/usr/bin/env python3
"""Bind the 24 repair prompts to actual failure logs, preserving the original 64 cases."""
import argparse
import hashlib
import json
from pathlib import Path
HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[1]
SCENE_CODE=[
'glEnable(GL_BLEND); glBlendFunc(GL_SRC_ALPHA, GL_ONE_MINUS_SRC_ALPHA); glDisable(GL_BLEND); // transparent card draw follows',
'vec2 normal=vec2(sin(uv.y*30.+.7),cos(uv.x*24.-.4))*.012; vec3 bed=texture(image,uv+normal*12.).rgb;',
'float soft=clamp((depth-.65)*12.,0.,1.); alpha=(1.-smoothstep(.2,1.,radius))*1.*.45;',
'vec3 mapped=x/(1.+x); color=vec4(mapped,1.); // output contract expects gamma-encoded display RGB',
'glEnable(GL_DEPTH_TEST); glDisable(GL_DEPTH_TEST); draw_instances(...);',
'bones={cos(.3),sin(.3),0,0,cos(-.6),sin(-.6),0,0}; bones[5]=1.8; glBufferData(GL_UNIFORM_BUFFER,sizeof(bones),bones.data(),GL_DYNAMIC_DRAW);',
'glDispatchCompute(...); glMemoryBarrier(GL_SHADER_STORAGE_BARRIER_BIT|GL_COMMAND_BARRIER_BIT); glMemoryBarrier(GL_BUFFER_UPDATE_BARRIER_BIT); glBindBuffer(GL_DRAW_INDIRECT_BUFFER,indirect); GLuint zero=0; glBufferSubData(GL_DRAW_INDIRECT_BUFFER,sizeof(GLuint),sizeof(GLuint),&zero);',
'float a=exp(-dot(q,q)*5.); color=vec4(tint,a*.85); // reference opacity is fixed by the visual contract'
]
def assemble(report_path):
    baseline=json.loads((HERE/'cases.json').read_text()); repairs=json.loads((HERE/'repair-cases.json').read_text());report=json.loads(report_path.read_text())
    if report['status']!='PASS' or len(report['results'])!=24:raise ValueError('Need completed actual repair reproductions')
    rows={r['case_id']:r for r in report['results']}
    for c in repairs['cases']:
        row=rows[c['case_id']]
        if row['status']!='PASS':raise ValueError('Missing actual failure/fix control')
        if row['kind']=='actual_software_runtime_failure_fix':log=row['bad']['run']['stderr']
        elif row['kind']=='actual_shader_failure_fix':log=row['captures']['bad']['stdout']+row['captures']['bad']['stderr']
        else:
            log=json.dumps({'visual_difference':row['degraded'][0]['baseline_difference'],'driver':row['degraded'][0]['renderer'],'gpu_time_ms':None})
            code=SCENE_CODE[int(c['case_id'][1:])-81]
            c['prompt']=c['prompt'].split('Controlled failure input:')[0]+'Controlled failure input (focused excerpt of scene source):\n```cpp\n'+code+'\n```\nReturn the minimal semantics-preserving correction and validation commands; no mobile performance result is available.'
        # Idempotent enrichment: do not append logs repeatedly.
        c['prompt']=c['prompt'].split('\nActual failure log:')[0]+'\nActual failure log:\n'+log
        c['repair']['reproduction_report']=str(report_path.relative_to(ROOT))
        c['repair']['reproduction_sha256']=hashlib.sha256(report_path.read_bytes()).hexdigest()
        c['compile_evidence']['status']='CONTROLLED_FIXTURE_EXECUTED_NOT_MODEL_PATCH'
    baseline['baseline_case_count']=64;baseline['baseline_sha256']=hashlib.sha256((HERE/'cases.json').read_bytes()).hexdigest();baseline['cases']+=repairs['cases']
    (HERE/'repair-cases.json').write_text(json.dumps(repairs,indent=2)+'\n');(HERE/'cases-v1.0.4.json').write_text(json.dumps(baseline,indent=2)+'\n')
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('report',type=Path);a=p.parse_args();assemble(a.report.resolve())
