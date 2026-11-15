"""Finite authored GLES3 experiment corpus; not measured optimizations."""
import hashlib,json
from pathlib import Path
HERE=Path(__file__).resolve().parent
VERTEX='''#version 300 es
void main(){vec2 p=vec2((gl_VertexID<<1)&2,gl_VertexID&2);gl_Position=vec4(p*2.0-1.0,0.0,1.0);}
'''
def fragment(expression,precision='highp'):
 return '#version 300 es\nprecision '+precision+' float;\nlayout(location=0) out vec4 color;\nvoid main(){vec2 uv=gl_FragCoord.xy/4.0; color='+expression+';}\n'
def corpus():
 # 16 distinct transformations, all sampled at exact binary pixel centres.
 pairs=[
 ('branch-select','vec4(uv.x<0.5?0.25:0.75,uv.y,0.0,1.0)','vec4(mix(0.25,0.75,step(0.5,uv.x)),uv.y,0.0,1.0)'),
 ('multiply-divide','vec4(uv/2.0,0.25,1.0)','vec4(uv*0.5,0.25,1.0)'),
 ('square-pow','vec4(pow(uv.x,2.0),uv.y,0.0,1.0)','vec4(uv.x*uv.x,uv.y,0.0,1.0)'),
 ('clamp-minmax','vec4(clamp(uv,0.25,0.75),0.0,1.0)','vec4(min(max(uv,vec2(0.25)),vec2(0.75)),0.0,1.0)'),
 ('mix-linear','vec4(mix(uv.x,uv.y,0.5),0.0,0.0,1.0)','vec4((uv.x+uv.y)*0.5,0.0,0.0,1.0)'),
 ('constant-fold','vec4(uv,0.125+0.375,1.0)','vec4(uv,0.5,1.0)'),
 ('vector-scalar','vec4(uv*vec2(0.5),0.0,1.0)','vec4(uv*0.5,0.0,1.0)'),
 ('dot-expand','vec4(dot(uv,vec2(0.25)),0.0,0.0,1.0)','vec4(uv.x*0.25+uv.y*0.25,0.0,0.0,1.0)'),
 ('factor-common','vec4(uv.x*0.25+uv.x*0.5,uv.y,0.0,1.0)','vec4(uv.x*0.75,uv.y,0.0,1.0)'),
 ('abs-branch','vec4(abs(uv.x-0.5),uv.y,0.0,1.0)','vec4(uv.x<0.5?0.5-uv.x:uv.x-0.5,uv.y,0.0,1.0)'),
 ('precision-safe','vec4(uv,0.25,1.0)','vec4(uv,0.25,1.0)'),
 ('premultiply','vec4(vec3(uv,0.5)*0.5,0.5)','vec4(uv*0.5,0.25,0.5)'),
 ('swizzle','vec4(uv.y,uv.x,0.0,1.0)','vec4(uv.yx,0.0,1.0)'),
 ('reciprocal-divide','vec4(uv.x/2.0,uv.y/4.0,0.0,1.0)','vec4(uv*vec2(0.5,0.25),0.0,1.0)'),
 ('negative-alpha','vec4(uv,0.25,0.5)','vec4(uv,0.25,1.0)'),
 ('negative-color','vec4(uv,0.25,1.0)','vec4(uv.yx,0.25,1.0)')]
 return [dict(id=n,category='shader_ab',sources={'a':fragment(a),'b':fragment(b,'mediump' if n=='precision-safe' else 'highp')},expected_quality='FAIL' if n.startswith('negative') else 'PASS',performance_status='NOT_MEASURED',scope='4x4 authored arithmetic/precision control; no general equivalence',counterexample='Any changed alpha/color or out-of-domain precision input must be revalidated') for n,a,b in pairs]
def write():
 rows=corpus()
 for row in rows:
  d=HERE/'sources'/row['id'];d.mkdir(parents=True,exist_ok=True);(d/'shader.vert').write_text(VERTEX)
  for arm,src in row['sources'].items():(d/(arm+'.frag')).write_text(src)
  row['source_sha256']={k:hashlib.sha256(v.encode()).hexdigest() for k,v in row['sources'].items()}
 (HERE/'cases.json').write_text(json.dumps(rows,indent=2)+'\n')
if __name__=='__main__':write()
