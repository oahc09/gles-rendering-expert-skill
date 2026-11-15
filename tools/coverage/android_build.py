#!/usr/bin/env python3
"""Build only with explicitly supplied existing SDK; never download or accept licenses."""
import argparse,hashlib,json,os,re,shutil,subprocess,zipfile
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
def inspect(sdk,gradle):
 sdk=Path(sdk);requirements={'java':bool(shutil.which('java')),'gradle':Path(gradle).is_file(),'android_35':(sdk/'platforms/android-35/android.jar').is_file(),'ndk_27':(sdk/'ndk/27.0.12077973/build/cmake/android.toolchain.cmake').is_file(),'cmake_3_22_1':(sdk/'cmake/3.22.1/bin/cmake').is_file(),'build_tools_35':(sdk/'build-tools/35.0.0/aapt2').is_file()}
 return {'schema_version':1,'requirements':requirements,'build':'READY_NOT_RUN' if all(requirements.values()) else 'BLOCKED_BY_TOOLCHAIN','apk':None,'install':'NOT_RUN','physical_execution':'NOT_RUN','license_acceptance':'NOT_PERFORMED','sdk_download':'DISABLED','release_acceptance':False}
def sanitize(s,paths):
 for p in sorted(map(str,paths),key=len,reverse=True):
  if p:s=s.replace(p,'<LOCAL_PATH>')
 # Public logs do not retain incidental absolute filesystem or host metadata.
 s=re.sub(r'(?<![\w:])/(?:tmp|workspace|home|opt|usr)/[^\s\]\)\"\']+', '<LOCAL_PATH>',s)
 return s

def build(sdk,gradle,output,execute=False):
 r=inspect(sdk,gradle);output=Path(output);output.mkdir(parents=True,exist_ok=True)
 if execute and r['build']=='READY_NOT_RUN':
  env=dict(os.environ);env['ANDROID_SDK_ROOT']=str(Path(sdk).resolve());env['ANDROID_HOME']=env['ANDROID_SDK_ROOT']
  # Explicit SDK points only to pre-provisioned packages. Never run sdkmanager --licenses.
  command=[str(Path(gradle).resolve()),'--no-daemon','-Pandroid.builder.sdkDownload=false',':app:assembleDebug']
  try:
   proc=subprocess.run(command,cwd=ROOT/'examples/system_android',env=env,capture_output=True,text=True,timeout=900)
   r['exit_code']=proc.returncode;log=sanitize(proc.stdout+'\n'+proc.stderr,[ROOT,Path(sdk).resolve(),Path(gradle).resolve(),Path.home()]);(output/'build.log').write_text(log)
   apk=ROOT/'examples/system_android/app/build/outputs/apk/debug/app-debug.apk'
   r['build']='FAIL'
   if proc.returncode==0 and apk.is_file():
    with zipfile.ZipFile(apk) as z:
     names=z.namelist();native=[n for n in names if n.startswith('lib/arm64-v8a/') and n.endswith('.so')]
     valid=bool(native) and 'classes.dex' in names and 'AndroidManifest.xml' in names
    if valid:r['build']='PASS';r['apk']={'sha256':hashlib.sha256(apk.read_bytes()).hexdigest(),'bytes':apk.stat().st_size,'contains_arm64_native':True,'contains_dex':True,'artifact':'examples/system_android/app/build/outputs/apk/debug/app-debug.apk'}
  except (OSError,subprocess.TimeoutExpired,zipfile.BadZipFile) as e:r['build']='FAIL';r['diagnostic']=type(e).__name__
 (output/'report.json').write_text(json.dumps(r,indent=2)+'\n');return r
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--sdk',type=Path,required=True);p.add_argument('--gradle',type=Path,required=True);p.add_argument('--output',type=Path,required=True);p.add_argument('--execute',action='store_true');a=p.parse_args();r=build(a.sdk,a.gradle,a.output,a.execute);raise SystemExit(0 if r['build']=='PASS' else 2)
