#!/usr/bin/env python3
"""Explicit RGBA16F accumulation, final RGBA8 quantization and UNORM diagnostics."""
import argparse,ctypes as C,hashlib,json,math,struct,sys,zipfile
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parent))
import projected as p
import tiered as t
U,I,P,F=p.U,p.I,p.P,p.F
project=p.project
class UnsupportedCapability(RuntimeError):pass
class FloatHost(p.diff.Host):
 def draw(self,objects,camera,resolution=64,full_float=False):
  extensions=self.metadata['extensions']
  if full_float and not ({'GL_EXT_color_buffer_float','GL_EXT_float_blend'} <= set(extensions)):raise UnsupportedCapability('Required float32 color/blend capabilities absent')
  if not full_float and not any(x in extensions for x in ('GL_EXT_color_buffer_float','GL_EXT_color_buffer_half_float')):raise UnsupportedCapability('Required half-float color capability absent')
  fb=U();rb=U();vao=U();dst=U();drb=U();prog=0; SIZE=resolution
  try:
   prog,compile_info=self.program({'shader.vert':p.VERT.replace('0.03125',str(2/resolution)), 'shader.frag':p.FRAG.replace('/64.0','/'+str(float(resolution)))})
   if not compile_info['compile'] or not compile_info['link']:raise RuntimeError('shader compile/link failure')
   self.fn('glGenFramebuffers',None,[I,P])(1,C.byref(fb));self.fn('glBindFramebuffer',None,[U,U])(0x8d40,fb)
   self.fn('glGenRenderbuffers',None,[I,P])(1,C.byref(rb));self.fn('glBindRenderbuffer',None,[U,U])(0x8d41,rb)
   self.fn('glRenderbufferStorage',None,[U,U,I,I])(0x8d41,0x8814 if full_float else 0x881a,SIZE,SIZE);self.fn('glFramebufferRenderbuffer',None,[U,U,U,U])(0x8d40,0x8ce0,0x8d41,rb)
   if self.fn('glCheckFramebufferStatus',U,[U])(0x8d40)!=0x8cd5:raise RuntimeError('FBO incomplete')
   for cap in (0xbd0,0xb71,0xb90,0xc11,0xb44):self.fn('glDisable',None,[U])(cap)
   self.fn('glEnable',None,[U])(0xbe2);self.fn('glBlendFuncSeparate',None,[U]*4)(0x302,0x303,1,0x303)
   self.fn('glViewport',None,[I]*4)(0,0,SIZE,SIZE);self.fn('glClearColor',None,[F]*4)(0,0,0,0);self.fn('glClear',None,[U])(0x4000)
   self.fn('glGenVertexArrays',None,[I,P])(1,C.byref(vao));self.fn('glBindVertexArray',None,[U])(vao);self.fn('glUseProgram',None,[U])(prog)
   loc={n:self.fn('glGetUniformLocation',I,[U,C.c_char_p])(prog,n.encode()) for n in ('rect','tint','mode')}
   previous=None; self.tint_updates=0
   for o in objects:
    self.fn('glUniform4f',None,[I,F,F,F,F])(loc['rect'],*project(o,camera))
    if o['color']!=previous:
     self.fn('glUniform4f',None,[I,F,F,F,F])(loc['tint'],*o['color']); self.tint_updates+=1; previous=o['color']
    self.fn('glUniform1i',None,[I,I])(loc['mode'],o['mode']);self.fn('glDrawArrays',None,[U,I,I])(4,0,6)
   if True:
    self.fn('glGenFramebuffers',None,[I,P])(1,C.byref(dst));self.fn('glBindFramebuffer',None,[U,U])(0x8ca9,dst)
    self.fn('glGenRenderbuffers',None,[I,P])(1,C.byref(drb));self.fn('glBindRenderbuffer',None,[U,U])(0x8d41,drb)
    self.fn('glRenderbufferStorage',None,[U,U,I,I])(0x8d41,0x8058,64,64)
    self.fn('glFramebufferRenderbuffer',None,[U,U,U,U])(0x8ca9,0x8ce0,0x8d41,drb)
    if self.fn('glCheckFramebufferStatus',U,[U])(0x8ca9)!=0x8cd5:raise RuntimeError('resolve FBO incomplete')
    self.fn('glBindFramebuffer',None,[U,U])(0x8ca8,fb)
    self.fn('glBlitFramebuffer',None,[I]*8+[U,U])(0,0,SIZE,SIZE,0,0,64,64,0x4000,0x2600)
    self.fn('glBindFramebuffer',None,[U,U])(0x8d40,dst)
   SIZE=64
   buf=(C.c_ubyte*(SIZE*SIZE*4))();self.fn('glReadPixels',None,[I,I,I,I,U,U,P])(0,0,SIZE,SIZE,0x1908,0x1401,buf)
   if self.error():raise RuntimeError('GL operation failed')
   return list(buf)
  finally:
   self.fn('glUseProgram',None,[U])(0);self.fn('glBindFramebuffer',None,[U,U])(0x8d40,0);self.fn('glBindVertexArray',None,[U])(0)
   if drb.value:self.fn('glDeleteRenderbuffers',None,[I,P])(1,C.byref(drb))
   if dst.value:self.fn('glDeleteFramebuffers',None,[I,P])(1,C.byref(dst))
   if prog:self.fn('glDeleteProgram',None,[U])(prog)
   if vao.value:self.fn('glDeleteVertexArrays',None,[I,P])(1,C.byref(vao))
   if rb.value:self.fn('glDeleteRenderbuffers',None,[I,P])(1,C.byref(rb))
   if fb.value:self.fn('glDeleteFramebuffers',None,[I,P])(1,C.byref(fb))

def q8(v):return math.floor(v*255+.5)/255
def half(v):return struct.unpack('e',struct.pack('e',v))[0]
def reference(obs,cam,model):
 # Independent scalar equations. Diagnostic models are never substituted for acceptance goldens.
 pixels=[0.0]*16384
 for o in obs:
  cx,cy,rx,ry=project(o,cam)
  for y in range(64):
   v=((y+.5)/64*2-1-cy)/ry
   if not -1<v<1:continue
   for x in range(64):
    u=((x+.5)/64*2-1-cx)/rx
    if not -1<u<1:continue
    a=o['color'][3]*(math.exp(-3*(u*u+v*v)) if o['mode']==0 else 1);cs=o['color'][:3]+[1]
    if model in ('source8','split8'):a=q8(a);cs=list(map(q8,cs))
    i=(y*64+x)*4
    for k in range(4):
     value=cs[k]*a+pixels[i+k]*(1-a)
     if model=='split8':value=q8(cs[k]*a)+q8(pixels[i+k]*(1-a))
     pixels[i+k]=min(1,max(0,half(value) if model=='half' else q8(value) if model!='linear' else value))
 return [min(255,max(0,math.floor(x*255+.5))) for x in pixels]
def summary(a,b):
 e=[abs(x-y) for x,y in zip(a,b)];return dict(max_error=max(e),different_channels=sum(x>0 for x in e),mean_error=sum(e)/len(e))
def run(config,output):
 path=Path(output);path.parent.mkdir(parents=True,exist_ok=True);rows=[];diagnostics=[];artifacts={};readback_count=0;host=FloatHost(config);unorm=t.TierHost(config)
 try:
  for n in (8,24,48):
   for cam in (-.3,0,.3):
    obs=t.scene(n);base=unorm.draw(obs,cam);readback_count+=1;prefix=f'n{n}-cam{cam}'
    models={model:reference(obs,cam,model) for model in ('ideal8','source8','split8','half','linear')}
    diagnostics.append(dict(count=n,camera=cam,rgba8_vs_models={k:summary(base,v) for k,v in models.items()}))
    try:actual=host.draw(obs,cam);readback_count+=1
    except UnsupportedCapability:
     rows.append(dict(count=n,camera=cam,status='NOT_SUPPORTED',fallback='RGBA8_ONLY_IF_ORIGINAL_CPU_GATE_PASSES',baseline_quality='PASS' if t.accepted(p.metrics(base,models['ideal8'])) else 'FAIL'));continue
    bad=host.draw(obs[:len(obs)//2],cam);readback_count+=1
    m=p.metrics(actual,models['half']);negative=p.metrics(bad,models['half'])
    rows.append(dict(count=n,camera=cam,status='PASS' if t.accepted(m) and not t.accepted(negative) else 'FAIL',float_metrics=m,original_rgba8_golden_metrics=p.metrics(actual,models['ideal8']),negative_metrics=negative,format_change_delta=summary(actual,base),linear_ideal_comparison=summary(actual,models['linear']),artifact_prefix=prefix))
    try:
     fp32=host.draw(obs,cam,full_float=True);readback_count+=1;bad32=host.draw(obs[:len(obs)//2],cam,full_float=True);readback_count+=1
     m32=p.metrics(fp32,models['linear']);n32=p.metrics(bad32,models['linear'])
     rows[-1]['float32_control']=dict(status='PASS' if t.accepted(m32) and not t.accepted(n32) else 'FAIL',metrics=m32,original_rgba8_golden_metrics=p.metrics(fp32,models['ideal8']),half_golden_metrics=p.metrics(fp32,models['half']),negative_metrics=n32,format_change_delta=summary(fp32,base))
     artifacts[prefix+'-fp32.rgba']=bytes(fp32);artifacts[prefix+'-bad32.rgba']=bytes(bad32)
    except UnsupportedCapability:rows[-1]['float32_control']=dict(status='NOT_SUPPORTED',fallback='Do not select without advertised color/float-blend capability and passing readback')
    for name,pix in dict(actual=actual,negative=bad,baseline8=base,**models).items():artifacts[prefix+'-'+name+'.rgba']=bytes(pix)
 finally:host.close();unorm.close()
 archive=path.with_suffix('.zip')
 with zipfile.ZipFile(archive,'w',compression=zipfile.ZIP_DEFLATED) as z:
  for name,value in sorted(artifacts.items()):
   info=zipfile.ZipInfo(name,(1980,1,1,0,0,0));info.compress_type=zipfile.ZIP_DEFLATED;info.external_attr=0o100644<<16;z.writestr(info,value)
 r=dict(status='HOST_PASS' if all(x['status']=='PASS' and x.get('float32_control',{}).get('status')=='PASS' for x in rows) else 'FAIL',scope='Explicit linear RGBA16F accumulation with final RGBA8 blit; intentionally different format contract, not equivalence to per-layer RGBA8',performance_status='NOT_MEASURED',readbacks=readback_count,diagnostic_models='hypotheses only; never acceptance golden for RGBA8',source_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),rows=rows,diagnostics=diagnostics,artifact_archive=dict(file=archive.name,sha256=hashlib.sha256(archive.read_bytes()).hexdigest(),instructions='Extract beside report, all rgba files 64x64 bottom-up RGBA8'))
 r['shader_source_sha256']={'vertex':hashlib.sha256(p.VERT.encode()).hexdigest(),'fragment':hashlib.sha256(p.FRAG.encode()).hexdigest()}
 r['explicit_float32_correction']='PASS' if all(x.get('float32_control',{}).get('status')=='PASS' for x in rows) else 'NOT_ACCEPTED'
 r['contract_status']='PASS' if all(x.get('float32_control',{}).get('status') =='PASS' for x in rows) else 'FAIL'
 path.write_text(json.dumps(r,indent=2)+'\n');return r
if __name__=='__main__':
 parser=argparse.ArgumentParser();parser.add_argument('--config',required=True);parser.add_argument('--output',required=True);parser.add_argument('--require-contract-only',action='store_true');a=parser.parse_args();r=run(json.loads(Path(a.config).read_text()),a.output);print(r['status']);raise SystemExit(r['contract_status']!='PASS' if a.require_contract_only else r['status']!='HOST_PASS')
