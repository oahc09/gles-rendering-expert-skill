#!/usr/bin/env python3
"""Real host EGL and Android compile/link; explicitly not an APK/device run."""
import argparse,hashlib,json,os,subprocess,tempfile
from pathlib import Path
HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[1]
def digest(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def invoke(cmd,env=None):
 try:
  p=subprocess.run([str(x) for x in cmd],capture_output=True,text=True,timeout=120,env=env)
  return {'command':[str(x) for x in cmd],'exit_code':p.returncode,'stdout':p.stdout,'stderr':p.stderr,'status':'PASS' if p.returncode==0 else 'FAIL'}
 except (OSError,subprocess.TimeoutExpired) as e:return {'command':[str(x) for x in cmd],'exit_code':None,'status':'FAIL','stderr':str(e)}
def main():
 p=argparse.ArgumentParser();p.add_argument('--output',type=Path,required=True);p.add_argument('--ndk',type=Path);p.add_argument('--jdk',type=Path);p.add_argument('--android-jar',type=Path);a=p.parse_args()
 report={'schema_version':1,'scope':'software EGL runtime / Android arm64 source compile-link, not APK or physical acceptance','device_roundtrip':'NOT_RUN','android_lifecycle':'NOT_RUN','apk_assembly':'NOT_RUN','source_sha256':{str(x.relative_to(ROOT)):digest(x) for x in sorted(HERE.rglob('*')) if x.is_file() and x.suffix in ('.hpp','.cpp','.java','.py')},'checks':[]}
 report['source_sha256'].update({str(x.relative_to(ROOT)):digest(x) for x in (ROOT/'examples/repro/state_fixture.cpp',ROOT/'examples/scenes/scene_lab.cpp')})
 env=os.environ.copy();sdk=env.get('GLES_SDK_ROOT')
 if sdk:
  env['CPLUS_INCLUDE_PATH']=str(Path(sdk)/'include');env['LIBRARY_PATH']=str(Path(sdk)/'lib/x86_64-linux-gnu');env['LD_LIBRARY_PATH']=env['LIBRARY_PATH']
 env.update(EGL_PLATFORM='surfaceless',LIBGL_ALWAYS_SOFTWARE='1',MESA_SHADER_CACHE_DISABLE='true')
 with tempfile.TemporaryDirectory(prefix='gles-system-') as directory:
  temp=Path(directory)
  for name,source in [('multi',HERE/'multi_surface_host.cpp'),('state',ROOT/'examples/repro/state_fixture.cpp')]:
   binary=temp/name;check=invoke(['c++','-std=c++17','-Wall','-Wextra','-Werror','-pedantic',source,'-lEGL','-lGLESv2','-pthread','-o',binary],env);check['name']=name+' host compile';report['checks'].append(check)
   if check['status']=='PASS':
    run=invoke([binary],env);run.update(name=name+' real software execution',binary_sha256=digest(binary));report['checks'].append(run)
  if a.ndk:
   compiler=a.ndk/'toolchains/llvm/prebuilt/linux-x86_64/bin/aarch64-linux-android26-clang++'
   for name,source,flags in [('interop',HERE/'interop_roundtrip.cpp',['-Wno-missing-field-initializers','-lvulkan']),('jni',HERE/'app/src/main/cpp/bridge.cpp',['-shared','-fPIC'])]:
    binary=temp/(name+'.so' if name=='jni' else name);check=invoke([compiler,'-std=c++17','-Wall','-Wextra','-Werror','-pedantic',source,*flags,'-lEGL','-lGLESv3','-landroid','-Wl,--no-undefined','-Wl,-z,max-page-size=16384','-o',binary]);check['name']=name+' NDK API26 arm64 compile/link'
    if binary.exists():check['binary_sha256']=digest(binary);check['elf']=invoke([compiler.parent/'llvm-readelf','-h','-lW',binary])
    report['checks'].append(check)
  else:report['checks'].append({'name':'NDK','status':'BLOCKED_BY_TOOLCHAIN'})
  if a.jdk and a.android_jar:
   classes=temp/'classes';classes.mkdir();sources=sorted(HERE.glob('app/src/main/java/**/*.java'));check=invoke([a.jdk/'bin/javac','--release','17','-Xlint:all','-classpath',a.android_jar,'-d',classes,*sources]);check.update(name='Android API35 Java compile',android_jar_sha256=digest(a.android_jar),class_sha256={str(x.relative_to(classes)):digest(x) for x in classes.rglob('*.class')});report['checks'].append(check)
  else:report['checks'].append({'name':'Java Android','status':'BLOCKED_BY_TOOLCHAIN'})
 report['status']='PASS' if all(x['status']=='PASS' for x in report['checks']) else 'FAIL_OR_BLOCKED'
 a.output.parent.mkdir(parents=True,exist_ok=True);a.output.write_text(json.dumps(report,indent=2)+'\n');print(json.dumps({'status':report['status'],'checks':len(report['checks'])}));return 0 if report['status']=='PASS' else 1
if __name__=='__main__':raise SystemExit(main())
