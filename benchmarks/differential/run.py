#!/usr/bin/env python3
"""Bounded real-driver differential suite. No modelled results count as execution."""
from datetime import datetime, timezone
import argparse, ctypes as C, hashlib, importlib.util, json, math, os, platform, re, subprocess, sys, tempfile
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'tools'))
import shader_fuzz

def module(name,path):
    spec=importlib.util.spec_from_file_location(name,path);m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m);return m
reducer=module('diff_reducer',ROOT/'benchmarks/reducer/reduce.py')
pipeline=module('diff_pipeline',ROOT/'benchmarks/pipeline/runtime.py')
U=C.c_uint; I=C.c_int; P=C.c_void_p; F=C.c_float

def digest(path): return hashlib.sha256(Path(path).read_bytes()).hexdigest()
def cases():
    out=[]
    for c in shader_fuzz.corpus(7):
        if c['version']==300 and 'compute' not in c['id']:
            out.append(dict(c,kind='shader',expected_compile=c['expected']=='accept' or c['family']=='varying',expected_link=c['expected']=='accept'))
    api=[('viewport-valid','glViewport',[0,0,4,4],0),('viewport-negative','glViewport',[0,0,-1,4],0x501),('scissor-negative','glScissor',[0,0,-1,4],0x501),('pack-valid','glPixelStorei',[0xd05,4],0),('pack-invalid','glPixelStorei',[0xd05,3],0x501),('enable-invalid','glEnable',[0xdead],0x500),('clear-valid','glClear',[0x4000],0),('clear-invalid','glClear',[1],0x501),('buffer-target-invalid','glBindBuffer',[0xdead,0],0x500),('texture-target-invalid','glBindTexture',[0xdead,0],0x500),('unbind-program','glUseProgram',[0],0)]
    for name,fn,args,expected in api:out.append(dict(id=name,kind='api_error',function=fn,args=args,expected=expected))
    for name,color in [('black',[0,0,0,1]),('white',[1,1,1,1]),('primaries',[1,0,.5,1]),('fractions',[.1,.2,.3,.4]),('clamp',[-1,2,.25,1]),('midpoint',[.5,.5,.5,1])]:
        out.append(dict(id='fbo-'+name,kind='fbo_pixels',color=color,expected=[pipeline.quantize(x) for x in color],tolerance=1))
    for name,expression,expected in [('add','2.0+3.0',5),('multiply','1.25*4.0',5),('divide','1.0/4.0',.25),('sqrt','sqrt(4.0)',2)]:
        source='#version 310 es\nprecision highp float;\nlayout(local_size_x=1) in;\nlayout(std430,binding=0) buffer Data { float value; };\nvoid main() { value='+expression+'; }\n'
        out.append(dict(id='ssbo-'+name,kind='ssbo_numeric',version=310,sources={'shader.comp':source},expected=expected,absolute_tolerance=1e-6,relative_tolerance=1e-6))
    return out

class Host:
    def fn(self,name,restype,args,egl=False):
        f=getattr(self.egl if egl else self.gl,name);f.restype=restype;f.argtypes=args;return f
    def __init__(self,config):
        os.environ['LP_NUM_THREADS']='2';os.environ['OMP_NUM_THREADS']='2'
        if config['kind']=='mesa':os.environ['EGL_PLATFORM']='surfaceless';os.environ['LIBGL_ALWAYS_SOFTWARE']='1'
        else:os.environ['VK_ICD_FILENAMES']=config['icd']
        self.egl=C.CDLL(config['egl']);self.gl=C.CDLL(config['gles'])
        if config['kind']=='angle':
            proc=self.fn('eglGetProcAddress',P,[C.c_char_p],True)(b'eglGetPlatformDisplayEXT')
            if not proc:raise RuntimeError('ANGLE platform entrypoint missing')
            self.d=C.CFUNCTYPE(P,U,P,C.POINTER(I))(proc)(0x3202,None,(I*5)(0x3203,0x3450,0x3209,0x3487,0x3038))
        else:self.d=self.fn('eglGetDisplay',P,[P],True)(None)
        if not self.fn('eglInitialize',U,[P,P,P],True)(self.d,None,None):raise RuntimeError('eglInitialize failed')
        cfg=P();n=I()
        attrs=(I*13)(0x3033,1,0x3040,0x40,0x3024,8,0x3023,8,0x3022,8,0x3021,8,0x3038)
        if not self.fn('eglChooseConfig',U,[P,C.POINTER(I),C.POINTER(P),I,C.POINTER(I)],True)(self.d,attrs,C.byref(cfg),1,C.byref(n)) or not n.value:raise RuntimeError('GLES3 config missing')
        self.c=self.fn('eglCreateContext',P,[P,P,P,C.POINTER(I)],True)(self.d,cfg,None,(I*3)(0x3098,3,0x3038))
        self.s=self.fn('eglCreatePbufferSurface',P,[P,P,C.POINTER(I)],True)(self.d,cfg,(I*5)(0x3057,4,0x3056,4,0x3038))
        if not self.c or not self.s or not self.fn('eglMakeCurrent',U,[P,P,P,P],True)(self.d,self.s,self.s,self.c):raise RuntimeError('context/surface unavailable')
        gs=self.fn('glGetString',C.c_char_p,[U]);gi=self.fn('glGetIntegerv',None,[U,C.POINTER(I)]);gi(0x821d,C.byref(n))
        extensions=[self.fn('glGetStringi',C.c_char_p,[U,U])(0x1f03,i).decode() for i in range(n.value)]
        version=gs(0x1f02).decode();self.supports_compute=bool(re.search(r'OpenGL ES 3\.[12]',version))
        paths=set()
        for line in Path('/proc/self/maps').read_text().splitlines():
            path=line.split()[-1]
            if path.startswith('/') and any(x in path for x in ['libEGL','libGLES','swrast','swiftshader','libvulkan','libLLVM']):paths.add(path)
        self.metadata=dict(implementation=config['kind'],config_sha256=hashlib.sha256(json.dumps(config,sort_keys=True).encode()).hexdigest(),icd_sha256=digest(config['icd']) if config.get('icd') else None,vendor=gs(0x1f00).decode(),renderer=gs(0x1f01).decode(),api=version,shading_language=gs(0x8b8c).decode(),extensions=extensions,os=platform.platform(),os_build=platform.uname().version,executable_sha256=digest(sys.executable),libraries={p:digest(p) for p in sorted(paths) if Path(p).is_file()},source_sha256=digest(__file__),egl_vendor=self.fn('eglQueryString',C.c_char_p,[P,I],True)(self.d,0x3053).decode())
    def error(self):return self.fn('glGetError',U,[])()
    def shader(self,source,stage):
        obj=self.fn('glCreateShader',U,[U])({'vert':0x8b31,'frag':0x8b30,'comp':0x91b9}[stage]);raw=C.c_char_p(source.encode())
        self.fn('glShaderSource',None,[U,I,C.POINTER(C.c_char_p),P])(obj,1,C.byref(raw),None);self.fn('glCompileShader',None,[U])(obj);ok=I();self.fn('glGetShaderiv',None,[U,U,C.POINTER(I)])(obj,0x8b81,C.byref(ok));log=C.create_string_buffer(8192);self.fn('glGetShaderInfoLog',None,[U,I,P,P])(obj,len(log),None,log)
        return obj,bool(ok.value),log.value.decode(errors='replace')
    def program(self,sources):
        sources=dict(sources)
        if 'shader.frag' in sources and 'shader.vert' not in sources:sources['shader.vert']='#version 300 es\nvoid main(){ gl_Position=vec4(0.0,0.0,0.0,1.0); }'
        objects=[self.shader(src,name.rsplit('.',1)[1]) for name,src in sources.items()];program=self.fn('glCreateProgram',U,[])()
        for obj,_,_ in objects:self.fn('glAttachShader',None,[U,U])(program,obj)
        self.fn('glLinkProgram',None,[U])(program);ok=I();self.fn('glGetProgramiv',None,[U,U,C.POINTER(I)])(program,0x8b82,C.byref(ok));log=C.create_string_buffer(8192);self.fn('glGetProgramInfoLog',None,[U,I,P,P])(program,len(log),None,log)
        for obj,_,_ in objects:self.fn('glDeleteShader',None,[U])(obj)
        return program,dict(compile=all(x[1] for x in objects),link=bool(ok.value),compile_logs=[x[2] for x in objects],link_log=log.value.decode(errors='replace'))
    def execute(self,c):
        while self.error():pass
        kind=c['kind'];result={'id':c['id'],'status':'EXECUTED','kind':kind}
        if c.get('version',300)>=310 and not self.supports_compute:return dict(result,status='SKIP_UNSUPPORTED',reason='GLES 3.1 compute unavailable')
        if kind=='shader':
            p,observed=self.program(c['sources']);self.fn('glDeleteProgram',None,[U])(p);result.update(observed)
        elif kind=='api_error':
            self.fn(c['function'],None,[I]*len(c['args']))(*c['args']);result['api_error']=self.error()
        elif kind=='fbo_pixels':
            fb=U();rb=U();self.fn('glGenFramebuffers',None,[I,P])(1,C.byref(fb));self.fn('glBindFramebuffer',None,[U,U])(0x8d40,fb)
            self.fn('glGenRenderbuffers',None,[I,P])(1,C.byref(rb));self.fn('glBindRenderbuffer',None,[U,U])(0x8d41,rb);self.fn('glRenderbufferStorage',None,[U,U,I,I])(0x8d41,0x8058,4,4);self.fn('glFramebufferRenderbuffer',None,[U,U,U,U])(0x8d40,0x8ce0,0x8d41,rb)
            if self.fn('glCheckFramebufferStatus',U,[U])(0x8d40)!=0x8cd5:raise RuntimeError('RGBA8 FBO incomplete')
            self.fn('glDisable',None,[U])(0xbd0);self.fn('glClearColor',None,[F]*4)(*c['color']);self.fn('glClear',None,[U])(0x4000)
            pixels=(C.c_ubyte*64)();self.fn('glReadPixels',None,[I,I,I,I,U,U,P])(0,0,4,4,0x1908,0x1401,pixels);result['pixels']=list(pixels)
            self.fn('glBindFramebuffer',None,[U,U])(0x8d40,0);self.fn('glDeleteFramebuffers',None,[I,P])(1,C.byref(fb));self.fn('glDeleteRenderbuffers',None,[I,P])(1,C.byref(rb))
        else:
            p,observed=self.program(c['sources']);result.update(observed)
            if observed['link']:
                buf=U();zero=F(0);self.fn('glGenBuffers',None,[I,P])(1,C.byref(buf));self.fn('glBindBuffer',None,[U,U])(0x90d2,buf);self.fn('glBufferData',None,[U,C.c_ssize_t,P,U])(0x90d2,4,C.byref(zero),0x88e4);self.fn('glBindBufferBase',None,[U,U,U])(0x90d2,0,buf);self.fn('glUseProgram',None,[U])(p);self.fn('glDispatchCompute',None,[U,U,U])(1,1,1);self.fn('glMemoryBarrier',None,[U])(0x200)
                ptr=self.fn('glMapBufferRange',P,[U,C.c_ssize_t,C.c_ssize_t,U])(0x90d2,0,4,1)
                if not ptr:raise RuntimeError('SSBO read mapping failed')
                result['numeric']=C.cast(ptr,C.POINTER(F))[0];self.fn('glUnmapBuffer',U,[U])(0x90d2);self.fn('glDeleteBuffers',None,[I,P])(1,C.byref(buf))
            self.fn('glUseProgram',None,[U])(0);self.fn('glDeleteProgram',None,[U])(p)
        result['harness_gl_error']=self.error();return result
    def close(self):
        self.fn('eglMakeCurrent',U,[P,P,P,P],True)(self.d,None,None,None);self.fn('eglDestroySurface',U,[P,P],True)(self.d,self.s);self.fn('eglDestroyContext',U,[P,P],True)(self.d,self.c);self.fn('eglTerminate',U,[P],True)(self.d)

def compare(case,a,b):
    if any(x.get('status')=='SKIP_UNSUPPORTED' for x in (a,b)):return 'SKIP_UNSUPPORTED'
    if any(x.get('status')!='EXECUTED' for x in (a,b)):return 'UNKNOWN'
    if any(x['harness_gl_error'] for x in (a,b)):return 'FAIL'
    kind=case['kind']
    if kind=='shader':ok=all(x['compile']==case['expected_compile'] and x['link']==case['expected_link'] for x in (a,b))
    elif kind=='api_error':ok=all(x['api_error']==case['expected'] for x in (a,b))
    elif kind=='fbo_pixels':
        expected=case['expected']*16;t=case['tolerance'];ok=all(len(x['pixels'])==64 and all(abs(v-e)<=t for v,e in zip(x['pixels'],expected)) for x in (a,b)) and all(abs(v-w)<=t for v,w in zip(a['pixels'],b['pixels']))
    else:
        def near(v,w):return math.isfinite(v) and math.isfinite(w) and abs(v-w)<=case['absolute_tolerance']+case['relative_tolerance']*abs(w)
        ok=all(x.get('compile') and x.get('link') and near(x.get('numeric',float('nan')),case['expected']) for x in (a,b)) and near(a.get('numeric',float('nan')),b.get('numeric',float('nan')))
    return 'PASS' if ok else 'FAIL'

def child(config,selected):
    host=Host(config)
    try:return dict(status='EXECUTED',metadata=host.metadata,cases=[host.execute(c) for c in selected])
    finally:host.close()

def isolated(config,selected):
    with tempfile.TemporaryDirectory(prefix='gles-diff-') as tmp:
        request=Path(tmp)/'request.json';output=Path(tmp)/'output.json';request.write_text(json.dumps(dict(config=config,cases=selected)))
        # W1 process-group CPU/address-space/file-size limiter, with room for LLVM/SwiftShader JIT.
        run=shader_fuzz.isolated([sys.executable,str(Path(__file__).resolve()),'--child',str(request),'--output',str(output)],45,memory_mb=4096,log_bytes=2**20)
        if run['status']!='EXITED' or run['exit_code']!=0 or not output.exists():return dict(status='UNKNOWN',process=run,cases=[])
        return json.loads(output.read_text())

def signature(row):return {k:row.get(k) for k in ('status','compile','link','api_error','pixels','numeric','harness_gl_error')}
def reduce_mismatch(case,configs,observations,out):
    out.mkdir(parents=True,exist_ok=True);(out/'original.json').write_text(json.dumps(case,indent=2)+'\n')
    original=json.dumps(case,indent=2)+'\n';predicate=[signature(x) for x in observations]
    # Reuse existing ddmin with a fixed case identity/kind/domain. It deletes source lines
    # for shader cases; JSON lines for API/FBO, reporting only domain-limited minimality.
    source_key=next(iter(case.get('sources',{})),None);original=case['sources'][source_key] if source_key else original
    def oracle(candidate):
        try:
            trial=dict(case)
            if source_key:trial['sources']=dict(case['sources'],**{source_key:candidate})
            else:
                trial=json.loads(candidate)
                if set(trial)!=set(case) or trial['id']!=case['id'] or trial['kind']!=case['kind']:return dict(matches=False,diagnostic='outside fixed schema domain')
            runs=[isolated(cfg,[trial]) for cfg in configs]
            if any(r['status']!='EXECUTED' or not r['cases'] for r in runs):return dict(matches=False,error_type='replay_unavailable')
            rows=[r['cases'][0] for r in runs]
            return dict(matches=compare(trial,*rows)=='FAIL' and [signature(x) for x in rows]==predicate,diagnostic='exact original observation pair and FAIL required')
        except (ValueError,KeyError,TypeError):return dict(matches=False,diagnostic='invalid candidate')
    result=reducer.minimize(original,oracle,max_attempts=12);reduced=result.pop('source');(out/('reduced.'+source_key.rsplit('.',1)[1] if source_key else 'reduced.json')).write_text(reduced)
    result.update(predicate=predicate,minimality_domain='line deletion of first shader source, other sources fixed' if source_key else 'JSON line deletion preserving all case keys',budget_attempts=12,semantic_global_minimality=False)
    (out/'reduction.json').write_text(json.dumps(result,indent=2)+'\n');return result

def run(configs,out,selected):
    out.mkdir(parents=True,exist_ok=True);(out/'cases.json').write_text(json.dumps(selected,indent=2)+'\n');(out/'implementations.json').write_text(json.dumps(configs,indent=2)+'\n')
    runs=[isolated(cfg,selected) for cfg in configs]
    for cfg,r in zip(configs,runs):(out/(cfg['kind']+'.json')).write_text(json.dumps(r,indent=2)+'\n')
    rows=[]
    for case in selected:
        observations=[next((x for x in r.get('cases',[]) if x['id']==case['id']),dict(status='UNKNOWN')) for r in runs]
        status=compare(case,*observations);row=dict(id=case['id'],kind=case['kind'],status=status,comparison_channels=({'compile':[x.get('compile') for x in observations],'link':[x.get('link') for x in observations]} if case['kind'] in ('shader','ssbo_numeric') else {}),source_sha256=hashlib.sha256(json.dumps(case,sort_keys=True).encode()).hexdigest(),replay=f'python3 benchmarks/differential/run.py --config {out}/implementations.json --cases {out}/cases.json --case {case["id"]} --output /tmp/differential-replay')
        if status=='FAIL':row['reducer']=reduce_mismatch(case,configs,observations,out/'mismatches'/case['id'])
        rows.append(row)
    status='PASS' if rows and all(x['status']=='PASS' for x in rows) else ('FAIL' if any(x['status']=='FAIL' for x in rows) else 'UNKNOWN')
    report=dict(schema_version=1,generated_at=datetime.now(timezone.utc).isoformat(),status=status,evidence='HOST_REPRODUCED' if all(r['status']=='EXECUTED' for r in runs) else 'UNVERIFIED',implementations=[r.get('metadata',{}) for r in runs],cases=rows,executed_comparisons=sum(x['status'] in ('PASS','FAIL') for x in rows),real_gpu_gate='BLOCKED_BY_HARDWARE',android_native_gate='BLOCKED_BY_HARDWARE',performance_comparison='NOT_MEASURED',tolerances=dict(fbo='linear RGBA8 UNORM, no texture filtering or sRGB: max absolute 1 code value against CPU golden and peer',ssbo='highp finite float: absolute 1e-6 + relative 1e-6; simple well-conditioned arithmetic only'),dependency_hashes={str(p.relative_to(ROOT)):digest(p) for p in [ROOT/'tools/shader_fuzz.py',ROOT/'benchmarks/state_machine/host.py',ROOT/'benchmarks/pipeline/runtime.py',ROOT/'benchmarks/reducer/reduce.py']})
    (out/'driver-matrix.md').write_text('# Actual host driver matrix\n\n'+'\n'.join('- '+r.get('metadata',{}).get('implementation','unavailable')+': '+r.get('metadata',{}).get('renderer',r['status'])+'; '+r.get('metadata',{}).get('api','unknown') for r in runs)+'\n\nNative Android / physical GPU: BLOCKED_BY_HARDWARE.\n')
    (out/'summary.json').write_text(json.dumps(report,indent=2)+'\n');(out/'summary.md').write_text('# Host differential\n\nStatus: '+status+'\n\nActual comparisons: '+str(report['executed_comparisons'])+'\n\nReal GPU / Android: BLOCKED_BY_HARDWARE. Performance: NOT_MEASURED.\n\n'+ '\n'.join('- '+x['id']+' ['+x['kind']+']: '+x['status'] for x in rows)+'\n');return report

def main():
    p=argparse.ArgumentParser();p.add_argument('--config',type=Path);p.add_argument('--cases',type=Path);p.add_argument('--case');p.add_argument('--child',type=Path);p.add_argument('--output',type=Path,required=True);a=p.parse_args()
    if a.child:
        try:
            data=json.loads(a.child.read_text());result=child(data['config'],data['cases'])
        except Exception as e:result=dict(status='UNKNOWN',error=str(e),cases=[])
        a.output.write_text(json.dumps(result,indent=2)+'\n');return 0
    configs=json.loads(a.config.read_text())
    if len(configs)!=2 or {c['kind'] for c in configs}!={'mesa','angle'}:raise ValueError('two distinct implementations mesa+angle required')
    selected=json.loads(a.cases.read_text()) if a.cases else cases()
    if a.case:selected=[c for c in selected if c['id']==a.case]
    report=run(configs,a.output,selected);print(json.dumps(dict(status=report['status'],executed_comparisons=report['executed_comparisons'])));return 0 if report['status']=='PASS' else 1
if __name__=='__main__':raise SystemExit(main())
