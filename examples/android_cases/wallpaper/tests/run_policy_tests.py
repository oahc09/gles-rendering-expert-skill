#!/usr/bin/env python3
"""Compile and execute the Android-independent HDR policy with a real JDK."""
import argparse
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import tempfile

ROOT=Path(__file__).resolve().parents[1]
def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--javac',default='javac');p.add_argument('--java',default='java')
    p.add_argument('--java-home',help='Optional javac java.home override for a local extracted JDK')
    p.add_argument('--output',type=Path,default=ROOT/'tests/policy-validation.json')
    a=p.parse_args();javac=shutil.which(a.javac);java=shutil.which(a.java)
    if not javac or not java:
        print(json.dumps({'status':'BLOCKED_BY_TOOLCHAIN','reason':'Both javac and java are required'}));return 2
    sources=[ROOT/'src/main/java/org/example/gleslab/HdrOutputPolicy.java',ROOT/'src/main/java/org/example/gleslab/SharedLease.java',ROOT/'tests/HdrOutputPolicyTest.java',ROOT/'tests/SharedLeaseTest.java']
    with tempfile.TemporaryDirectory(prefix='hdr-policy-') as temp:
        command=[javac]+(['-J-Djava.home='+a.java_home] if a.java_home else [])+['--release','17','-d',temp,*map(str,sources)]
        compiled=subprocess.run(command,capture_output=True,text=True,timeout=60)
        executed=None
        lease=None
        if compiled.returncode==0:
            executed=subprocess.run([java,'-cp',temp,'org.example.gleslab.HdrOutputPolicyTest'],capture_output=True,text=True,timeout=60)
            lease=subprocess.run([java,'-cp',temp,'org.example.gleslab.SharedLeaseTest'],capture_output=True,text=True,timeout=60)
        report={'scope':'Real Java17 language/API compile and host policy execution; not Android display/EGL execution',
                'source_sha256':{str(s.relative_to(ROOT)):hashlib.sha256(s.read_bytes()).hexdigest() for s in sources},
                'compile_exit':compiled.returncode,'compile_stdout':compiled.stdout,'compile_stderr':compiled.stderr,
                'execution_exit':None if executed is None else executed.returncode,
                'execution_stdout':None if executed is None else executed.stdout,
                'execution_stderr':None if executed is None else executed.stderr,
                'lease_execution_exit':None if lease is None else lease.returncode,
                'lease_execution_stdout':None if lease is None else lease.stdout,
                'lease_execution_stderr':None if lease is None else lease.stderr,
                'android_display_runtime':'NOT_RUN','apk_build':'NOT_RUN'}
        report['status']='PASS' if compiled.returncode==0 and executed is not None and executed.returncode==0 and lease is not None and lease.returncode==0 else 'FAIL'
        a.output.parent.mkdir(parents=True,exist_ok=True);a.output.write_text(json.dumps(report,indent=2)+'\n')
        print(json.dumps({'status':report['status'],'output':str(a.output)}));return 0 if report['status']=='PASS' else 1
if __name__=='__main__':raise SystemExit(main())
