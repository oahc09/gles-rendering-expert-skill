#!/usr/bin/env python3
"""Bounded official CTS build helper. Never certifies a driver or downloads sources."""
import argparse, pathlib, subprocess, shutil, os, json, hashlib
REVISION='5bb4c7e83acea0fc73e3333625e4f20542e584d0'
def main():
 p=argparse.ArgumentParser();p.add_argument('--source',required=True);p.add_argument('--build',required=True);p.add_argument('--cmake',default='cmake');p.add_argument('--jobs',type=int,default=2);p.add_argument('--receipt',type=pathlib.Path,required=True);a=p.parse_args()
 s=pathlib.Path(a.source).resolve();b=pathlib.Path(a.build).resolve();b.mkdir(parents=True,exist_ok=True)
 if subprocess.check_output(['git','rev-parse','HEAD'],cwd=s,text=True).strip()!=REVISION:raise SystemExit('source revision mismatch')
 if subprocess.check_output(['git','status','--porcelain','--untracked-files=no'],cwd=s,text=True).strip():raise SystemExit('dirty tracked CTS source rejected')
 if shutil.disk_usage(b).free < 2*1024**3:raise SystemExit('insufficient build space: require 2 GiB safety reserve')
 if not 1<=a.jobs<=8:raise SystemExit('jobs outside 1..8')
 env=dict(os.environ);env.pop('CPATH',None) # Prevent unrelated installed SPIRV headers shadowing pinned CTS dependencies.
 subprocess.run([a.cmake,'--fresh','-S',str(s),'-B',str(b),'-DDEQP_TARGET=surfaceless','-DCMAKE_BUILD_TYPE=Release'],check=True,timeout=180,env=env)
 subprocess.run([a.cmake,'--build',str(b),'--target','deqp-gles3','--parallel',str(a.jobs)],check=True,timeout=900,env=env)
 exe=b/'modules/gles3/deqp-gles3'
 deps={x.parent.parent.name:subprocess.check_output(['git','rev-parse','HEAD'],cwd=x.parent,text=True).strip() for x in (s/'external').glob('*/src/.git')}
 if subprocess.check_output(['git','status','--porcelain','--untracked-files=no'],cwd=s,text=True).strip():raise SystemExit('source changed during build')
 result={'source_revision':REVISION,'tracked_source_clean':True,'dependencies':deps,'dependency_manifest_sha256':hashlib.sha256((s/'external/fetch_sources.py').read_bytes()).hexdigest(),'executable_sha256':hashlib.sha256(exe.read_bytes()).hexdigest(),'target':'deqp-gles3','configure_exit_code':0,'build_exit_code':0,'target_platform':'surfaceless','certification_claim':False,'helper_sha256':hashlib.sha256(pathlib.Path(__file__).read_bytes()).hexdigest()}
 a.receipt.parent.mkdir(parents=True,exist_ok=True);a.receipt.write_text(json.dumps(result,indent=2)+'\n')
if __name__=='__main__':main()
