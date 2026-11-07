#!/usr/bin/env python3
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import shutil
import sys
import tempfile
import unittest

ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'tools'))
import shader_fuzz as fuzz

class CorpusTests(unittest.TestCase):
    def test_stable_unique_corpus(self):
        cases=fuzz.corpus()
        self.assertEqual(cases,fuzz.corpus())
        self.assertEqual(len(cases),89)
        self.assertEqual(len({c['id'] for c in cases}),89)
        self.assertEqual(len({json.dumps(c['sources'],sort_keys=True) for c in cases}),89)
        self.assertEqual(sum(c['mutation'] in fuzz.MUTATIONS for c in cases),60)
        for case in cases:
            for name,source in case['sources'].items():
                self.assertEqual(source,(ROOT/'benchmarks/fuzz/shaders'/case['id']/name).read_text())
                self.assertTrue(source.startswith(f"#version {case['version']} es\n"))
                self.assertLess(len(source),16384)
    def test_checked_report_schema(self):
        try: import jsonschema
        except ImportError: self.skipTest('optional jsonschema not installed')
        report=ROOT/'benchmarks/fuzz/evidence/glslang-15.2.0/report.json'
        if not report.exists(): self.skipTest('checked compiler report not available')
        jsonschema.validate(json.loads(report.read_text()),json.loads((ROOT/'benchmarks/fuzz/report.schema.json').read_text()))
    def test_seed_and_proof_bounds(self):
        for seed in (0,1,63,2**32-1):
            for case in fuzz.corpus(seed): self.assertTrue(case['rule'])
        self.assertNotEqual(fuzz.corpus(0),fuzz.corpus(1))
        for seed in (-1,2**32):
            with self.assertRaises(ValueError): fuzz.corpus(seed)
        for value in (-1,0,17):
            with self.assertRaises(ValueError): fuzz.Literal(value).emit()
    def test_expected_errors_are_not_crashes(self):
        for code,log,expected in [(2,'ERROR: bad','EXPECTED_ERROR'),(3,'ERROR: bad','EXPECTED_ERROR'),(1,'ERROR: bad','HARNESS_FAILURE'),(-11,'ERROR: bad','COMPILER_FAILURE'),(2,'no diagnosis','MISMATCH'),(0,'','MISMATCH')]:
            self.assertEqual(fuzz.classify({'status':'EXITED','exit_code':code,'log':log},'reject'),expected)
        self.assertEqual(fuzz.classify({'status':'TEST_TIMEOUT'},'reject'),'TEST_TIMEOUT')
    def test_source_quota(self):
        with tempfile.TemporaryDirectory() as d:
            r=fuzz.run_case(fuzz.corpus()[0],'/not/a/compiler',Path(d),1,512,1)
            self.assertEqual(r['status'],'RESOURCE_LIMIT')
    @unittest.skipUnless(os.name=='posix','requires POSIX quotas')
    def test_timeout_and_isolation(self):
        r=fuzz.isolated([sys.executable,'-c','import time;time.sleep(10)'],.1)
        self.assertEqual(r['status'],'TEST_TIMEOUT')
        r=fuzz.isolated([sys.executable,'-c','import os;os.kill(os.getpid(),11)'],1)
        self.assertEqual(fuzz.classify(r,'reject'),'COMPILER_FAILURE')
        r=fuzz.isolated(['/not/a/compiler'],1)
        self.assertEqual(r['status'],'HARNESS_FAILURE')
    @unittest.skipUnless(os.name=='posix','requires POSIX quotas')
    def test_output_and_memory_bounded(self):
        r=fuzz.isolated([sys.executable,'-c','import os;os.write(1,b"x"*1000000)'],1,log_bytes=4096)
        self.assertLessEqual(len(r['log']),4096)
        r=fuzz.isolated([sys.executable,'-c','x=bytearray(1024**3)'],1,memory_mb=128)
        self.assertNotEqual(r['exit_code'],0)
    @unittest.skipUnless(os.name=='posix','requires POSIX process groups')
    def test_grandchildren_cleaned_on_all_exits(self):
        import time
        for mode in ('success','failure','timeout'):
            with self.subTest(mode=mode), tempfile.TemporaryDirectory() as d:
                marker=Path(d)/'escaped';ready=Path(d)/'spawned'
                descendant=f"import time,pathlib;time.sleep(.5);pathlib.Path({str(marker)!r}).write_text('leaked')"
                tail="time.sleep(2)" if mode=='timeout' else f"sys.exit({0 if mode=='success' else 1})"
                source=f"import subprocess,sys,time,pathlib;subprocess.Popen([sys.executable,'-c',{descendant!r}]);pathlib.Path({str(ready)!r}).write_text('spawned');{tail}"
                result=fuzz.isolated([sys.executable,'-c',source],.2 if mode=='timeout' else 1)
                self.assertTrue(ready.exists(),'test did not spawn its descendant')
                self.assertEqual(result['status'],'TEST_TIMEOUT' if mode=='timeout' else 'EXITED')
                time.sleep(.65)
                self.assertFalse(marker.exists(),'descendant survived process-group cleanup')

    def test_missing_tool_is_not_pass(self):
        with tempfile.TemporaryDirectory() as d:
            import subprocess
            p=subprocess.run([sys.executable,str(ROOT/'tools/shader_fuzz.py'),'--compiler','/missing-compiler','--output',d],capture_output=True)
            self.assertEqual(p.returncode,2)
            report=json.loads((Path(d)/'report.json').read_text())
            self.assertEqual(report['status'],'INCOMPLETE')
            self.assertTrue(all(c['status']=='BLOCKED_BY_TOOLCHAIN' for c in report['cases']))
    @unittest.skipUnless(os.environ.get('GLSLANG_VALIDATOR') or shutil.which('glslangValidator'),'real compiler unavailable')
    def test_real_compiler_corpus(self):
        compiler=os.environ.get('GLSLANG_VALIDATOR') or shutil.which('glslangValidator')
        with tempfile.TemporaryDirectory() as d:
            for case in fuzz.corpus():
                with self.subTest(case=case['id']):
                    r=fuzz.run_case(case,compiler,Path(d)/case['id'],3,512,16384)
                    self.assertIn(r['status'],('PASS','EXPECTED_ERROR'),r)

    @unittest.skipUnless(os.environ.get('GLSLANG_VALIDATOR') or shutil.which('glslangValidator'),'real compiler unavailable')
    def test_existing_reducer_reuse(self):
        compiler=os.environ.get('GLSLANG_VALIDATOR') or shutil.which('glslangValidator')
        case=next(c for c in fuzz.corpus() if c['id']=='300-invalid-type')
        with tempfile.TemporaryDirectory() as d:
            out=Path(d)
            fuzz.run_case(case,compiler,out,3,512,16384)
            r=fuzz.reduce_failure(case,compiler,3,10,out)
            self.assertEqual(r['status'],'REPRODUCED',r)
            self.assertTrue(r['trials'][0]['matches'])
            self.assertLessEqual(len(r['trials']),40)
            self.assertTrue((out/'reduced.frag').exists())

if __name__=='__main__':unittest.main()
