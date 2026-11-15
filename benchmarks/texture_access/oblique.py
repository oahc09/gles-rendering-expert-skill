#!/usr/bin/env python3
"""Affine oblique texture footprint and locality controls, not a speed benchmark."""
import argparse,ctypes as C,json
from pathlib import Path
import mechanisms as m
class RampHost(m.TextureHost):
 def fn(self,name,restype,args,*extra):
  original=super().fn(name,restype,args,*extra)
  if name=='glTexImage2D':
   def upload(*unused):
    raw=(C.c_ubyte*(64*64*4))(*[v for y in range(64) for x in range(64) for v in (x*4,y*4,64,255)])
    original(0xde1,0,0x8058,64,64,0,0x1908,0x1401,raw)
   return upload
  if name=='glTexParameterf':
   def aniso(target,pname,value):original(target,pname,1.0 if getattr(self,'isotropic',False) else value)
   return aniso
  return original

def controls():
 rows=[]
 for scattered in [False,True]:
  # Same set of texels, different spatial order. Explicit mip 0 prevents implicit
  # derivative/LOD changes from becoming a confounder in the locality control.
  expr='ivec2(gl_FragCoord.xy)'
  coords=[(x,y) for y in range(4) for x in range(4)]
  if scattered:expr='ivec2((int(gl_FragCoord.x)*3+int(gl_FragCoord.y)*2)%4,(int(gl_FragCoord.y)*3)%4)';coords=[((x*3+y*2)%4,(y*3)%4) for x,y in coords]
  golden=[v for x,y in coords for v in ((16+x*8)*4,(16+y*8)*4,64,255)]
  rows.append(dict(id='scattered' if scattered else 'coherent',mode='direct',source=m.source('texelFetch(tex,ivec2(16)+('+expr+')*8,0)'),golden=golden,tolerance=0))
 # x derivative length=.125, y derivative ~.0215: anisotropic footprint with
 # shear. The affine ramp's filter average equals its center, away from edges.
 golden=[v for y in range(4) for x in range(4) for v in (round(256*(.2+.125*(x+.5)+.02*(y+.5))-2),round(256*(.4+.0078125*(y+.5))-2),64,255)]
 expr='textureGrad(tex,vec2(.2+.125*gl_FragCoord.x+.02*gl_FragCoord.y,.4+.0078125*gl_FragCoord.y),vec2(.125,0.),vec2(.02,.0078125))'
 rows.append(dict(id='oblique-affine',mode='aniso',source=m.source(expr),golden=golden,tolerance=3))
 return rows

def run(config,output):
 h=RampHost(config)
 try:
  rows=[]
  for c in controls():
   h.isotropic=False;row=h.execute(c);row['logical_texture_bytes']=16384+(5460 if c['mode']=='aniso' else 0);rows.append(row)
   if c['mode']=='aniso':
    h.isotropic=True;row=h.execute(dict(c,id='oblique-isotropic-fallback'));row['logical_texture_bytes']=21844;rows.append(row)
  if any(x['gl_error'] or x['quality']!='PASS' for x in rows):raise RuntimeError('oracle failure')
  result=dict(status='HOST_PASS',experiments=rows,extension_present='GL_EXT_texture_filter_anisotropic' in h.metadata['extensions'],fallback='isotropic legal trilinear filtering',performance_status='NOT_MEASURED',scope='64x64 affine texture; explicit mip0 locality permutation; oblique affine finite footprint center oracle tolerance3. Not general anisotropic kernel/image-quality equivalence or performance.')
 finally:h.close()
 Path(output).parent.mkdir(parents=True,exist_ok=True);Path(output).write_text(json.dumps(result,indent=2)+'\n');return result
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--config',required=True);p.add_argument('--output',required=True);a=p.parse_args();print(run(json.loads(Path(a.config).read_text()),a.output)['status'])
