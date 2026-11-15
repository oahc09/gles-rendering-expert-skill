#!/usr/bin/env python3
"""Actual bounded UBO/SSBO/compute/depth GLES controls; no performance claims."""
import argparse
import ctypes as C
import hashlib
import importlib.util
import json
from pathlib import Path
SPEC=importlib.util.spec_from_file_location('advanced_differential',Path(__file__).resolve().parents[1]/'differential/run.py')
diff=importlib.util.module_from_spec(SPEC);SPEC.loader.exec_module(diff)
U,I,P,F=diff.U,diff.I,diff.P,diff.F
VERT='''#version VERSION es
void main(){vec2 p=vec2((gl_VertexID<<1)&2,gl_VertexID&2);gl_Position=vec4(p*2.0-1.0,0.0,1.0);}
'''

def sources(kind,wrong=False):
    version=310 if kind in ('ssbo','compute') else 300
    vertex=VERT.replace('VERSION',str(version))
    declaration=''
    value='vec4(0.25,0.5,0.75,1.0)'
    if kind=='ubo': declaration='layout(std140) uniform Data {vec4 data;};';value='data'
    if kind in ('ssbo','compute'): declaration='layout(std430,binding=0) readonly buffer Data {vec4 data;};';value='data'
    body='color='+value+';'
    if kind=='discard': body=('if(gl_FragCoord.x<2.0)discard;' if not wrong else '')+body
    if wrong and kind not in ('discard','depth'):body='color='+value+'.bgra;'
    fragment=f'#version {version} es\nprecision highp float;\n{declaration}\nlayout(location=0) out vec4 color;\nvoid main(){{{body}}}\n'
    result={'shader.vert':vertex,'shader.frag':fragment}
    if kind=='compute':
        result['shader.comp']='#version 310 es\nprecision highp float;\nlayout(local_size_x=1) in;layout(std430,binding=0) buffer Data {vec4 data;};void main(){data=vec4(0.25,0.5,0.75,1.0);}'
    return result

class AdvancedHost(diff.Host):
    def draw(self,kind,wrong=False,barrier=True):
        if kind in ('compute','ssbo') and not self.supports_compute:return {'status':'SKIP_UNSUPPORTED'}
        if kind=='compute' and not barrier:
            return {'status':'REJECTED_UNSAFE','reason':'Compute SSBO writes require GL_SHADER_STORAGE_BARRIER_BIT before fragment reads; undefined visibility is not a deterministic negative image oracle.'}
        while self.error():pass
        src=sources(kind,wrong);compute=src.pop('shader.comp',None)
        program=comp=0;fb=U();rb=U();depth=U();vao=U();buf=U()
        row={'kind':kind,'variant':'negative' if wrong else 'baseline','status':'COMPILE_FAILED','source_sha256':{k:hashlib.sha256(v.encode()).hexdigest() for k,v in src.items()},'performance':'NOT_MEASURED'}
        if compute:row['source_sha256']['shader.comp']=hashlib.sha256(compute.encode()).hexdigest()
        try:
            program,obs=self.program(src);row.update(obs)
            if not obs['compile'] or not obs['link']:return row
            self.fn('glGenFramebuffers',None,[I,P])(1,C.byref(fb));self.fn('glBindFramebuffer',None,[U,U])(0x8d40,fb)
            for obj,fmt,attachment in ((rb,0x8058,0x8ce0),(depth,0x81a6,0x8d00)):
                self.fn('glGenRenderbuffers',None,[I,P])(1,C.byref(obj));self.fn('glBindRenderbuffer',None,[U,U])(0x8d41,obj)
                self.fn('glRenderbufferStorage',None,[U,U,I,I])(0x8d41,fmt,4,4);self.fn('glFramebufferRenderbuffer',None,[U,U,U,U])(0x8d40,attachment,0x8d41,obj)
            if self.fn('glCheckFramebufferStatus',U,[U])(0x8d40)!=0x8cd5:raise RuntimeError('Framebuffer incomplete')
            for cap in (0xbd0,0xbe2,0xb71,0xb90,0xc11,0xb44):self.fn('glDisable',None,[U])(cap)
            self.fn('glColorMask',None,[U]*4)(1,1,1,1);self.fn('glDepthMask',None,[U])(1)
            self.fn('glClearColor',None,[F]*4)(0,0,0,0);self.fn('glClearDepthf',None,[F])(0.25 if kind=='depth' else 1)
            self.fn('glClear',None,[U])(0x4000|0x100);self.fn('glViewport',None,[I]*4)(0,0,4,4)
            if kind=='depth' and not wrong:self.fn('glEnable',None,[U])(0xb71);self.fn('glDepthFunc',None,[U])(0x201)
            self.fn('glGenVertexArrays',None,[I,P])(1,C.byref(vao));self.fn('glBindVertexArray',None,[U])(vao)
            if kind in ('ubo','ssbo','compute'):
                target=0x8a11 if kind=='ubo' else 0x90d2
                data=(F*4)(*([0,0,0,0] if compute else [.25,.5,.75,1]))
                self.fn('glGenBuffers',None,[I,P])(1,C.byref(buf));self.fn('glBindBuffer',None,[U,U])(target,buf)
                self.fn('glBufferData',None,[U,C.c_ssize_t,P,U])(target,16,data,0x88e4);self.fn('glBindBufferBase',None,[U,U,U])(target,0,buf)
                if kind=='ubo':
                    idx=self.fn('glGetUniformBlockIndex',U,[U,C.c_char_p])(program,b'Data');self.fn('glUniformBlockBinding',None,[U,U,U])(program,idx,0)
            if compute:
                comp,cobs=self.program({'shader.comp':compute});row['compute']=cobs
                if not cobs['compile'] or not cobs['link']:return row
                self.fn('glUseProgram',None,[U])(comp);self.fn('glDispatchCompute',None,[U]*3)(1,1,1)
                self.fn('glMemoryBarrier',None,[U])(0x2000)
                row['barrier']='GL_SHADER_STORAGE_BARRIER_BIT'
            self.fn('glUseProgram',None,[U])(program);self.fn('glDrawArrays',None,[U,I,I])(4,0,3)
            pixels=(C.c_ubyte*64)();self.fn('glReadPixels',None,[I,I,I,I,U,U,P])(0,0,4,4,0x1908,0x1401,pixels)
            row.update(status='EXECUTED',pixels=list(pixels),harness_gl_error=self.error())
            return row
        finally:
            self.fn('glUseProgram',None,[U])(0);self.fn('glBindFramebuffer',None,[U,U])(0x8d40,0);self.fn('glBindVertexArray',None,[U])(0)
            for p in (program,comp):
                if p:self.fn('glDeleteProgram',None,[U])(p)
            for obj,fn in ((buf,'glDeleteBuffers'),(vao,'glDeleteVertexArrays'),(rb,'glDeleteRenderbuffers'),(depth,'glDeleteRenderbuffers'),(fb,'glDeleteFramebuffers')):
                if obj.value:self.fn(fn,None,[I,P])(1,C.byref(obj))

def golden(kind):
    return [v for y in range(4) for x in range(4) for v in ([0,0,0,0] if kind=='depth' or (kind=='discard' and x<2) else [64,128,191,255])]

def quality(row,expected):
    if len(expected)!=64 or any(type(v) is not int or not 0<=v<=255 for v in expected):return 'UNKNOWN'
    if row.get('status')!='EXECUTED' or row.get('harness_gl_error') or len(row.get('pixels',[]))!=64:return 'UNKNOWN'
    if any(type(v) is not int or not 0<=v<=255 for v in row['pixels']):return 'UNKNOWN'
    if row.get('compile') is not True or row.get('link') is not True:return 'UNKNOWN'
    return 'PASS' if max(abs(a-b) for a,b in zip(row['pixels'],expected))<=1 else 'FAIL'

def run(config):
    host=AdvancedHost(config);rows=[]
    try:
        for kind in ('uniform_constant','ubo','ssbo','compute','discard','depth'):
            a=host.draw(kind);b=host.draw(kind,True)
            rows.append({'id':kind,'baseline':a,'negative':b,'baseline_quality':quality(a,golden(kind)),'negative_quality':quality(b,golden(kind))})
        missing=host.draw('compute',barrier=False)
    finally:host.close()
    status='HOST_PASS' if all(r['baseline_quality']=='PASS' and r['negative_quality']=='FAIL' for r in rows) and missing['status']=='REJECTED_UNSAFE' else 'PARTIAL_OR_FAIL'
    pairs=[{'baseline':'uniform_constant','candidate':kind,'quality':'PASS' if quality(rows[i]['baseline'],rows[0]['baseline'].get('pixels',[]))=='PASS' else 'UNKNOWN_OR_FAIL','performance':'NOT_MEASURED'} for i,kind in enumerate(('uniform_constant','ubo','ssbo','compute')) if i]
    return {'status':status,'mechanism_ab':pairs,'scope':'4x4 software GLES functional controls; not device speed or general source equivalence','performance':'NOT_MEASURED','cases':rows,'missing_barrier_control':missing}

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--config',type=Path,required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args()
    result=run(json.loads(a.config.read_text()));a.output.write_text(json.dumps(result,indent=2)+'\n');print(result['status']);raise SystemExit(result['status']!='HOST_PASS')
