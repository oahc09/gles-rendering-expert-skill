#!/usr/bin/env python3
"""Bounded ESSL grammar mutations; standalone compiler evidence, never GPU evidence."""
import argparse
from dataclasses import dataclass
import hashlib
import importlib.util
import json
import math
import os
import re
from pathlib import Path
import shutil
import signal
import subprocess
import sys
import tempfile
import time
from validate_shaders import expected_result

ROOT = Path(__file__).resolve().parents[1]
MUTATIONS = ('identity', 'exact_fold', 'local_binding', 'dead_branch')

@dataclass(frozen=True)
class Literal:
    """Restricted typed AST: exactly representable finite positive float literals."""
    value: int
    def emit(self):
        if not 1 <= self.value <= 16:
            raise ValueError('literal outside proven exact range')
        return f'{self.value}.0'

@dataclass(frozen=True)
class Add:
    left: Literal
    right: Literal
    def emit(self):
        return f'({self.left.emit()} + {self.right.emit()})'
    def fold(self):
        return f'{self.left.value + self.right.value}.0'

def corpus(seed=0):
    """Closed grammar, not a general parser. No arbitrary source substitution."""
    if not 0 <= seed <= 2**32-1:
        raise ValueError('seed must be uint32')
    cases = []
    expr = Add(Literal(1 + seed % 8), Literal(1 + (seed // 8) % 8))
    for version in (300, 310, 320):
        header = f'#version {version} es\nprecision highp float;\nprecision highp int;\n'
        for family in ('scalar', 'vector', 'function', 'ubo', 'sampler'):
            for mutation in MUTATIONS:
                value = expr.fold() if mutation == 'exact_fold' else expr.emit()
                prefix = f'float localValue = {value};\n' if mutation == 'local_binding' else ''
                if mutation == 'local_binding': value = 'localValue'
                suffix = 'if (false) { color = vec4(0.0); }\n' if mutation == 'dead_branch' else ''
                decl = 'layout(location=0) out vec4 color;\n'
                if family == 'scalar': body = f'color = vec4({value});'
                elif family == 'vector': body = f'vec2 pair = vec2({value}); color = vec4(pair, pair);'
                elif family == 'function':
                    decl += 'float identityValue(float x) { return x; }\n'
                    body = f'color = vec4(identityValue({value}));'
                elif family == 'ubo':
                    decl += 'layout(std140) uniform Params { vec4 tint; };\n'
                    body = f'color = tint * {value};'
                else:
                    decl += 'uniform highp sampler2D tex;\n'
                    body = f'color = texture(tex, vec2(0.5)) * {value};'
                cases.append(dict(id=f'{version}-{family}-{mutation}', version=version, family=family,
                    mutation=mutation, expected='accept', rule='Exact integer float addition in [2,16]; local binding and unreachable branch preserve the expression and all resource operations.',
                    sources={'shader.frag': header+decl+'void main() {\n'+prefix+body+'\n'+suffix+'}\n'}))
        # Each negative has one deterministic compile/link violation, never a runtime OOB.
        invalid = {
            'type': ('shader.frag', 'layout(location=0) out vec4 color; void main() { color = mat4(1.0); }', 'Assignment types must match'),
            'precision': ('shader.frag', 'layout(location=0) out vec4 color; void main() { color=vec4(1.0); }', 'Fragment float requires a default or explicit precision'),
            'sampler': ('shader.frag', 'uniform sampler2D tex; layout(location=0) out vec4 color; void main() { color=texture(tex, vec3(0.0)); }', 'sampler2D texture coordinates must be vec2'),
            'extension': ('shader.frag', '#extension GL_NONEXISTENT_fuzz_extension : require\nvoid main() {}', 'Unsupported required extension must be rejected'),
            'array_size': ('shader.frag', 'float values[-1]; void main() {}', 'Array sizes must be positive integral constants'),
        }
        for name, (file, body, rule) in invalid.items():
            h = f'#version {version} es\n' if name == 'precision' else header
            cases.append(dict(id=f'{version}-invalid-{name}',version=version,family=name,mutation='invalid',expected='reject',rule=rule,sources={file:h+body+'\n'}))
        cases.append(dict(id=f'{version}-invalid-varying',version=version,family='varying',mutation='invalid',expected='reject',rule='Statically used linked varying types must agree',sources={
            'shader.vert':header+'out vec3 bridge; void main() { bridge=vec3(1.0); gl_Position=vec4(0.0,0.0,0.0,1.0); }\n',
            'shader.frag':header+'in vec4 bridge; layout(location=0) out vec4 color; void main() { color=bridge; }\n'}))
        for family, body in {
            'ssbo': 'layout(std430,binding=0) buffer Data { uint value; }; void main() { value=1u; }',
            'image': 'layout(r32ui,binding=0) uniform highp uimage2D target; void main() { imageStore(target,ivec2(0),uvec4(1u)); }',
            'atomic': 'shared uint value; void main() { value=0u; barrier(); atomicAdd(value,1u); }',
        }.items():
            cases.append(dict(id=f'{version}-compute-{family}',version=version,family=family,mutation='version_boundary',expected='reject' if version==300 else 'accept',rule='Compute, SSBO, image and shared atomic operations require ESSL 310 or later; one invocation, no race.',sources={'shader.comp':header+'layout(local_size_x=1) in;\n'+body+'\n'}))
        if version >= 310:
            cases.append(dict(id=f'{version}-invalid-workgroup-limit',version=version,family='compute_limit',mutation='invalid',expected='reject',rule='Local workgroup dimension exceeds the glslang built-in static resource limit; compiler-profile oracle only, not a universal device limit.',sources={'shader.comp':header+'layout(local_size_x=2147483647) in; void main() {}\n'}))
    return cases

def isolated(command, timeout, memory_mb=512, log_bytes=65536, env=None):
    """Separate process group; kernel CPU/address-space/file quotas on POSIX."""
    if os.name != 'posix':
        return dict(status='UNSUPPORTED', exit_code=None, log='POSIX resource isolation required')
    import resource
    def limits():
        resource.setrlimit(resource.RLIMIT_AS, (memory_mb*1024**2, memory_mb*1024**2))
        resource.setrlimit(resource.RLIMIT_CPU, (max(1, math.ceil(timeout)), max(2, math.ceil(timeout)+1)))
        resource.setrlimit(resource.RLIMIT_FSIZE, (log_bytes, log_bytes))
        resource.setrlimit(resource.RLIMIT_CORE, (0, 0))
    with tempfile.TemporaryFile() as log:
        try:
            p = subprocess.Popen(command, stdout=log, stderr=log, start_new_session=True, preexec_fn=limits, env=env)
            status = 'EXITED'
            try: p.wait(timeout=timeout)
            except subprocess.TimeoutExpired:
                status = 'TEST_TIMEOUT'
            finally:
                # The leader can exit while descendants still own our stdout/file
                # descriptors. Kill its entire group on success and failure too.
                try: os.killpg(p.pid, signal.SIGKILL)
                except ProcessLookupError: pass
                p.wait()
            log.seek(0)
            return dict(status=status, exit_code=p.returncode, log=log.read(log_bytes).decode('utf-8','replace'))
        except OSError as e:
            return dict(status='HARNESS_FAILURE',exit_code=None,log=str(e))

def classify(result, expected):
    if result['status'] != 'EXITED': return result['status']
    if result['exit_code'] in (-signal.SIGXCPU, -signal.SIGXFSZ): return 'RESOURCE_LIMIT'
    if result['exit_code'] < 0: return 'COMPILER_FAILURE'
    if expected_result(result['exit_code'],expected=='accept',result['log']):
        return 'PASS' if expected=='accept' else 'EXPECTED_ERROR'
    return 'MISMATCH' if result['exit_code'] in (0,2,3) else 'HARNESS_FAILURE'

def run_case(case, compiler, directory, timeout, memory_mb, max_bytes):
    directory.mkdir(parents=True,exist_ok=True)
    files=[]; hashes={}
    for name, source in case['sources'].items():
        if len(source.encode()) > max_bytes:
            return {'id':case['id'], 'status':'RESOURCE_LIMIT', 'exit_code':None, 'log':'shader length quota exceeded'}
        path=directory/name; path.write_text(source); files.append(str(path.resolve()))
        hashes[name]=hashlib.sha256(source.encode()).hexdigest()
    command=[compiler]+(['-l'] if len(files)>1 else [])+files
    result=isolated(command,timeout,memory_mb)
    result['status']=classify(result,case['expected'])
    return {**{k:v for k,v in case.items() if k!='sources'},**result,'sha256':hashes,'command':command,'artifacts':str(directory),'output_image':None}

def reduce_failure(case, compiler, timeout, budget, out, memory_mb=512):
    """Reuse v1.0.6 ddmin; preserve exact first diagnostic, not arbitrary rejection."""
    if len(case['sources']) != 1: return {'status':'UNSUPPORTED_LINK_REDUCTION'}
    name,source=next(iter(case['sources'].items()))
    deadline=time.monotonic()+budget
    initial=isolated([compiler,str((out/name).resolve())],min(timeout,budget),memory_mb)
    signature=next((re.sub(r'^ERROR: [^:]+:[0-9]+: ', '', s) for s in initial['log'].splitlines() if s.startswith('ERROR:') and 'compilation errors' not in s),None)
    if not signature or initial['exit_code'] not in (2,3): return {'status':'NO_STABLE_DIAGNOSTIC'}
    spec=importlib.util.spec_from_file_location('existing_reducer',ROOT/'benchmarks/reducer/reduce.py')
    module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
    def oracle(candidate):
        if not candidate.startswith(source.splitlines()[0]+'\n') or time.monotonic()>=deadline:
            return {'matches':False,'error_type':'DomainOrBudgetLimit'}
        path=out/('candidate'+Path(name).suffix);path.write_text(candidate)
        r=isolated([compiler,str(path.resolve())],min(timeout,max(.01,deadline-time.monotonic())),memory_mb)
        return {'matches':r['status']=='EXITED' and r['exit_code'] in (2,3) and signature in r['log'],'exit_code':r['exit_code'],'diagnostic':r['log'],'compiler_crash':r['exit_code'] is not None and r['exit_code']<0,**({'error_type':r['status']} if r['status']!='EXITED' else {})}
    reduced=module.minimize(source,oracle,max_attempts=40)
    (out/('reduced'+Path(name).suffix)).write_text(reduced.pop('source'))
    return {'predicate':signature,**reduced}

def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--seed',type=int,default=0);p.add_argument('--case')
    p.add_argument('--compiler',default='glslangValidator');p.add_argument('--output',type=Path,default=Path('reports/fuzz'))
    p.add_argument('--timeout',type=float,default=3);p.add_argument('--budget',type=float,default=90)
    p.add_argument('--max-shader-bytes',type=int,default=16384);p.add_argument('--memory-mb',type=int,default=512)
    p.add_argument('--emit-only',action='store_true');p.add_argument('--reduce',action='store_true')
    a=p.parse_args()
    if not (0<a.timeout<=30 and 0<a.budget<=600 and 128<=a.memory_mb<=2048 and 512<=a.max_shader_bytes<=65536): p.error('limits outside safe bounds')
    if not 0 <= a.seed <= 2**32-1: p.error('seed must be uint32')
    cases=corpus(a.seed)
    if a.case:
        cases=[c for c in cases if c['id']==a.case]
        if not cases: p.error('unknown case ID')
    a.output.mkdir(parents=True,exist_ok=True)
    compiler=shutil.which(a.compiler);results=[];deadline=time.monotonic()+a.budget
    identity=isolated([compiler,'--version'],min(a.timeout,a.budget),a.memory_mb) if compiler and not a.emit_only else None
    for case in cases:
        directory=a.output/case['id']
        if a.emit_only:
            directory.mkdir(parents=True,exist_ok=True)
            for name,source in case['sources'].items(): (directory/name).write_text(source)
            r={k:v for k,v in case.items() if k!='sources'};r['status']='NOT_RUN'
        elif not compiler: r={'id':case['id'],'status':'BLOCKED_BY_TOOLCHAIN'}
        elif time.monotonic()>=deadline:r={'id':case['id'],'status':'BUDGET_EXHAUSTED'}
        else:
            r=run_case(case,compiler,directory,min(a.timeout,deadline-time.monotonic()),a.memory_mb,a.max_shader_bytes)
            if a.reduce and r['status']=='MISMATCH' and case['expected']=='accept' and time.monotonic()<deadline:
                r['reduction']=reduce_failure(case,compiler,a.timeout,deadline-time.monotonic(),directory,a.memory_mb)
        r['replay']=[sys.executable,'tools/shader_fuzz.py','--seed',str(a.seed),'--case',case['id'],'--compiler',compiler or a.compiler,'--output',str(a.output/'replay')]
        results.append(r)
    status='NOT_RUN' if a.emit_only else ('PASS' if identity and identity['status']=='EXITED' and identity['exit_code']==0 and all(r['status'] in ('PASS','EXPECTED_ERROR') for r in results) else 'INCOMPLETE' if any(r['status'] in ('BLOCKED_BY_TOOLCHAIN','BUDGET_EXHAUSTED','UNSUPPORTED') for r in results) else 'FAIL')
    report={'schema_version':1,'status':status,'seed':a.seed,'scope':'glslang standalone compile/link only; no GLES driver, GPU execution, image or performance evidence', 'device':None,'extensions':None,'generator_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),'compiler':compiler,'compiler_version':identity,'compiler_sha256':hashlib.sha256(Path(compiler).read_bytes()).hexdigest() if compiler else None,'limits':{'timeout_seconds':a.timeout,'budget_seconds':a.budget,'memory_mb':a.memory_mb,'max_shader_bytes':a.max_shader_bytes},'cases':results}
    (a.output/'report.json').write_text(json.dumps(report,indent=2)+'\n')
    (a.output/'report.md').write_text('# Bounded shader fuzz\n\n'+report['scope']+'\n\nStatus: '+status+'\n\n'+'\n'.join(f"- {r['id']}: {r['status']}" for r in results)+'\n')
    print(json.dumps({'status':status,'cases':len(results),'report':str(a.output/'report.json')}))
    return 0 if status in ('PASS','NOT_RUN') else 2 if status=='INCOMPLETE' else 1

if __name__=='__main__':raise SystemExit(main())
