#!/usr/bin/env python3
"""GLES3 two-bone std140 linear blend skinning, captured positions and CPU fallback."""
import argparse,ctypes as C,hashlib,importlib.util,json,math
from pathlib import Path
ROOT=Path(__file__).resolve().parents[3]
s=importlib.util.spec_from_file_location('skinning_host',ROOT/'benchmarks/differential/run.py');d=importlib.util.module_from_spec(s);s.loader.exec_module(d)
U,I,P,F=d.U,d.I,d.P,d.F
VERTICES=[(-.5,-.5,0),(.5,-.5,0),(-.5,.5,0),(-.5,.5,0),(.5,-.5,0),(.5,.5,0)]
WEIGHTS=[2,1,1,0];JOINTS=[0,1,0,1]
VERT='''#version 300 es
precision highp float;layout(location=0)in vec3 position;layout(location=1)in vec4 weights;layout(location=2)in uvec4 joints;
layout(std140)uniform Bones{mat4 bones[2];};out vec4 captured;
void main(){vec4 w=weights/max(dot(weights,vec4(1)),0.000001);vec4 p=vec4(position,1);vec4 q=w.x*(bones[joints.x]*p)+w.y*(bones[joints.y]*p)+w.z*(bones[joints.z]*p)+w.w*(bones[joints.w]*p);captured=vec4(q.xyz,1);gl_Position=captured;}
'''
FALLBACK='#version 300 es\nlayout(location=0)in vec3 position;out vec4 captured;void main(){captured=vec4(position,1);gl_Position=captured;}'
FRAG='#version 300 es\nprecision highp float;out vec4 color;void main(){color=vec4(0,1,0,1);}'
def cpu(pose):
 if pose not in (0,1):raise ValueError('pose')
 # Independent normalized scalar translation, not matrix-shader evaluation.
 tx=.5*pose*3/4;ty=.5*pose*1/4
 return [v for x,y,z in VERTICES for v in (x+tx,y+ty,z,1.)]
def golden(pose):
 return [v for y in range(16) for x in range(16) for v in ([0,255,0,255] if 4+3*pose<=x<12+3*pose and 4+pose<=y<12+pose else [0,0,0,255])]
def matrix(tx,ty,wrong=False):
 m=[1.,0,0,0,0,1.,0,0,0,0,1.,0,tx,ty,0,1.]
 return [m[r*4+c] for c in range(4) for r in range(4)] if wrong else m

class Host(d.Host):
 def draw(self,pose,arm):
  if pose not in (0,1) or arm not in ('gpu','cpu_fallback','wrong_weights','wrong_matrix','stalled_pose'):raise ValueError('unregistered case')
  g=self.fn;objects=[];program=0;vao=U();fb=U();rb=U()
  try:
   src=FALLBACK if arm=='cpu_fallback' else VERT.replace('weights/max(dot(weights,vec4(1)),0.000001)','weights') if arm=='wrong_weights' else VERT
   shaders=[self.shader(src,'vert'),self.shader(FRAG,'frag')]
   if not all(x[1] for x in shaders):raise RuntimeError('compile')
   program=g('glCreateProgram',U,[])()
   for sh,_,_ in shaders:g('glAttachShader',None,[U,U])(program,sh)
   names=(C.c_char_p*1)(b'captured');g('glTransformFeedbackVaryings',None,[U,I,C.POINTER(C.c_char_p),U])(program,1,names,0x8c8c)
   g('glLinkProgram',None,[U])(program);ok=I();g('glGetProgramiv',None,[U,U,P])(program,0x8b82,C.byref(ok))
   for sh,_,_ in shaders:g('glDeleteShader',None,[U])(sh)
   if not ok.value:raise RuntimeError('link')
   g('glUseProgram',None,[U])(program);g('glGenVertexArrays',None,[I,P])(1,C.byref(vao));g('glBindVertexArray',None,[U])(vao)
   def buffer(target,data,size):
    obj=U();g('glGenBuffers',None,[I,P])(1,C.byref(obj));objects.append(obj);g('glBindBuffer',None,[U,U])(target,obj);g('glBufferData',None,[U,C.c_ssize_t,P,U])(target,size,data,0x88e4);return obj
   positions=cpu(pose);values=[v for n in range(6) for v in positions[n*4:n*4+3]] if arm=='cpu_fallback' else [v for p in VERTICES for v in p]
   raw=(F*18)(*values);buffer(0x8892,raw,C.sizeof(raw));g('glVertexAttribPointer',None,[U,I,U,U,I,P])(0,3,0x1406,0,0,None);g('glEnableVertexAttribArray',None,[U])(0)
   if arm!='cpu_fallback':
    g('glVertexAttrib4f',None,[U,F,F,F,F])(1,*WEIGHTS);g('glVertexAttribI4ui',None,[U,U,U,U,U])(2,*JOINTS)
    actual_pose=0 if arm=='stalled_pose' else pose
    mats=matrix(.5*actual_pose,0,arm=='wrong_matrix')+matrix(0,.5*actual_pose,arm=='wrong_matrix');raw=(F*32)(*mats);ubo=buffer(0x8a11,raw,128)
    block=g('glGetUniformBlockIndex',U,[U,C.c_char_p])(program,b'Bones')
    if block==0xffffffff:raise RuntimeError('missing UBO')
    size=I();g('glGetActiveUniformBlockiv',None,[U,U,U,P])(program,block,0x8a40,C.byref(size))
    if size.value!=128:raise RuntimeError('unexpected std140 size')
    g('glUniformBlockBinding',None,[U,U,U])(program,block,0);g('glBindBufferBase',None,[U,U,U])(0x8a11,0,ubo)
   feedback=buffer(0x8c8e,None,96);g('glBindBufferBase',None,[U,U,U])(0x8c8e,0,feedback)
   g('glGenFramebuffers',None,[I,P])(1,C.byref(fb));g('glBindFramebuffer',None,[U,U])(0x8d40,fb);g('glGenRenderbuffers',None,[I,P])(1,C.byref(rb));g('glBindRenderbuffer',None,[U,U])(0x8d41,rb);g('glRenderbufferStorage',None,[U,U,I,I])(0x8d41,0x8058,16,16);g('glFramebufferRenderbuffer',None,[U,U,U,U])(0x8d40,0x8ce0,0x8d41,rb)
   if g('glCheckFramebufferStatus',U,[U])(0x8d40)!=0x8cd5:raise RuntimeError('FBO')
   for cap in (0xbd0,0xbe2,0xb71,0xb90,0xc11,0xb44,0x8c89):g('glDisable',None,[U])(cap)
   g('glViewport',None,[I]*4)(0,0,16,16);g('glClearColor',None,[F]*4)(0,0,0,1);g('glClear',None,[U])(0x4000)
   g('glBeginTransformFeedback',None,[U])(4);g('glDrawArrays',None,[U,I,I])(4,0,6);g('glEndTransformFeedback',None,[])()
   g('glBindBuffer',None,[U,U])(0x8c8e,feedback);ptr=g('glMapBufferRange',P,[U,C.c_ssize_t,C.c_ssize_t,U])(0x8c8e,0,96,1)
   if not ptr:raise RuntimeError('map feedback')
   captured=list((F*24).from_buffer_copy(C.string_at(ptr,96)))
   if not g('glUnmapBuffer',U,[U])(0x8c8e):raise RuntimeError('invalid feedback storage')
   pixels=(C.c_ubyte*1024)();g('glReadPixels',None,[I]*4+[U,U,P])(0,0,16,16,0x1908,0x1401,pixels)
   if self.error() or any(not math.isfinite(v) for v in captured):raise RuntimeError('GL/nonfinite capture')
   err=max(abs(a-b) for a,b in zip(captured,positions));image=list(pixels);quality=err<=1e-6 and image==golden(pose)
   return dict(pose=pose,arm=arm,captured_positions=captured,position_max_error=err,pixels=image,pixel_exact=image==golden(pose),quality='PASS' if quality else 'FAIL',vertex_sha256=hashlib.sha256(src.encode()).hexdigest(),fragment_sha256=hashlib.sha256(FRAG.encode()).hexdigest(),std140_bytes=128 if arm!='cpu_fallback' else 0)
  finally:
   g('glUseProgram',None,[U])(0);g('glBindFramebuffer',None,[U,U])(0x8d40,0);g('glBindVertexArray',None,[U])(0)
   for obj in objects:g('glDeleteBuffers',None,[I,P])(1,C.byref(obj))
   for obj,name in [(vao,'glDeleteVertexArrays'),(rb,'glDeleteRenderbuffers'),(fb,'glDeleteFramebuffers')]:
    if obj.value:g(name,None,[I,P])(1,C.byref(obj))
   if program:g('glDeleteProgram',None,[U])(program)
def run(config,output):
 h=Host(config)
 try:rows=[h.draw(pose,arm) for pose in (0,1) for arm in ('gpu','cpu_fallback','wrong_weights','wrong_matrix','stalled_pose') if pose==1 or arm in ('gpu','cpu_fallback')]
 finally:h.close()
 passed=all(r['quality']==('PASS' if r['arm'] in ('gpu','cpu_fallback') else 'FAIL') for r in rows)
 result=dict(status='HOST_PASS' if passed else 'FAIL',gles='3.0',draws=len(rows),rows=rows,cpu_position_goldens={str(p):cpu(p) for p in (0,1)},performance_status='NOT_MEASURED',physical_gpu='NOT_RUN',scope='Two translation matrices, normalized four positive weights, six-vertex quad, two discrete poses; no normals/DQ/hierarchy/interpolation/general animation claims.')
 out=Path(output);out.parent.mkdir(parents=True,exist_ok=True);out.write_text(json.dumps(result,indent=2)+'\n');return result
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--config',type=Path,required=True);p.add_argument('--output',required=True);a=p.parse_args();r=run(json.loads(a.config.read_text()),a.output);print(r['status']);raise SystemExit(r['status']!='HOST_PASS')
