"""Finite global-order proof from complete per-pixel layer depths, not OIT tuning."""
import math

def decide(layers,width,height):
 if type(width) is not int or type(height) is not int or width<1 or height<1:return {'selection':'UNAVAILABLE','reason':'INVALID_EXTENT'}
 if not isinstance(layers,list) or not layers:return {'selection':'UNAVAILABLE','reason':'NO_LAYERS'}
 if any(not isinstance(l,dict) for l in layers):return {'selection':'UNAVAILABLE','reason':'MALFORMED_LAYER'}
 ids=[l.get('id') for l in layers]
 if any(not isinstance(i,str) or not i for i in ids) or len(ids)!=len(set(ids)):return {'selection':'UNAVAILABLE','reason':'INVALID_IDS'}
 for l in layers:
  z=l.get('depths');c=l.get('rgba')
  if not isinstance(z,list) or len(z)!=width*height or any(type(v) not in (int,float) or not math.isfinite(v) or not 0<=v<=1 for v in z):return {'selection':'UNAVAILABLE','reason':'INCOMPLETE_DEPTH_EVIDENCE'}
  if not isinstance(c,list) or len(c)!=4 or any(type(v) not in (int,float) or not math.isfinite(v) or not 0<=v<=1 for v in c):return {'selection':'UNAVAILABLE','reason':'INVALID_COLOR'}
 # Every admitted pair has one strict depth ordering for every covered sample.
 edges=set()
 for i,a in enumerate(layers):
  for b in layers[i+1:]:
   signs={1 if x>y else -1 if x<y else 0 for x,y in zip(a['depths'],b['depths'])}
   if 0 in signs:return {'selection':'UNAVAILABLE','reason':'AMBIGUOUS_TIE'}
   if len(signs)!=1:return {'selection':'UNAVAILABLE','reason':'CROSSING_PER_PIXEL_ORDER'}
   edges.add((a['id'],b['id']) if signs=={1} else (b['id'],a['id']))
 order=[];remaining=set(ids)
 while remaining:
  ready=sorted(v for v in remaining if not any(b==v and a in remaining for a,b in edges))
  if not ready:return {'selection':'UNAVAILABLE','reason':'CYCLIC_ORDER'}
  order+=ready;remaining-=set(ready)
 return {'selection':'EXACT_SORTED_ALPHA','reason':'STRICT_GLOBAL_ORDER_FOR_FINITE_FULL_COVERAGE_GRID','far_to_near':order,'scope':'Requires complete validated full-coverage depths for this sample grid, straight RGBA and no refraction; not arbitrary mesh proof','performance':'NOT_MEASURED'}
