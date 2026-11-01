#!/usr/bin/env python3
"""Capture timed external workload iterations, never fabricate frame/device telemetry."""
import argparse,hashlib,json,math,os,platform,subprocess,time
from datetime import datetime,timezone
from pathlib import Path

def sha(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()
def main():
    p=argparse.ArgumentParser();p.add_argument('--duration',type=float,default=600);p.add_argument('--interval',type=float,default=1);p.add_argument('--scene-source',type=Path,required=True);p.add_argument('--output',type=Path,required=True);p.add_argument('command',nargs=argparse.REMAINDER);a=p.parse_args()
    if not math.isfinite(a.duration) or not math.isfinite(a.interval) or a.duration<=0 or a.interval<=0 or not a.command:raise ValueError('finite positive duration/interval and explicit command required')
    command=a.command[1:] if a.command[0]=='--' else a.command
    if not command:raise ValueError('empty command')
    binary=Path(command[0]).resolve()
    if not binary.is_file():raise ValueError('command must name an actual executable file')
    report={'schema_version':1,'provenance':'host_workload_iterations','clock':'monotonic_ns','started_at':datetime.now(timezone.utc).isoformat(),
      'device':{'device':'current host','soc':None,'gpu':None,'driver':None,'os':platform.platform(),'api':None,'backend':'software','refresh_hz':None,'resolution':None,'power_mode':'unknown'},
      'runner_sha256':sha(__file__),'scene_sha256':sha(a.scene_source),'binary_sha256':sha(binary),'command':command,'requested_duration_s':a.duration,'coverage':'sampled workload invocations, NOT display frames',
      'power_source':None,'thermal_source':None,'frequency_source':None,'samples':[],'events':[], 'device_acceptance':'NOT_RUN_DEVICE'}
    env=os.environ.copy();env.update(EGL_PLATFORM='surfaceless',LIBGL_ALWAYS_SOFTWARE='1',MESA_SHADER_CACHE_DISABLE='true')
    report['controlled_backend_environment']={k:env[k] for k in ('EGL_PLATFORM','LIBGL_ALWAYS_SOFTWARE','MESA_SHADER_CACHE_DISABLE')}
    def checkpoint():
        a.output.parent.mkdir(parents=True,exist_ok=True)
        temporary=a.output.with_suffix(a.output.suffix+'.partial')
        temporary.write_text(json.dumps(report,indent=2)+'\n');temporary.replace(a.output)
    report['status']='RUNNING';checkpoint()
    start=time.monotonic_ns();deadline=start+int(a.duration*1e9);next_sample=start
    while time.monotonic_ns()<deadline:
        now=time.monotonic_ns()
        if now<next_sample:time.sleep(min((next_sample-now)/1e9,max(0,(deadline-now)/1e9)));continue
        before=time.monotonic_ns()
        try:
            result=subprocess.run(command,capture_output=True,timeout=120,env=env)
        except (subprocess.TimeoutExpired,OSError) as error:
            report.update(status='FAILED',failure={'type':type(error).__name__,'message':str(error)},actual_wall_duration_s=(time.monotonic_ns()-start)/1e9);checkpoint();return 1
        after=time.monotonic_ns()
        row={'t_s':(before-start)/1e9,'elapsed_end_s':(after-start)/1e9,'iteration_ms':(after-before)/1e6,'frame_ms':None,'budget_ms':None,'foreground':True,'quality_level':0,'refresh_hz':None,'thermal_status':None,'temperature_c':None,'gpu_hz':None,'cpu_hz':None,'power_mw':None,
             'exit_code':result.returncode,'raw_stdout':result.stdout.decode(errors='replace'),'raw_stderr':result.stderr.decode(errors='replace'),'stdout_sha256':hashlib.sha256(result.stdout).hexdigest(),'stderr_sha256':hashlib.sha256(result.stderr).hexdigest()}
        report['samples'].append(row);report['actual_wall_duration_s']=(after-start)/1e9;checkpoint()
        if result.returncode:
            report['failure']={'stdout':result.stdout.decode(errors='replace'),'stderr':result.stderr.decode(errors='replace')};break
        next_sample=after+int(a.interval*1e9)
    report['actual_wall_duration_s']=(time.monotonic_ns()-start)/1e9
    report['status']='CAPTURED_HOST_ONLY' if report['samples'] and all(s['exit_code']==0 for s in report['samples']) else 'FAILED'
    checkpoint();print(json.dumps({'status':report['status'],'iterations':len(report['samples']),'wall_s':report['actual_wall_duration_s']}));return 0 if report['status']=='CAPTURED_HOST_ONLY' else 1
if __name__=='__main__':raise SystemExit(main())
