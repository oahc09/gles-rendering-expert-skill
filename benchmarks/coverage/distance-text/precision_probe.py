#!/usr/bin/env python3
"""Independent precision intervention; original collector is unchanged."""
import argparse,ctypes as C,gzip,hashlib,importlib.util,json,math,struct
from pathlib import Path
HERE=Path(__file__).resolve().parent
sp=importlib.util.spec_from_file_location('distance_original',HERE/'run.py');base=importlib.util.module_from_spec(sp);sp.loader.exec_module(base)
FETCH='''vec3 explicitSample(vec2 uv){vec2 p=uv*8.0-0.5;ivec2 q=ivec2(floor(p));vec2 f=fract(p);vec3 a=texelFetch(atlas,clamp(q,ivec2(0),ivec2(7)),0).rgb;vec3 b=texelFetch(atlas,clamp(q+ivec2(1,0),ivec2(0),ivec2(7)),0).rgb;vec3 c=texelFetch(atlas,clamp(q+ivec2(0,1),ivec2(0),ivec2(7)),0).rgb;vec3 d=texelFetch(atlas,clamp(q+ivec2(1,1),ivec2(0),ivec2(7)),0).rgb;return mix(mix(a,b,f.x),mix(c,d,f.x),f.y);}
'''
MODES=('original','highp_hardware','highp_four_tap')
def transform(source,mode,diagnostic=None):
 if mode not in MODES or diagnostic not in (None,0,1,2,3):raise ValueError('fixed probe')
 if mode!='original':source=source.replace('uniform sampler2D atlas','uniform highp sampler2D atlas')
 if mode=='highp_four_tap':
  source=source.replace('void main()',FETCH+'void main()').replace('texture(atlas,gl_FragCoord','explicitSample(gl_FragCoord').replace(').rgb;float a=',');float a=')
 if diagnostic is not None:
  source=source.replace('precision highp float;', 'precision highp float;precision highp int;')
  value=f's[{diagnostic}]' if diagnostic<3 else 'a'
  source=source.replace('color=vec4(vec3(a),1);',f'uint bits=floatBitsToUint({value});color=vec4(float(bits&255u),float((bits>>8u)&255u),float((bits>>16u)&255u),float(bits>>24u))/255.0;')
 return source
class Host(base.Host):
 def program(self,sources):
  sources=dict(sources);src=sources['shader.frag']
  # Alpha fallback remains resolution-specific NEAREST, no new 8x8 fetch.
  if self.arm!='alpha_fallback':src=transform(src,self.mode,self.diagnostic)
  sources['shader.frag']=src;self.last_shader=src
  return super().program(sources)
 def capture(self,size,kind,arm,mode,diagnostic=None):
  self.arm=arm;self.mode=mode;self.diagnostic=diagnostic
  row=super().draw(size,kind,arm)
  row['fragment_sha256']=hashlib.sha256(self.last_shader.encode()).hexdigest();row['mode']=mode
  return row

def decode(pixels):
 if len(pixels)%4:raise ValueError('bad pixel length')
 values=list(struct.unpack('<'+'f'*(len(pixels)//4),bytes(pixels)))
 if not all(math.isfinite(v) for v in values):raise ValueError('nonfinite probe')
 return values

def cpu_values(size,kind):
 data=base.atlas(kind);samples=[];coverage=[]
 for y in range(size):
  for x in range(size):
   rgb=base.sample(data,(x+.5)/size,(y+.5)/size);samples.append(rgb)
   distance=sorted(rgb)[1] if kind=='msdf' else rgb[0]
   t=max(0,min(1,(distance-(.5-1/size))/(2/size)));coverage.append(t*t*(3-2*t))
 return samples,coverage

def select(rows,max_explicit_fetches=1):
 if type(max_explicit_fetches) is not int or not 0<=max_explicit_fetches<=4:raise ValueError('fetch budget must be integer 0..4')
 decisions=[]
 for n in (16,32):
  for kind in ('sdf','msdf'):
   def find(mode,arm):
    matches=[r for r in rows if r['size']==n and r['kind']==kind and r['mode']==mode and r['arm']==arm]
    if len(matches)!=1:raise ValueError('missing or duplicate route evidence')
    row=matches[0];gold=base.golden(n,kind);pixels=row['pixels']
    if len(pixels)!=len(gold) or any(type(v)is not int or not 0<=v<=255 for v in pixels):raise ValueError('invalid pixel evidence')
    return max(abs(a-b) for a,b in zip(pixels,gold))<=3
   hardware=find('highp_hardware','correct');four=find('highp_four_tap','correct');fallback=find('original','alpha_fallback')
   route='highp_hardware' if hardware and max_explicit_fetches>=1 else 'highp_four_tap' if four and max_explicit_fetches>=4 else 'alpha_fallback' if fallback and max_explicit_fetches>=1 else 'UNAVAILABLE'
   decisions.append(dict(size=n,kind=kind,selected=route,max_explicit_fetches=max_explicit_fetches,selected_shader_texture_instructions=4 if route=='highp_four_tap' else 1 if route!='UNAVAILABLE' else 0,quality_only=True,performance='NOT_MEASURED',four_tap_budget_allowed=max_explicit_fetches>=4))
 return decisions

def run(config,output,max_explicit_fetches=1):
 h=Host(config);rows=[];probes=[]
 try:
  for mode in MODES:
   for n in (16,32):
    for kind in ('sdf','msdf'):
     for arm in ('correct','alpha_fallback','wrong_threshold','wrong_outline','wrong_channel'):
      if arm=='wrong_channel' and kind!='msdf':continue
      rows.append(h.capture(n,kind,arm,mode))
     captures=[h.capture(n,kind,'correct',mode,i) for i in range(4)]
     values=[decode(c['pixels']) for c in captures];cpu,coverage=cpu_values(n,kind)
     sample_error=max(abs(values[c][j]-cpu[j][c]) for j in range(n*n) for c in range(3));errors=[abs(values[3][j]-coverage[j]) for j in range(n*n)];peak=max(range(n*n),key=lambda j:errors[j])
     probes.append(dict(mode=mode,size=n,kind=kind,sample_max_abs_error=sample_error,coverage_max_abs_error=max(errors),worst_coverage_xy=[peak%n,peak//n],worst_cpu_sample=cpu[peak],worst_actual_sample=[values[c][peak] for c in range(3)],worst_cpu_coverage=coverage[peak],worst_actual_coverage=values[3][peak],packed_float_captures=[dict(fragment_sha256=c['fragment_sha256'],pixels=c['pixels']) for c in captures]))
 finally:h.close()
 improved=[r for r in rows if r['mode']=='highp_four_tap']
 passed=all(r['quality']==('FAIL' if r['arm'].startswith('wrong_') else 'PASS') for r in improved)
 # Instrumented float outputs must agree with ordinary UNORM coverage to 1 byte.
 consistent=True
 for probe in probes:
  ordinary=next(r for r in rows if r['mode']==probe['mode'] and r['size']==probe['size'] and r['kind']==probe['kind'] and r['arm']=='correct')
  floats=decode(probe['packed_float_captures'][3]['pixels']);error=max(abs(base.quant(v)-ordinary['pixels'][j*4]) for j,v in enumerate(floats));probe['instrumentation_byte_max_error']=error;consistent &= error<=1
 decisions=select(rows,max_explicit_fetches)
 result=dict(decisions=decisions,status='HOST_PASS' if passed and consistent and all(x['selected']!='UNAVAILABLE' for x in decisions) else 'FAIL',draws=len(rows)+4*len(probes),pixel_budget=3,rows=rows,probes=probes,performance='NOT_MEASURED',physical_device='NOT_RUN',source_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),original_source_sha256=hashlib.sha256((HERE/'run.py').read_bytes()).hexdigest(),scope='Highp four explicit texelFetch instructions versus hardware sample on a fixed authored 8x8 atlas; diagnostic float packing is not GPU timing.')
 out=Path(output);out.parent.mkdir(parents=True,exist_ok=True);raw=(json.dumps(result,indent=2)+'\n').encode()
 if out.suffix=='.gz':
  compressed=gzip.compress(raw,compresslevel=9,mtime=0);out.write_bytes(compressed[:9]+b'\xff'+compressed[10:])
 else:out.write_bytes(raw)
 return result
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--config',type=Path,required=True);p.add_argument('--output',required=True);p.add_argument('--max-explicit-fetches',type=int,default=1);a=p.parse_args();r=run(json.loads(a.config.read_text()),a.output,a.max_explicit_fetches);print(r['status']);raise SystemExit(r['status']!='HOST_PASS')
