"""Explicit ownership/lifetime oracle; not an implementation of the GL specification."""
import importlib.util
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
spec = importlib.util.spec_from_file_location('existing_reducer', ROOT/'benchmarks/reducer/reduce.py')
reducer = importlib.util.module_from_spec(spec)
spec.loader.exec_module(reducer)
DOMAINS = ('texture', 'renderbuffer', 'framebuffer', 'vao', 'vbo', 'ubo', 'program', 'pipeline', 'sync', 'query', 'pbo')
LOCAL = {'framebuffer', 'vao', 'pipeline', 'query'}

class Model:
    def __init__(self, fault=None):
        self.objects = {}; self.bindings = {}; self.generation = 1
        self.context = 'a'; self.thread = 'render'; self.surface = True
        self.fault = fault

    def step(self, command):
        op, *args = command.split(':')
        if op == 'noise': return 'PASS'
        if op == 'unbind_thread': self.thread = None; return 'PASS'
        if op == 'bind_thread':
            if self.thread is not None: return 'EXPECTED_ERROR'
            self.thread = 'worker'; return 'PASS'
        if op == 'surface_loss': self.surface = False; return 'EXPECTED_ERROR'
        if op == 'surface_restore': self.surface = True; return 'PASS'
        if op == 'swap': return 'PASS' if self.surface else 'EXPECTED_ERROR'
        if op == 'reset':
            self.generation += 1
            if self.fault != 'reset': self.objects.clear(); self.bindings.clear()
            return 'PASS'
        if op == 'switch': self.context = args[0]; return 'PASS'
        if op == 'undefined': return 'UNDEFINED'
        if op == 'reuse_name': return 'IMPLEMENTATION_DEPENDENT'
        if op == 'bad_display': return 'EXPECTED_ERROR'
        domain = args[0]; key = (domain, '1')
        if op == 'create':
            self.objects[key] = (self.context, self.generation); return 'PASS'
        if op == 'delete':
            self.objects.pop(key, None)
            if self.fault != domain: self.bindings.pop(key, None)
            return 'PASS'
        if op == 'bind':
            if key not in self.objects: return 'EXPECTED_ERROR'
            owner, generation = self.objects[key]
            if generation != self.generation: return 'EXPECTED_ERROR'
            if domain in LOCAL and owner != self.context: return 'EXPECTED_ERROR'
            self.bindings[key] = self.context; return 'PASS'
        if op == 'audit':
            # Application cache invariant, not a claim that every GL object detaches everywhere.
            return 'HARNESS_FAILURE' if any(k not in self.objects or self.objects[k][1] != self.generation for k in self.bindings) else 'PASS'
        raise ValueError('Unknown model operation: '+command)

def replay(sequence, fault=None):
    if not isinstance(sequence,list) or len(sequence)>128 or any(not isinstance(x,str) or len(x)>128 for x in sequence):
        raise ValueError('bounded operation list required')
    m = Model(fault)
    return [m.step(command) for command in sequence]

def cases():
    result=[]
    def add(label, domain, seq, expected, rule):
        result.append(dict(id='SM-%03d' % (len(result)+1), label=label, domain=domain,
                           sequence=seq, expected=expected, oracle=rule, evidence='MODEL_EXECUTED'))
    for d in DOMAINS:
        add(d+' create/bind',d,['create:'+d,'bind:'+d],['PASS','PASS'],'live object allowed by application ownership policy')
        add(d+' delete/cache invalidation',d,['create:'+d,'bind:'+d,'delete:'+d,'audit:'+d],['PASS']*4,'deleted object cannot remain in application binding cache')
        add(d+' delete/rebuild',d,['create:'+d,'delete:'+d,'create:'+d,'bind:'+d],['PASS']*4,'recreated owned object may be rebound')
    for d in sorted(LOCAL):
        add(d+' cross-context ownership',d,['create:'+d,'switch:b','bind:'+d],['PASS','PASS','EXPECTED_ERROR'],'application policy rejects nonshared container misuse; not a GL error assertion')
    extras=[('thread handoff',['unbind_thread','bind_thread'],['PASS','PASS']),('thread double bind',['bind_thread'],['EXPECTED_ERROR']),('surface loss',['surface_loss','swap','surface_restore','swap'],['EXPECTED_ERROR','EXPECTED_ERROR','PASS','PASS']),('wrong display',['bad_display'],['EXPECTED_ERROR']),('simulated context loss',['create:texture','bind:texture','reset','audit:texture'],['PASS']*4),('uninitialized read',['undefined'],['UNDEFINED']),('numeric name reuse',['reuse_name'],['IMPLEMENTATION_DEPENDENT'])]
    for label,seq,expected in extras: add(label,'EGL/lifecycle',seq,expected,'controlled model only; undefined and implementation-dependent cases are not executed on GPU')
    return result

def minimize_fault(domain):
    seq=['noise','create:'+domain,'bind:'+domain,'noise','delete:'+domain,'audit:'+domain,'noise']
    def oracle(source):
        try:
            observed=replay(source.splitlines(),domain)
            return {'matches':'HARNESS_FAILURE' in observed,'diagnostic':'stale application cache '+domain,'compiler_crash':False}
        except (ValueError,IndexError): return {'matches':False,'diagnostic':'invalid sequence','compiler_crash':False}
    reduced=reducer.minimize('\n'.join(seq)+'\n',oracle,max_attempts=100)
    minimal=reduced.pop('source').splitlines()
    return dict(domain=domain, injected=True, fault='stale application cache', actual_device_reset=False,
                original=seq, minimal=minimal, repetitions=[replay(minimal,domain) for _ in range(3)],
                corrected=replay(minimal), minimality_domain='operation deletion, fixed injected cache fault', **reduced)

def run():
    rows=[]
    for case in cases():
        observed=replay(case['sequence'])
        rows.append({**case,'observed':observed,'status':'PASS' if observed==case['expected'] else 'FAIL'})
    faults=[minimize_fault(d) for d in DOMAINS]
    ok=all(x['status']=='PASS' for x in rows) and all(x['one_minimal'] and all(r[-1]=='HARNESS_FAILURE' for r in x['repetitions']) and x['corrected'][-1]=='PASS' for x in faults)
    return dict(schema_version=1,scope='offline explicit application state model and deterministic injected faults; not driver conformance',status='PASS' if ok else 'FAIL', cases=rows,faults=faults,device_status='BLOCKED_BY_HARDWARE')

if __name__=='__main__':
    import argparse
    p=argparse.ArgumentParser();p.add_argument('--output',type=Path);p.add_argument('--replay',type=Path);p.add_argument('--fault',choices=DOMAINS);a=p.parse_args()
    if a.replay and a.replay.stat().st_size>32768: p.error('replay exceeds 32 KiB')
    result={'observed':replay(json.loads(a.replay.read_text()),a.fault)} if a.replay else run()
    raw=json.dumps(result,indent=2)+'\n'
    if a.output: a.output.parent.mkdir(parents=True,exist_ok=True);a.output.write_text(raw)
    else: print(raw)
