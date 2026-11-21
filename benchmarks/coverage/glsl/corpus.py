"""Authored positive/negative GLSL ES family controls, not exhaustive CTS."""
def graphics(body,version=300,decl='',vertex=None):
 head=f'#version {version} es\n' if version!=100 else '#version 100\n'
 v=vertex or head+'void main(){gl_Position=vec4(0,0,0,1);}'
 f=head+(decl+'\nprecision highp float;\n' if decl.startswith('#extension') else 'precision highp float;\n'+decl+'\n')+('out vec4 color;\n' if version!=100 else '')+'void main(){'+body+'}'
 return {'shader.vert':v,'shader.frag':f}
def compute(body,decl='',version=310):return {'shader.comp':f'#version {version} es\nprecision highp float;\nlayout(local_size_x=1) in;\n'+decl+'\nvoid main(){'+body+'}'}
def cases():
 pairs=[
 ('migration-100',graphics('gl_FragColor=vec4(1);',100),graphics('color=vec4(1);',100)),
 ('lexical-preprocessor',graphics('color=vec4(VALUE);',decl='#define VALUE 0.5'),graphics('color=vec4(VALUE);')),
 ('precision',graphics('mediump float x=.5;color=vec4(x);'),graphics('precision bogus float;color=vec4(1);')),
 ('types-arrays-matrices',graphics('mat2 m=mat2(1);float a[2]=float[2](.2,.3);color=vec4(m*vec2(a[0]),0,1);'),graphics('mat2 m=mat2(1);vec3 x=m*vec3(1);color=vec4(x,1);')),
 ('control-flow',graphics('float x=0.;for(int i=0;i<3;i++){if(i==1)continue;x+=.1;}color=vec4(x);'),graphics('break;color=vec4(1);')),
 ('uniform-std140',graphics('color=u.c;',decl='layout(std140) uniform Block{vec4 c;}u;'),graphics('color=u.c;',decl='layout(std430) uniform Block{vec4 c;}u;')),
 ('layout-output',graphics('color=vec4(1);'),graphics('color=vec4(1);',decl='layout(location=-1) out vec4 invalid;')),
 ('texture-derivative',graphics('color=texture(tex,vec2(.5))+vec4(dFdx(gl_FragCoord.x));',decl='uniform sampler2D tex;'),graphics('color=texture(tex,vec3(.5));',decl='uniform sampler2D tex;')),
 ('compute-ssbo-std430',compute('b.x[0]=1u;', 'layout(std430,binding=0) buffer B{uint x[];}b;'),compute('b.x[0]=1u;', 'layout(std430,binding=0) buffer B{uint x[];}b;',300)),
 ('atomics-barriers',compute('atomicAdd(b.x,1u);memoryBarrierBuffer();barrier();','layout(std430,binding=0) buffer B{uint x;}b;'),compute('atomicAdd(b.x,1.0);','layout(std430,binding=0) buffer B{float x;}b;')),
 ('image-store',compute('imageStore(img,ivec2(0),vec4(1));','layout(rgba8,binding=0) writeonly uniform highp image2D img;'),compute('imageStore(img,ivec2(0),vec4(1));','layout(rgba8,binding=0) readonly uniform highp image2D img;')),
 ('extension-gate',graphics('gl_FragColor=vec4(dFdx(gl_FragCoord.x));',100,decl='#extension GL_OES_standard_derivatives : require'),graphics('color=vec4(1);',decl='#extension GL_FAKE_coverage_unavailable : require')),
 ]
 v='#version 300 es\nout mediump vec3 value;void main(){value=vec3(1);gl_Position=vec4(0);}'
 pairs.append(('varying-interface',graphics('color=vec4(value,1);',decl='in mediump vec3 value;',vertex=v),graphics('color=value;',decl='in mediump vec4 value;',vertex=v)))
 v='#version 300 es\nflat out highp int value;void main(){value=1;gl_Position=vec4(0);}'
 pairs.append(('interpolation',graphics('color=vec4(float(value));',decl='flat in highp int value;',vertex=v),graphics('color=vec4(float(value));',decl='in highp int value;',vertex=v)))
 geom='#version 320 es\nlayout(points) in;layout(points,max_vertices=1) out;void main(){gl_Position=gl_in[0].gl_Position;EmitVertex();EndPrimitive();}'
 src=graphics('color=vec4(1);',320);src['shader.geom']=geom
 neg=dict(src);neg['shader.geom']=geom.replace('#version 320','#version 300')
 pairs.append(('geometry-version',src,neg))
 tc='#version 320 es\nlayout(vertices=3) out;void main(){gl_out[gl_InvocationID].gl_Position=gl_in[gl_InvocationID].gl_Position;gl_TessLevelOuter[0]=1.;gl_TessLevelOuter[1]=1.;gl_TessLevelOuter[2]=1.;gl_TessLevelInner[0]=1.;}'
 te='#version 320 es\nlayout(triangles,equal_spacing,cw) in;void main(){gl_Position=gl_in[0].gl_Position;}'
 src=graphics('color=vec4(1);',320);src.update({'shader.tesc':tc,'shader.tese':te});neg=dict(src);neg['shader.tesc']=tc.replace('#version 320','#version 310')
 pairs.append(('tessellation-version',src,neg))
 return [dict(id=name+'-'+arm,family=name,expected=arm=='positive',sources=src) for name,a,b in pairs for arm,src in [('positive',a),('negative',b)]]
if __name__=='__main__':
 import json
 from pathlib import Path
 root=Path(__file__).parent/'fixtures'
 for row in cases():
  d=root/row['id'];d.mkdir(parents=True,exist_ok=True)
  for name,text in row['sources'].items():(d/name).write_text(text+'\n')
 (root.parent/'cases.json').write_text(json.dumps(cases(),indent=2)+'\n')
