"""Individually authored wrong transformations and independent scalar CPU reference."""
import math
from build_cases import fragment
WRONG=[
 ('branch-select','vec4(mix(0.75,0.25,step(0.5,uv.x)),uv.y,0.0,1.0)','reversed branch arms'),
 ('multiply-divide','vec4(uv*2.0,0.25,1.0)','reciprocal inverted'),
 ('square-pow','vec4(uv.x,uv.y,0.0,1.0)','power removed'),
 ('clamp-minmax','vec4(min(uv,vec2(0.75)),0.0,1.0)','lower clamp omitted'),
 ('mix-linear','vec4(uv.x+uv.y,0.0,0.0,1.0)','average scale omitted'),
 ('constant-fold','vec4(uv,0.375,1.0)','incorrect constant fold'),
 ('vector-scalar','vec4(uv*vec2(0.5,0.25),0.0,1.0)','unequal vector coefficients'),
 ('dot-expand','vec4(uv.x*0.25,0.0,0.0,1.0)','dot y term omitted'),
 ('factor-common','vec4(uv.x*0.5,uv.y,0.0,1.0)','coefficient term omitted'),
 ('abs-branch','vec4(uv.x-0.5,uv.y,0.0,1.0)','negative half loses absolute value'),
 ('precision-safe','vec4(floor(uv*2.0)/2.0,0.25,1.0)','explicit coarse quantization; not claimed mediump failure'),
 ('premultiply','vec4(uv,0.5,0.5)','premultiplication omitted'),
 ('swizzle','vec4(uv,0.0,1.0)','swizzle omitted'),
 ('reciprocal-divide','vec4(uv*vec2(0.25,0.5),0.0,1.0)','divisors exchanged'),
 ('negative-alpha','vec4(uv,0.25,0.0)','alpha zeroed'),
 ('negative-color','vec4(1.0-uv,0.25,1.0)','coordinates inverted')]
def wrong(name):
 _,expression,reason=next(x for x in WRONG if x[0]==name);return fragment(expression),reason
def golden(name):
 pixels=[]
 for y in range(4):
  for x in range(4):
   u,v=(x+.5)/4,(y+.5)/4
   values={
    'branch-select':(.25 if u<.5 else .75,v,0,1), 'multiply-divide':(u/2,v/2,.25,1),
    'square-pow':(u*u,v,0,1),'clamp-minmax':(max(.25,min(.75,u)),max(.25,min(.75,v)),0,1),
    'mix-linear':((u+v)/2,0,0,1),'constant-fold':(u,v,.5,1),'vector-scalar':(u/2,v/2,0,1),
    'dot-expand':((u+v)/4,0,0,1),'factor-common':(.75*u,v,0,1),'abs-branch':(abs(u-.5),v,0,1),
    'precision-safe':(u,v,.25,1),'premultiply':(u/2,v/2,.25,.5),'swizzle':(v,u,0,1),
    'reciprocal-divide':(u/2,v/4,0,1),'negative-alpha':(u,v,.25,.5),'negative-color':(u,v,.25,1)}[name]
   pixels.extend(math.floor(255*z+.5) for z in values)
 return pixels
