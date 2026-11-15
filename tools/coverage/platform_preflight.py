"""Separate build toolchain readiness from target execution; no downloads/licenses."""
import argparse,json,os,shutil,subprocess
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
def inspect():
 sdk=Path(os.environ.get('ANDROID_SDK_ROOT',os.environ.get('ANDROID_HOME','/nonexistent')))
 required={'java':bool(shutil.which('java')),'gradle':bool(shutil.which('gradle')),'android_35':(sdk/'platforms/android-35/android.jar').is_file(),'ndk_27':(sdk/'ndk/27.0.12077973/build/cmake/android.toolchain.cmake').is_file(),'cmake_3_22_1':(sdk/'cmake/3.22.1/bin/cmake').is_file(),'adb':bool(shutil.which('adb'))}
 return {'schema_version':1,'requirements':required,'android_build':'READY_NOT_RUN' if all(required[k] for k in required if k!='adb') else 'BLOCKED_BY_TOOLCHAIN','android_install':'NOT_RUN','physical_mali':'BLOCKED_BY_HARDWARE','physical_adreno':'BLOCKED_BY_HARDWARE','physical_powervr':'BLOCKED_BY_HARDWARE','windows_angle_x64':'BLOCKED_BY_HARDWARE','windows_angle_arm64':'BLOCKED_BY_HARDWARE','embedded_gbm_wayland_x11':'BLOCKED_BY_HARDWARE','software_egl':'SEPARATE_HOST_RUNS','device_acceptance':False,'apk_artifact':None}
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--build-android',action='store_true');p.add_argument('--output',type=Path,required=True);a=p.parse_args();result=inspect()
 if a.build_android and result['android_build']=='READY_NOT_RUN':
  run=subprocess.run(['gradle','--no-daemon','assembleDebug'],cwd=ROOT/'examples/system_android',capture_output=True,text=True)
  apk=ROOT/'examples/system_android/app/build/outputs/apk/debug/app-debug.apk';result['android_build']='PASS' if run.returncode==0 and apk.is_file() else 'FAIL';result['apk_artifact']=str(apk.relative_to(ROOT)) if apk.is_file() else None
 a.output.parent.mkdir(parents=True,exist_ok=True);a.output.write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result));raise SystemExit(1 if a.build_android and result['android_build']!='PASS' else 0)
