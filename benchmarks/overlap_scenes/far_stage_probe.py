#!/usr/bin/env python3
"""Diagnostic stage reads of unchanged reconstruction shaders, no acceptance changes."""
import argparse,ctypes as C,hashlib,json,math,zipfile
from pathlib import Path
import far_reconstruction as f

class Probe(f.FarHost):
 def __init__(self,config):
  self.stages={};self.fb_binds=0;self.blend_enables=0;super().__init__(config)
 def capture(self,name,size):
  pixels=(C.c_ubyte*(size*size*4))()
  super().fn('glReadPixels',None,[f.I]*4+[f.U,f.U,f.P])(0,0,size,size,0x1908,0x1401,pixels)
  self.stages[name]=list(pixels)
 def fn(self,name,restype,args,*extra):
  original=super().fn(name,restype,args,*extra)
  if name=='glBindFramebuffer':
   def bind(*values):
    obj=values[1].value if hasattr(values[1],'value') else values[1]
    if obj:
     self.fb_binds+=1
     if self.fb_binds==2:self.capture('far32',32)
    return original(*values)
   return bind
  if name=='glEnable':
   def enable(cap):
    if cap==0xbe2:
     self.blend_enables+=1
     if self.blend_enables==2:self.capture('resolve64',64)
    return original(cap)
   return enable
  return original

def resolve(low):
 out=[]
 for y in range(64):
  for x in range(64):
   px,py=(x+.5)/2-.5,(y+.5)/2-.5;ix,iy=math.floor(px),math.floor(py);wx,wy=px-ix,py-iy
   for k in range(4):
    value=sum(low[(max(0,min(31,iy+dy))*32+max(0,min(31,ix+dx)))*4+k]*weight for dx,dy,weight in [(0,0,(1-wx)*(1-wy)),(1,0,wx*(1-wy)),(0,1,(1-wx)*wy),(1,1,wx*wy)])
    out.append(math.floor(value+.5))
 return out

def run(config,output):
 far,near=f.scene();h=Probe(config)
 try:
  final=h.draw(far,near,0,32);h.stages['foreground64']=final
  if set(h.stages)!={'far32','resolve64','foreground64'}:raise RuntimeError('stage interception incomplete')
  if h.error():raise RuntimeError('probe GL error')
  actual=h.stages
 finally:h.close()
 low=f.cpu_layers(far,0,32);resolved=resolve(low);cpu=dict(far32=low,resolve64=resolved,foreground64=f.cpu_layers(near,0,64,resolved))
 if cpu['foreground64']!=f.cpu(far,near,0,32):raise RuntimeError('independent resolve disagreement')
 taps=[]
 for x,y,w in [(14,11,3/16),(15,11,1/16),(14,12,9/16),(15,12,3/16)]:
  idx=(y*32+x)*4;taps.append(dict(x=x,y=y,weight=w,cpu=low[idx:idx+4],actual=actual['far32'][idx:idx+4]))
 def weighted(which):return [sum(t[which][k]*t['weight'] for t in taps) for k in range(4)]
 index=(24*64+29)*4
 point=dict(x=29,y=24,taps=taps,cpu_weighted_rgba=weighted('cpu'),actual_low32_weighted_rgba=weighted('actual'),actual_low32_half_up_prediction=[math.floor(v+.5) for v in weighted('actual')],stages={k:dict(actual=v[index:index+4],cpu=cpu[k][index:index+4]) for k,v in actual.items() if k!='far32'})
 out=Path(output);out.parent.mkdir(parents=True,exist_ok=True);archive=out.with_suffix('.zip')
 with zipfile.ZipFile(archive,'w',compression=zipfile.ZIP_DEFLATED) as z:
  for prefix,images in [('actual',actual),('cpu',cpu)]:
   for name,pixels in images.items():
    info=zipfile.ZipInfo(prefix+'-'+name+'.rgba',(1980,1,1,0,0,0));info.compress_type=zipfile.ZIP_DEFLATED;info.external_attr=0o100644<<16;z.writestr(info,bytes(pixels))
 errors={k:max(abs(a-b) for a,b in zip(actual[k],cpu[k])) for k in actual}
 resolved_from_actual_low=resolve(actual['far32'])
 stage_error=max(abs(a-b) for a,b in zip(actual['resolve64'],resolved_from_actual_low))
 diagnostic_ok=stage_error<=1 and point['stages']['resolve64']['actual']==point['actual_low32_half_up_prediction'] and point['stages']['foreground64']['actual']==point['stages']['resolve64']['actual']
 report=dict(status='HOST_PASS' if diagnostic_ok else 'FAIL',diagnostic_only=True,original_visual_acceptance='UNCHANGED_NOT_EVALUATED',actual_low_to_resolve_cpu_max_error=stage_error,camera=0,diagnostic_readbacks=3,complete_stage_bytes={k:len(v) for k,v in actual.items()},cpu_max_errors=errors,point=point,source_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),reused_source_sha256=hashlib.sha256(Path(f.__file__).read_bytes()).hexdigest(),archive=dict(file=archive.name,sha256=hashlib.sha256(archive.read_bytes()).hexdigest()),performance_status='NOT_MEASURED',scope='Adds blocking readbacks after far32 blending and resolve64 to existing final readback, unchanged draw/shader inputs. These observations localize this diagnostic execution, not an exclusive cause or specification violation. CPU half-up normalized rounding is an independent finite oracle, not the only valid implementation. No image budget changed.')
 out.write_text(json.dumps(report,indent=2)+'\n');return report
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--config',type=Path,required=True);p.add_argument('--output',required=True);a=p.parse_args();r=run(json.loads(a.config.read_text()),a.output);print(r['status']);raise SystemExit(r['status']!='HOST_PASS')
