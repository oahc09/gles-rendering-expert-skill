#!/usr/bin/env python3
"""Bounded W2/W3 runner. JSON/Markdown retain model versus driver evidence."""
import argparse
import hashlib
from datetime import datetime, timezone
import importlib.util
import io
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
ROOT=Path(__file__).resolve().parents[2]

def load(name,path):
    spec=importlib.util.spec_from_file_location(name,path);module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module);return module

def run(library,host=True):
    policy=load('robust_policy',Path(__file__).with_name('policy.py'))
    model=load('state_model',ROOT/'benchmarks/state_machine/model.py')
    test=load('robustness_tests',Path(__file__).with_name('test_robustness.py'))
    suite=unittest.defaultTestLoader.loadTestsFromModule(test);ids=[]
    def collect(s):
        for t in s:
            if isinstance(t,unittest.TestSuite):collect(t)
            else:ids.append(t.id())
    collect(suite);stream=io.StringIO();tests=unittest.TextTestRunner(stream=stream,verbosity=2).run(suite)
    failed={t.id():msg for t,msg in tests.failures+tests.errors}
    rows=[dict(id='ROB-%03d'%(i+1),test=t,status='FAIL' if t in failed else 'PASS',evidence='HOST_PYTHON_EXECUTED',diagnostic=failed.get(t,'')) for i,t in enumerate(ids)]
    state=model.run();host_report={'status':'UNSUPPORTED','reason':'host execution explicitly disabled'}
    if host:
        with tempfile.TemporaryDirectory(prefix='gles-adversarial-') as tmp:
            out=Path(tmp)/'host.json';env=os.environ.copy();env.setdefault('MESA_SHADER_CACHE_DIR',str(Path(tmp)/'cache'))
            try:
                p=policy.isolated([sys.executable,str(ROOT/'benchmarks/state_machine/host.py'),'--gles-library',library,'--output',str(out)],timeout=30,memory_mb=4096,env=env)
                host_report=json.loads(out.read_text()) if out.exists() else {'status':'HARNESS_FAILURE','reason':'missing child report'}
                host_report.update(exit_code=p['exit_code'],stderr=p['log'])
                if p['status']!='PASS': host_report.update(status=p['status'],reason='bounded host child did not complete successfully; not diagnosed driver failure')
            except subprocess.TimeoutExpired:host_report={'status':'TEST_TIMEOUT','reason':'host child killed/reaped after 30 seconds; not diagnosed GPU hang'}
            except (OSError,ValueError):host_report={'status':'HARNESS_FAILURE','reason':'invalid child output or launch failure'}
    sources=[*Path(__file__).parent.glob('*.py'),*(ROOT/'benchmarks/state_machine').glob('*.py'),ROOT/'benchmarks/reducer/reduce.py',ROOT/'tools/shader_fuzz.py',ROOT/'tools/validate_shaders.py']
    passed=tests.wasSuccessful() and state['status']=='PASS' and host_report['status']=='PASS'
    return dict(timestamp=datetime.now(timezone.utc).isoformat(),gles_library_sha256=hashlib.sha256(Path(library).read_bytes()).hexdigest() if Path(library).is_file() else None,schema_version=1,status='PASS' if passed else 'INCOMPLETE',scope='bounded host and explicit model evidence; not mobile certification',source_sha256={str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest() for p in sources},cases=rows,state_machine=state,host=host_report,unittest_log=stream.getvalue(),device_status='BLOCKED_BY_HARDWARE',actual_device_reset=False)

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--output',type=Path,required=True);p.add_argument('--gles-library',default='libGLESv2.so.2');p.add_argument('--no-host',action='store_true');a=p.parse_args()
    r=run(a.gles_library,not a.no_host);a.output.mkdir(parents=True,exist_ok=True);(a.output/'report.json').write_text(json.dumps(r,indent=2)+'\n')
    (a.output/'report.md').write_text('# W2/W3 bounded validation\n\nStatus: '+r['status']+'\n\n- Offline state cases: '+str(len(r['state_machine']['cases']))+'\n- Authored, reduced faults: '+str(len(r['state_machine']['faults']))+'\n- Robustness unit cases: '+str(len(r['cases']))+'\n- Actual host status: '+r['host']['status']+'\n- Physical device: BLOCKED_BY_HARDWARE\n- No physical device reset was triggered.\n')
    print(json.dumps({'status':r['status'],'report':str(a.output/'report.json')}));raise SystemExit(0 if r['status']=='PASS' else 1)
