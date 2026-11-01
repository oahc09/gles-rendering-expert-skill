#!/usr/bin/env python3
"""Actual host software EGL probe adapter. Never claims a physical/ANGLE backend."""
import hashlib
import json
import os
from pathlib import Path
import platform
import subprocess
import sys
import tempfile
ROOT=Path(__file__).resolve().parents[2]
def call(command,env):
    p=subprocess.run(command,cwd=ROOT,env=env,capture_output=True,text=True,timeout=120)
    if p.returncode:raise RuntimeError(p.stderr or p.stdout)
    return p.stdout,p.stderr

def main():
    request=json.load(sys.stdin)
    if request.get('backend')!='software' or request.get('platform')!='host':
        print(json.dumps({'status':'BLOCKED_BY_HARDWARE','reason':'This adapter only controls host software EGL; native/ANGLE needs an explicitly installed target adapter.'}));return 3
    env=os.environ.copy();env.update(EGL_PLATFORM='surfaceless',LIBGL_ALWAYS_SOFTWARE='1',MESA_SHADER_CACHE_DISABLE='true')
    if env.get('GLES_SDK_ROOT'):
        sdk=Path(env['GLES_SDK_ROOT'])
        for key,value in [('CPLUS_INCLUDE_PATH',sdk/'include'),('LIBRARY_PATH',sdk/'lib/x86_64-linux-gnu'),('LD_LIBRARY_PATH',sdk/'lib/x86_64-linux-gnu')]:env[key]=str(value)+(os.pathsep+env[key] if env.get(key) else '')
    with tempfile.TemporaryDirectory(prefix='gles-device-lab-') as folder:
        binary=Path(folder)/'probe';call([env.get('CXX','c++'),'-std=c++17','-Wall','-Wextra','-Werror','-pedantic',str(ROOT/'benchmarks/device_lab/probe.cpp'),'-lEGL','-lGLESv2','-pthread','-o',str(binary)],env)
        output,stderr=call([str(binary)],env)
        rows=[json.loads(x) for x in output.splitlines()];snapshot=rows[0]['CapabilitySnapshot'];snapshot.update(rows[1]['extended_probe'])
        snapshot['egl_extensions']=snapshot['egl_extensions'].split();snapshot['limits'].update(max_texture_size=snapshot.pop('max_texture_size'),max_color_attachments=snapshot.pop('max_color_attachments'))
        snapshot.update(build={str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest() for p in (ROOT/'benchmarks/device_lab/probe.cpp',ROOT/'examples/validation/egl_smoke.cpp',ROOT/'references/examples/pbo_streaming_upload.cpp')},platform='host',os=platform.system(),os_build=platform.release(),api_level=None,device='current host',backend='software',backend_evidence={'kind':'controlled_creation','settings':{'LIBGL_ALWAYS_SOFTWARE':'1','EGL_PLATFORM':'surfaceless'}},hardware_kind='software',context_generation=1,surface_generation=1)
        smoke,smoke_err=call(['sh','examples/validation/run-host.sh'],env)
        events=[json.loads(x) for x in smoke.splitlines() if x.startswith('{')]
        print(json.dumps({'status':'CAPTURED','snapshot':snapshot,'correctness_events':[x for x in events if 'case' in x], 'raw_probe':output,'raw_smoke':smoke,'stderr':stderr+smoke_err,'binary_sha256':hashlib.sha256(binary.read_bytes()).hexdigest(),'performance_claim':'NOT_MEASURED'}))
    return 0
if __name__=='__main__':
    try:raise SystemExit(main())
    except (ValueError,OSError,RuntimeError,subprocess.TimeoutExpired) as e:print(str(e),file=sys.stderr);raise SystemExit(2)
