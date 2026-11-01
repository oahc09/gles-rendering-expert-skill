#!/usr/bin/env python3
"""Compile companion sources; compilation is NOT Android external-video execution."""
import argparse,hashlib,json,os,subprocess,tempfile
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
def main():
    p=argparse.ArgumentParser();p.add_argument('--jdk',type=Path,required=True);p.add_argument('--android-jar',type=Path,required=True);p.add_argument('--glslang',type=Path,required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args()
    java=ROOT/'examples/android_cases/surfacevideo/src/main/java/org/example/gleslab/VideoInputGuard.java';shader=ROOT/'examples/texture_pipeline/yuv_planes.frag'
    sources=sorted(java.parent.glob('*.java'))+[ROOT/'benchmarks/texture_pipeline/VideoInputGuardTest.java']
    with tempfile.TemporaryDirectory() as folder:
        commands=[[str(a.jdk/'bin/javac'),'-J-Djava.home='+str(a.jdk),'--release','17','-classpath',str(a.android_jar),'-d',folder]+[str(source) for source in sources],[str(a.glslang),str(shader)],['java','-classpath',folder+os.pathsep+str(a.android_jar),'org.example.gleslab.VideoInputGuardTest']]
        result={'android_video_runtime':'NOT_RUN','protected_pipeline':'BLOCKED_NOT_IMPLEMENTED','commands':[]}
        for command in commands:
            r=subprocess.run(command,capture_output=True,text=True);result['commands'].append(dict(argv=command,exit_code=r.returncode,stdout=r.stdout,stderr=r.stderr))
        result['source_sha256']={str(f.relative_to(ROOT)):hashlib.sha256(f.read_bytes()).hexdigest() for f in sources+[shader]}
        result['android_api_jar_sha256']=hashlib.sha256(a.android_jar.read_bytes()).hexdigest();result['status']='PASS' if all(x['exit_code']==0 for x in result['commands']) else 'FAIL'
        a.output.write_text(json.dumps(result,indent=2)+'\n');return 0 if result['status']=='PASS' else 1
if __name__=='__main__':raise SystemExit(main())
