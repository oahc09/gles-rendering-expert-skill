#!/usr/bin/env python3
"""Build/run actual host GL pressure; optional real NDK compile, never target run."""
import argparse, hashlib, json, os, subprocess, tempfile
from pathlib import Path
from datetime import datetime, timezone
from validate import validate_rows
ROOT=Path(__file__).resolve().parents[2]
def sha(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()
def call(command,env,timeout=120):
 r=subprocess.run([str(x) for x in command],env=env,capture_output=True,text=True,timeout=timeout)
 return {'command':[str(x) for x in command],'exit_code':r.returncode,'stdout':r.stdout,'stderr':r.stderr}
def main():
 p=argparse.ArgumentParser();p.add_argument('--output',type=Path,required=True);p.add_argument('--sdk',type=Path);p.add_argument('--ndk',type=Path);p.add_argument('--scenes',type=int,default=100);a=p.parse_args()
 env=os.environ.copy()
 if a.sdk:
  for k,v in [('CPLUS_INCLUDE_PATH',a.sdk/'include'),('LIBRARY_PATH',a.sdk/'lib/x86_64-linux-gnu'),('LD_LIBRARY_PATH',a.sdk/'lib/x86_64-linux-gnu')]:env[k]=str(v)+(os.pathsep+env[k] if env.get(k) else '')
 env.setdefault('EGL_PLATFORM','surfaceless');env.setdefault('LIBGL_ALWAYS_SOFTWARE','1');env.setdefault('MESA_SHADER_CACHE_DIR','/tmp/gles-resource-shader-cache')
 sources=[ROOT/'examples/resource_pressure/stress.cpp',ROOT/'examples/resource_pressure/completion_policy.hpp',ROOT/'examples/validation/egl_smoke.cpp',ROOT/'references/examples/pbo_streaming_upload.cpp',Path(__file__).resolve(),Path(__file__).with_name('validate.py').resolve()]
 report={'schema_version':1,'timestamp':datetime.now(timezone.utc).isoformat(),'scope':'actual host software GL resource accounting; synthetic pending policy separate; not Android runtime/performance','source_sha256':{str(s.relative_to(ROOT)):sha(s) for s in sources}}
 try:
  with tempfile.TemporaryDirectory(prefix='gles-resource-pressure-') as folder:
   binary=Path(folder)/'stress';flags=['-std=c++17','-Wall','-Wextra','-Werror','-pedantic',str(sources[0]),'-lEGL','-lGLESv2','-pthread']
   report['host_compiler_version']=call([env.get('CXX','c++'),'--version'],env)
   report['host_compile']=call([env.get('CXX','c++'),*flags,'-o',binary],env)
   if report['host_compile']['exit_code']==0:
    report['host_binary_sha256']=sha(binary);report['host_run']=call([binary,str(a.scenes)],env,300)
    if report['host_run']['exit_code']==0:
     rows=[json.loads(x) for x in report['host_run']['stdout'].splitlines()];report['summary']=validate_rows(rows,a.scenes)
   if a.ndk:
    tool=a.ndk/'toolchains/llvm/prebuilt/linux-x86_64/bin/aarch64-linux-android26-clang++';target=Path(folder)/'android-stress'
    report['ndk_compiler_version']=call([tool,'--version'],os.environ.copy())
    report['ndk_compile']=call([tool,*['-lGLESv3' if f=='-lGLESv2' else f for f in flags],'-o',target],os.environ.copy())
    if report['ndk_compile']['exit_code']==0:report['ndk_binary_sha256']=sha(target)
    report['ndk_target_execution']='NOT_RUN_DEVICE'
  report['status']='PASS' if report.get('summary',{}).get('status')=='PASS' and report.get('ndk_compile',{'exit_code':0})['exit_code']==0 else 'FAIL'
 except (OSError,ValueError,KeyError,subprocess.TimeoutExpired) as error:report.update(status='FAIL',error=str(error))
 a.output.parent.mkdir(parents=True,exist_ok=True);a.output.write_text(json.dumps(report,indent=2)+'\n');print(json.dumps({'status':report['status'],'report':str(a.output)}));return 0 if report['status']=='PASS' else 1
if __name__=='__main__':raise SystemExit(main())
