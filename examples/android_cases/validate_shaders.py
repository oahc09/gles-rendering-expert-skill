#!/usr/bin/env python3
"""Compile embedded GLSL, not Java or Android APKs."""
import argparse
import hashlib
import json
from pathlib import Path
import re
import shutil
import subprocess
import tempfile

ROOT=Path(__file__).parent

def main():
    p=argparse.ArgumentParser();p.add_argument('--compiler',default='glslangValidator');p.add_argument('--output',type=Path,default=ROOT/'shader-extraction-validation.json');a=p.parse_args()
    compiler=shutil.which(a.compiler)
    if not compiler:print(json.dumps({'status':'BLOCKED_BY_TOOLCHAIN'}));return 2
    results=[]
    with tempfile.TemporaryDirectory(prefix='gles-android-shaders-') as tmp:
        for module in ('wallpaper','surfacevideo'):
            source=next((ROOT/module/'src/main/java').rglob('*.java'))
            literals=re.findall(r'"(#version[^"\\]*(?:\\.[^"\\]*)*)"',source.read_text())
            if len(literals)!=2:raise ValueError('Expected exactly one vertex/fragment pair')
            paths=[]
            for content,suffix in zip(literals,['vert','frag']):
                path=Path(tmp)/(module+'.'+suffix);path.write_text(json.loads('"'+content+'"'));paths.append(path)
            result=subprocess.run([compiler,'-l',*map(str,paths)],capture_output=True,text=True,timeout=60)
            results.append({'module':module,'java_source_sha256':hashlib.sha256(source.read_bytes()).hexdigest(),
                            'shader_sha256':{path.suffix:hashlib.sha256(path.read_bytes()).hexdigest() for path in paths},
                            'glsl_compile_link':'PASS' if result.returncode==0 else 'FAIL','exit_code':result.returncode,
                            'stdout':result.stdout,'stderr':result.stderr,'android_target_compile':'NOT_RUN','device_runtime':'NOT_RUN'})
    report={'scope':'Actual glslang compile/link of extracted GLSL strings only; NOT Java/Android validation',
            'compiler_version':subprocess.check_output([compiler,'--version'],text=True),'results':results}
    a.output.parent.mkdir(parents=True,exist_ok=True);a.output.write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps({'shader_pairs':len(results),'failed':sum(r['exit_code']!=0 for r in results),'android_target_compile':'NOT_RUN'}))
    return int(any(row['exit_code']!=0 for row in results))
if __name__=='__main__':raise SystemExit(main())
