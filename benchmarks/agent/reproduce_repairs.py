#!/usr/bin/env python3
"""Execute authored failure/fix controls; NOT a live model repair benchmark."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import sys
import time
ROOT=Path(__file__).resolve().parents[2]
HERE=Path(__file__).resolve().parent

def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def command(args,env):
    p=subprocess.run(args,env=env,capture_output=True,text=True,timeout=120)
    return {'command':list(map(str,args)),'exit_code':p.returncode,'stdout':p.stdout,'stderr':p.stderr}
def main():
    p=argparse.ArgumentParser();p.add_argument('--compiler',default='glslangValidator');p.add_argument('--output',type=Path,required=True);a=p.parse_args()
    compiler=shutil.which(a.compiler)
    if not compiler:print('BLOCKED_BY_TOOLCHAIN');return 3
    env=os.environ.copy();env.update(EGL_PLATFORM='surfaceless',LIBGL_ALWAYS_SOFTWARE='1',MESA_SHADER_CACHE_DISABLE='true')
    if env.get('GLES_SDK_ROOT'):
        sdk=Path(env['GLES_SDK_ROOT'])
        for k,v in [('CPLUS_INCLUDE_PATH',sdk/'include'),('LIBRARY_PATH',sdk/'lib/x86_64-linux-gnu'),('LD_LIBRARY_PATH',sdk/'lib/x86_64-linux-gnu')]:env[k]=str(v)+(os.pathsep+env[k] if env.get(k) else '')
    results=[]
    for row in json.loads((HERE/'repair-fixtures/shader-pairs.json').read_text()):
        captures={}
        for kind in ('bad','good'):
            sources=[ROOT/row[kind]]
            if row['link_vertex']:sources.insert(0,ROOT/row['link_vertex'])
            captures[kind]=command([compiler]+(['-l'] if row['link_vertex'] else [])+list(map(str,sources)),env)
            captures[kind]['sources_sha256']={str(x.relative_to(ROOT)):sha(x) for x in sources}
        bad=captures['bad'];good=captures['good'];passed=bad['exit_code'] in (2,3) and 'ERROR:' in bad['stdout']+bad['stderr'] and good['exit_code']==0
        results.append({'case_id':row['id'],'kind':'actual_shader_failure_fix','status':'PASS' if passed else 'FAIL','captures':captures})
    source=ROOT/'examples/validation/egl_smoke.cpp';original=source.read_text();imports=ROOT/'references/examples/pbo_streaming_upload.cpp'
    # Preserve the tested original source hash; only resolve its existing relative include in scratch copies.
    resolved=original.replace('"../../references/examples/pbo_streaming_upload.cpp"',json.dumps(str(imports)))
    with tempfile.TemporaryDirectory(prefix='gles-repair-controls-') as folder:
        folder=Path(folder)
        def build_run(text,label):
            src=folder/(label+'.cpp');src.write_text(text);binary=folder/label
            build=command([env.get('CXX','c++'),'-std=c++17','-Wall','-Wextra','-Werror','-pedantic',str(src),'-lEGL','-lGLESv2','-pthread','-o',str(binary)],env)
            execution=command([str(binary),str(ROOT/'examples/validation/shaders')],env) if build['exit_code']==0 else None
            return {'build':build,'run':execution,'scratch_source_sha256':sha(src),'base_source_sha256':sha(source),'import_sha256':sha(imports)}
        fixed=build_run(resolved,'fixed-baseline')
        for row in json.loads((HERE/'repair-fixtures/runtime-mutations.json').read_text()):
            if resolved.count(row['good'])!=1:raise ValueError('Mutation anchor is not unique: '+row['id'])
            mutated=resolved.replace(row['good'],row['bad'],1);bad=build_run(mutated,row['id'])
            passed=bad['build']['exit_code']==0 and bad['run']['exit_code']==1 and 'FAIL:' in bad['run']['stderr'] and fixed['build']['exit_code']==0 and fixed['run']['exit_code']==0
            results.append({'case_id':row['id'],'kind':'actual_software_runtime_failure_fix','status':'PASS' if passed else 'FAIL','bad':bad,'fixed':fixed})
    # Fresh compilation and execution, not replay of a historical JSON verdict.
    scene_output=a.output.parent/('repair-scenes-'+str(time.time_ns()))
    scene_output.mkdir(parents=True,exist_ok=False)
    build_folder=scene_output/'build';env['GLES_SCENE_BUILD_DIR']=str(build_folder)
    build_capture=command(['sh',str(ROOT/'examples/scenes/run-host.sh'),'S01',str(scene_output/'build-smoke.ppm'),'96','64','baseline'],env)
    if build_capture['exit_code']!=0:raise ValueError('Scene build/runtime failed: '+build_capture['stderr'])
    binary=build_folder/'scene-lab'
    execution=command([sys.executable,str(ROOT/'benchmarks/scenes/run.py'),'--binary',str(binary),'--output',str(scene_output/'images')],env)
    if execution['exit_code']!=0:raise ValueError('Scene correctness execution failed: '+execution['stderr'])
    scene_path=scene_output/'images/report.json';scene=json.loads(scene_path.read_text())
    scene_source=ROOT/'examples/scenes/scene_lab.cpp'
    if sha(scene_source)!=scene['source_sha256'] or sha(ROOT/'benchmarks/scenes/run.py')!=scene['runner_sha256'] or sha(binary)!=scene['binary_sha256']:
        raise ValueError('Scene source/runner/binary does not match fresh execution')
    for row in scene['runs']:
        image=Path(row['command'][2])
        if not image.resolve().is_relative_to(scene_output.resolve()) or sha(image)!=row['image_sha256']:
            raise ValueError('Scene image evidence mismatch')
    # Executables are rebuildable and must not be shipped; keep hashes, source and image evidence.
    binary.unlink()
    for i in range(8):
        sid=f'S{i+1:02}';base=[x for x in scene['runs'] if x['scene']==sid and x['variant']=='baseline' and x['size']==96 and x['instances']==64]
        bad=[x for x in scene['runs'] if x['scene']==sid and x['variant']=='degraded']
        passed=len(base)==1 and len(bad)==1 and base[0]['golden']['pass'] and not bad[0]['baseline_difference']['pass']
        results.append({'case_id':f'A{81+i:03}','kind':'actual_scene_visual_failure_fix','status':'PASS' if passed else 'FAIL','source_sha256':sha(scene_source),'report_sha256':sha(scene_path),'baseline':base,'degraded':bad})
    report={'status':'PASS' if all(r['status']=='PASS' for r in results) else 'FAIL','scope':'24 authored controlled failure/fix reproductions, not production incidents or model-produced patches','live_provider_calls':0,'results':results}
    a.output.parent.mkdir(parents=True,exist_ok=True);a.output.write_text(json.dumps(report,indent=2)+'\n');print(json.dumps({'status':report['status'],'cases':len(results),'failed':[r['case_id'] for r in results if r['status']!='PASS']}));return int(report['status']!='PASS')
if __name__=='__main__':raise SystemExit(main())
