#!/usr/bin/env python3
"""Execute original and transformed finite graph on actual GLES FBOs, with CPU goldens."""
import copy
import argparse,ctypes as C,hashlib,importlib.util,json,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2];sys.path.insert(0,str(ROOT/'tools'))
from rendergraph_replay import baseline,transform,validate,digest
spec=importlib.util.spec_from_file_location('graph_diff',ROOT/'benchmarks/differential/run.py');diff=importlib.util.module_from_spec(spec);spec.loader.exec_module(diff)
U,I,P,F=diff.U,diff.I,diff.P,diff.F
VERT='#version 300 es\nvoid main(){vec2 p=vec2((gl_VertexID<<1)&2,gl_VertexID&2);gl_Position=vec4(p*2.-1.,0.,1.);}'
HEAD='#version 300 es\nprecision highp float;uniform sampler2D tex;uniform vec2 extent;out vec4 color;\n'

def fragment(pattern,source):
    if source:
        value='vec4(.25,.5,.75,1.)' if pattern=='constant' else 'vec4(vec3(mod(floor(gl_FragCoord.x)+floor(gl_FragCoord.y),2.)),1.)'
        return HEAD+'void main(){color='+value+';}'
    return HEAD+'void main(){color=texture(tex,gl_FragCoord.xy/extent);}'

class Host(diff.Host):
    def replay(self,graph,pattern):
        invariants=validate(graph) # Refuse unsafe graph BEFORE GPU execution, no UB negative.
        if pattern not in ('constant','checkerboard'):raise ValueError('unknown source')
        while self.error():pass
        textures={};fbs={};programs=[];vao=U();rows=[]
        try:
            self.fn('glGenVertexArrays',None,[I,P])(1,C.byref(vao));self.fn('glBindVertexArray',None,[U])(vao)
            for cap in (0xbd0,0xbe2,0xb71,0xb90,0xc11,0xb44):self.fn('glDisable',None,[U])(cap)
            self.fn('glColorMask',None,[U]*4)(1,1,1,1)
            self.fn('glActiveTexture',None,[U])(0x84c0)
            for name,r in graph['resources'].items():
                tex=U();fb=U();textures[name]=tex;fbs[name]=fb
                self.fn('glGenTextures',None,[I,P])(1,C.byref(tex));self.fn('glBindTexture',None,[U,U])(0xde1,tex)
                for param,value in ((0x2801,0x2600),(0x2800,0x2600),(0x2802,0x812f),(0x2803,0x812f)):
                    self.fn('glTexParameteri',None,[U,U,I])(0xde1,param,value)
                self.fn('glTexImage2D',None,[U,I,I,I,I,I,U,U,P])(0xde1,0,0x8058,*r['size'],0,0x1908,0x1401,None)
                self.fn('glGenFramebuffers',None,[I,P])(1,C.byref(fb));self.fn('glBindFramebuffer',None,[U,U])(0x8d40,fb)
                self.fn('glFramebufferTexture2D',None,[U,U,U,U,I])(0x8d40,0x8ce0,0xde1,tex,0)
                if self.fn('glCheckFramebufferStatus',U,[U])(0x8d40)!=0x8cd5:raise RuntimeError('incomplete FBO')
            for p in graph['passes']:
                output=p['writes'][0];size=graph['resources'][output]['size'];reads=p.get('reads',[])
                src={'shader.vert':VERT,'shader.frag':fragment(pattern,not reads)}
                prog,obs=self.program(src);programs.append(prog)
                if not obs['compile'] or not obs['link']:raise RuntimeError('shader compile/link failed')
                self.fn('glBindFramebuffer',None,[U,U])(0x8d40,fbs[output]);self.fn('glViewport',None,[I]*4)(0,0,*size)
                self.fn('glBindTexture',None,[U,U])(0xde1,textures[reads[0]] if reads else 0)
                self.fn('glUseProgram',None,[U])(prog)
                loc=self.fn('glGetUniformLocation',I,[U,C.c_char_p])(prog,b'extent')
                self.fn('glUniform2f',None,[I,F,F])(loc,*size)
                loc=self.fn('glGetUniformLocation',I,[U,C.c_char_p])(prog,b'tex');self.fn('glUniform1i',None,[I,I])(loc,0)
                self.fn('glDrawArrays',None,[U,I,I])(4,0,3)
                rows.append({'pass':p['id'],'extent':size,'compile':True,'link':True,'source_sha256':{k:hashlib.sha256(v.encode()).hexdigest() for k,v in src.items()}})
            pixels=(C.c_ubyte*64)();self.fn('glReadPixels',None,[I,I,I,I,U,U,P])(0,0,4,4,0x1908,0x1401,pixels)
            return {'graph_sha256':digest(graph),'passes':rows,'pixels':list(pixels),'gl_error':self.error(),'synchronization':invariants}
        finally:
            self.fn('glUseProgram',None,[U])(0);self.fn('glBindFramebuffer',None,[U,U])(0x8d40,0);self.fn('glBindTexture',None,[U,U])(0xde1,0)
            for program in programs:self.fn('glDeleteProgram',None,[U])(program)
            for objects,fn in ((textures.values(),'glDeleteTextures'),(fbs.values(),'glDeleteFramebuffers'),([vao],'glDeleteVertexArrays')):
                for obj in objects:
                    if obj.value:self.fn(fn,None,[I,P])(1,C.byref(obj))

def golden(pattern,scaled):
    if pattern=='constant':return [64,128,191,255]*16
    return [v for y in range(4) for x in range(4) for v in ([0,0,0,255] if scaled else [255*((x+y)%2)]*3+[255])]

def run(config):
    graph=baseline();change=transform(graph);host=Host(config);rows=[];rejected=[]
    invalid=[]
    g=copy.deepcopy(graph);g['passes'][1].pop('depends_on');invalid.append(('missing-producer-dependency',g))
    g=copy.deepcopy(graph);g['passes'][1]['barrier']=0;invalid.append(('unsupported-barrier-declaration',g))
    g=copy.deepcopy(graph);g['passes'][1]['writes']=['scene'];invalid.append(('attachment-sampling-feedback',g))
    for name,g in invalid:
        try:host.replay(g,'constant');rejected.append({'id':name,'status':'UNEXPECTED_ACCEPT'})
        except ValueError as e:rejected.append({'id':name,'status':'REJECTED_BEFORE_GL','reason':str(e)})
    try:
        for pattern in ('constant','checkerboard'):
            a=host.replay(graph,pattern);b=host.replay(change['candidate'],pattern)
            errs=[max(abs(x-y) for x,y in zip(row['pixels'],golden(pattern,scaled))) for row,scaled in ((a,False),(b,True))]
            image_error=max(abs(x-y) for x,y in zip(a['pixels'],b['pixels']))
            expected='PASS' if pattern=='constant' else 'REJECTED_BY_QUALITY'
            observed='PASS' if image_error<=1 else 'REJECTED_BY_QUALITY'
            rows.append({'pattern':pattern,'baseline':a,'candidate':b,'cpu_max_errors':errs,'baseline_candidate_max_error':image_error,'expected':expected,'observed':observed,'pass':max(errs)<=1 and not a['gl_error'] and not b['gl_error'] and expected==observed,'selected_graph_sha256':b['graph_sha256'] if observed=='PASS' else a['graph_sha256']})
    finally:host.close()
    return {'status':'HOST_PASS' if all(r['pass'] for r in rows) and all(r['status']=='REJECTED_BEFORE_GL' for r in rejected) else 'FAIL','transformation':change,'rejected_controls':rejected,'cases':rows,'draw_count':12,'readback_count':4,'quality_scope':'two static 4x4 RGBA8 patterns only','performance':'NOT_MEASURED','general_equivalence':'NOT_PROVEN','business_renderer_mutated':False}
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--config',type=Path,required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args();r=run(json.loads(a.config.read_text()));a.output.write_text(json.dumps(r,indent=2)+'\n');print(r['status']);raise SystemExit(r['status']!='HOST_PASS')
