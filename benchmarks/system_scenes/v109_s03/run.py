#!/usr/bin/env python3
"""Finite UI + depth-tested orthographic 3D + independent PostFX graph, actual GLES."""
import argparse,ctypes as C,hashlib,importlib.util,json,math
from pathlib import Path
ROOT=Path(__file__).resolve().parents[3]
spec=importlib.util.spec_from_file_location('s03_diff',ROOT/'benchmarks/differential/run.py');diff=importlib.util.module_from_spec(spec);spec.loader.exec_module(diff)
U,I,P,F=diff.U,diff.I,diff.P,diff.F
GEOM_VERT='''#version 300 es
uniform vec4 rect;uniform float depth;uniform float camera;
void main(){vec2 p[6]=vec2[6](vec2(0,0),vec2(1,0),vec2(0,1),vec2(0,1),vec2(1,0),vec2(1,1));vec2 q=mix(rect.xy,rect.zw,p[gl_VertexID]);q.x-=camera;gl_Position=vec4(q/4.-1.,depth,1.);}
'''
GEOM_FRAG='#version 300 es\nprecision highp float;uniform vec4 tint;out vec4 color;void main(){color=tint;}'
FULL_VERT='#version 300 es\nvoid main(){vec2 p=vec2((gl_VertexID<<1)&2,gl_VertexID&2);gl_Position=vec4(p*2.-1.,0.,1.);}'
POST_HEAD='#version 300 es\nprecision highp float;uniform sampler2D tex;uniform vec2 extent;out vec4 color;void main(){vec4 c=texture(tex,gl_FragCoord.xy/extent);'
POST=POST_HEAD+'color=c.bgra;}'
EQUIV=POST_HEAD+'color=vec4(c.b,c.g,c.r,c.a);}'
COPY=POST_HEAD+'color=c;}'
VARIANTS=('baseline','equivalent','half','bad_depth','bad_ui')

def oracle(camera,variant='baseline'):
    # Independent analytical orthographic rectangle coverage and depth visibility.
    pixels=[]
    for y in range(8):
        for x in range(8):
            world=x+.5+camera; py=y+.5
            near=2<=world<6 and 2<=py<6;far=1<=world<7 and 1<=py<7
            c=[0,255,0,255] if near and variant!='bad_depth' else [255,0,0,255] if far else [0,0,0,255]
            if py>=6:
                alpha=1 if variant=='bad_ui' else .5
                c=[math.floor((([0,0,1][k]*alpha+c[k]/255*(1-alpha))*255)+.5) for k in range(3)]+[255]
            pixels+=c
    size=4 if variant=='half' else 8
    post=[]
    for y in range(size):
        for x in range(size):
            sx=int((x+.5)*8/size);sy=int((y+.5)*8/size);r,g,b,a=pixels[(sy*8+sx)*4:(sy*8+sx)*4+4];post += [b,g,r,a]
    final=[]
    for y in range(8):
        for x in range(8):
            sx=int((x+.5)*size/8);sy=int((y+.5)*size/8);final+=post[(sy*size+sx)*4:(sy*size+sx)*4+4]
    return {'scene':pixels,'postfx':post,'screen':final}

class Host(diff.Host):
    def render(self,camera,variant):
        if camera not in (-1,0,1) or variant not in VARIANTS:raise ValueError('unregistered camera/variant')
        while self.error():pass
        programs=[];textures={};fbos={};depth=U();vao=U();draws=0;captures={};dimensions={'scene':8,'postfx':4 if variant=='half' else 8,'screen':8}
        def fn(n,ret,args):return self.fn(n,ret,args)
        def read(name):
            n=dimensions[name];p=(C.c_ubyte*(n*n*4))();fn('glReadPixels',None,[I,I,I,I,U,U,P])(0,0,n,n,0x1908,0x1401,p);captures[name]=list(p)
        sources=[{'shader.vert':GEOM_VERT,'shader.frag':GEOM_FRAG},{'shader.vert':FULL_VERT,'shader.frag':EQUIV if variant=='equivalent' else POST},{'shader.vert':FULL_VERT,'shader.frag':COPY}]
        try:
            for src in sources:
                prog,obs=self.program(src)
                if not obs['compile'] or not obs['link']:raise RuntimeError('compile/link failure')
                programs.append(prog)
            fn('glGenVertexArrays',None,[I,P])(1,C.byref(vao));fn('glBindVertexArray',None,[U])(vao)
            for cap in (0xbd0,0xbe2,0xb71,0xb90,0xc11,0xb44):fn('glDisable',None,[U])(cap)
            fn('glColorMask',None,[U]*4)(1,1,1,1);fn('glDepthMask',None,[U])(1);fn('glActiveTexture',None,[U])(0x84c0)
            for name,n in dimensions.items():
                t=U();f=U();textures[name]=t;fbos[name]=f
                fn('glGenTextures',None,[I,P])(1,C.byref(t));fn('glBindTexture',None,[U,U])(0xde1,t)
                for param,value in ((0x2801,0x2600),(0x2800,0x2600),(0x2802,0x812f),(0x2803,0x812f)):fn('glTexParameteri',None,[U,U,I])(0xde1,param,value)
                fn('glTexImage2D',None,[U,I,I,I,I,I,U,U,P])(0xde1,0,0x8058,n,n,0,0x1908,0x1401,None)
                fn('glGenFramebuffers',None,[I,P])(1,C.byref(f));fn('glBindFramebuffer',None,[U,U])(0x8d40,f)
                fn('glFramebufferTexture2D',None,[U,U,U,U,I])(0x8d40,0x8ce0,0xde1,t,0)
                if name=='scene':
                    fn('glGenRenderbuffers',None,[I,P])(1,C.byref(depth));fn('glBindRenderbuffer',None,[U,U])(0x8d41,depth)
                    fn('glRenderbufferStorage',None,[U,U,I,I])(0x8d41,0x81a6,n,n);fn('glFramebufferRenderbuffer',None,[U,U,U,U])(0x8d40,0x8d00,0x8d41,depth)
                if fn('glCheckFramebufferStatus',U,[U])(0x8d40)!=0x8cd5:raise RuntimeError('incomplete FBO')
            fn('glBindFramebuffer',None,[U,U])(0x8d40,fbos['scene']);fn('glViewport',None,[I]*4)(0,0,8,8)
            fn('glClearColor',None,[F]*4)(0,0,0,1);fn('glClearDepthf',None,[F])(1);fn('glClear',None,[U])(0x4100)
            fn('glBindTexture',None,[U,U])(0xde1,0);fn('glUseProgram',None,[U])(programs[0])
            def loc(name):return fn('glGetUniformLocation',I,[U,C.c_char_p])(programs[0],name.encode())
            if variant!='bad_depth':fn('glEnable',None,[U])(0xb71)
            fn('glDepthFunc',None,[U])(0x201)
            # Deliberately near-before-far order makes the depth test observable.
            for rect,z,tint in [((2,2,6,6),-.4,(0,1,0,1)),((1,1,7,7),.6,(1,0,0,1))]:
                fn('glUniform4f',None,[I,F,F,F,F])(loc('rect'),*rect);fn('glUniform1f',None,[I,F])(loc('depth'),z);fn('glUniform1f',None,[I,F])(loc('camera'),camera);fn('glUniform4f',None,[I,F,F,F,F])(loc('tint'),*tint);fn('glDrawArrays',None,[U,I,I])(4,0,6);draws+=1
            fn('glDisable',None,[U])(0xb71);fn('glEnable',None,[U])(0xbe2)
            fn('glBlendFuncSeparate',None,[U]*4)(0x302,0x303,1,0x303);fn('glBlendEquation',None,[U])(0x8006)
            fn('glUniform4f',None,[I,F,F,F,F])(loc('rect'),0,6,8,8);fn('glUniform1f',None,[I,F])(loc('camera'),0);fn('glUniform4f',None,[I,F,F,F,F])(loc('tint'),0,0,1,1 if variant=='bad_ui' else .5);fn('glDrawArrays',None,[U,I,I])(4,0,6);draws+=1;read('scene')
            fn('glDisable',None,[U])(0xbe2)
            for index,(target,source) in enumerate([('postfx','scene'),('screen','postfx')],1):
                n=dimensions[target];prog=programs[index];fn('glBindFramebuffer',None,[U,U])(0x8d40,fbos[target]);fn('glViewport',None,[I]*4)(0,0,n,n);fn('glBindTexture',None,[U,U])(0xde1,textures[source]);fn('glUseProgram',None,[U])(prog)
                fn('glUniform2f',None,[I,F,F])(fn('glGetUniformLocation',I,[U,C.c_char_p])(prog,b'extent'),n,n);fn('glUniform1i',None,[I,I])(fn('glGetUniformLocation',I,[U,C.c_char_p])(prog,b'tex'),0);fn('glDrawArrays',None,[U,I,I])(4,0,3);draws+=1;read(target)
            return {'camera':camera,'variant':variant,'pixels':captures,'gl_error':self.error(),'draws':draws,'readbacks':3,'dimensions':dimensions,'source_sha256':[{k:hashlib.sha256(v.encode()).hexdigest() for k,v in src.items()} for src in sources], 'render_target_sequence':['scene','postfx','screen'],'render_target_transitions':2,'attachment_events':[
                {'target':'scene','event':'clear','attachments':['RGBA8 color','DEPTH24 depth'],'extent':[8,8]},
                {'target':'scene','event':'depth_test_draw','order':['near green','far red'],'depth_write':True,'depth_test':variant!='bad_depth'},
                {'target':'scene','event':'ui_blend','color_load':'preserve geometry color','depth_test':False,'alpha':1 if variant=='bad_ui' else .5},
                {'target':'scene','event':'readback_and_later_texture_consume','logical_color_store_required':True},
                {'target':'postfx','event':'full_overwrite','previous_color_load_required':False,'input':'scene','logical_color_store_required':True,'extent':[dimensions['postfx']]*2},
                {'target':'screen','event':'full_overwrite','previous_color_load_required':False,'input':'postfx','logical_color_store_required':True,'extent':[8,8]}],
                'loads_stores':'API-derived logical preservation/overwrite events, not physical tile traffic','depth_geometry':'two orthographic planes with distinct clip depth, near submitted before far','memory_barrier':'not required: coherent framebuffer writes to distinct sampled textures in one context'}
        finally:
            fn('glUseProgram',None,[U])(0);fn('glBindFramebuffer',None,[U,U])(0x8d40,0);fn('glBindTexture',None,[U,U])(0xde1,0)
            for p in programs:fn('glDeleteProgram',None,[U])(p)
            for objects,name in ((textures.values(),'glDeleteTextures'),(fbos.values(),'glDeleteFramebuffers'),([depth],'glDeleteRenderbuffers'),([vao],'glDeleteVertexArrays')):
                for obj in objects:
                    if obj.value:fn(name,None,[I,P])(1,C.byref(obj))

def error(actual,expected):
    if not actual or len(actual)!=len(expected) or any(type(v)!=int or not 0<=v<=255 for v in actual+expected):raise ValueError('invalid pixels')
    return max(abs(a-b) for a,b in zip(actual,expected))

def run(config):
    host=Host(config);rows=[]
    try:
        for camera in (-1,0,1):
            reference=oracle(camera)
            for variant in VARIANTS:
                capture=host.render(camera,variant);own=oracle(camera,variant)
                own_errors={k:error(capture['pixels'][k],own[k]) for k in own}
                target_error=error(capture['pixels']['screen'],reference['screen'])
                observed='PASS' if target_error<=1 else 'REJECTED_BY_QUALITY';expected='PASS' if variant in ('baseline','equivalent') else 'REJECTED_BY_QUALITY'
                rows.append({'capture':capture,'cpu_max_errors':own_errors,'target_max_error':target_error,'quality':observed,'expected':expected,'pass':max(own_errors.values())<=1 and not capture['gl_error'] and observed==expected,'selection':'candidate_quality_only' if observed=='PASS' else 'baseline','performance':'NOT_MEASURED'})
    finally:host.close()
    baseline_valid=all(r['pass'] and r['quality']=='PASS' for r in rows if r['capture']['variant']=='baseline')
    decisions=[]
    for variant in VARIANTS:
        candidates=[r for r in rows if r['capture']['variant']==variant]
        valid=all(r['pass'] and r['quality']=='PASS' for r in candidates)
        selected=variant if valid and baseline_valid else 'baseline' if baseline_valid else 'UNAVAILABLE'
        decisions.append({'variant':variant,'all_camera_quality_pass':valid,'quality_selection':selected,
            'production_selection':'baseline' if baseline_valid else 'UNAVAILABLE','performance':'NOT_MEASURED'})
        for r in candidates:r['selection']=selected
    return {'global_baseline_valid':baseline_valid,'global_decisions':decisions,'status':'HOST_PASS' if all(r['pass'] for r in rows) else 'FAIL','scene':'S03 bounded integrated UI + orthographic depth geometry + PostFX','rows':rows,'draws':75,'readbacks':45,'cameras':[-1,0,1],'image_budget_rgba8':1,'actual_tile_load_store':'NOT_MEASURED','physical_performance':'BLOCKED_BY_HARDWARE','release_acceptance':False,'scope':'8x8 deterministic static geometry, three discrete camera positions; not complex production perspective scene or continuous animation'}
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--config',type=Path,required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args();a.output.parent.mkdir(parents=True,exist_ok=True);r=run(json.loads(a.config.read_text()));a.output.write_text(json.dumps(r,indent=2)+'\n');print(r['status']);raise SystemExit(r['status']!='HOST_PASS')
