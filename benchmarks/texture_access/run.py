#!/usr/bin/env python3
"""Eight actual texture sampling controls; compression/streaming remain separate gates."""
import argparse,hashlib,importlib.util,json,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'benchmarks/shader_ab'))
spec=importlib.util.spec_from_file_location('v109_shader_ab',ROOT/'benchmarks/shader_ab/run.py')
ab=importlib.util.module_from_spec(spec);spec.loader.exec_module(ab)
ExperimentHost=ab.ExperimentHost;quality=ab.quality
SOURCE='#version 300 es\nprecision highp float;\nuniform sampler2D tex;\nlayout(location=0) out vec4 color;\nvoid main(){color=texture(tex,COORD);}'
def cases():
 tex=dict(size=2,filter=0x2600,pixels=[255,0,0,255,0,255,0,255,0,0,255,255,255,255,255,255])
 return [dict(id=n,a=SOURCE.replace('COORD',a),b=SOURCE.replace('COORD',b),texture=tex,expected=expected) for n,a,b,expected in [
 ('coordinate-hoist','gl_FragCoord.xy/4.0','gl_FragCoord.xy*0.25','PASS'),
 ('scalar-vector','vec2(gl_FragCoord.x/4.0,gl_FragCoord.y/4.0)','gl_FragCoord.xy/4.0','PASS'),
 ('clamp-safe','gl_FragCoord.xy/4.0','clamp(gl_FragCoord.xy/4.0,0.0,1.0)','PASS'),
 ('nearest-texel-center','gl_FragCoord.xy/4.0','(floor(gl_FragCoord.xy/2.0)+0.5)/2.0','PASS'),
 ('transpose-negative','gl_FragCoord.xy/4.0','gl_FragCoord.yx/4.0','FAIL'),
 ('mirror-negative','gl_FragCoord.xy/4.0','1.0-gl_FragCoord.xy/4.0','FAIL'),
 ('atlas-offset-negative','gl_FragCoord.xy/4.0','gl_FragCoord.xy/4.0+vec2(0.5,0.0)','FAIL'),
 ('resolution-loss-negative','gl_FragCoord.xy/4.0','vec2(0.25)','FAIL')]]
def run(config,output):
 h=ExperimentHost(config);rows=[]
 try:
  for c in cases():
   draws=[h.draw(c['id'],c[a],texture=c['texture']) for a in ('a','b')]
   rows.append(dict(id=c['id'],observed=quality(*draws),expected=c['expected'],draws=draws,source_sha256={a:hashlib.sha256(c[a].encode()).hexdigest() for a in ('a','b')},performance_status='NOT_MEASURED',dram_bytes=None,cpu_transcode_ms=None,resident_memory_bytes=None,upload_stall_ms=None))
  result=dict(status='HOST_PASS' if all(r['observed']==r['expected'] for r in rows) else 'FAIL',metadata=h.metadata,experiments=rows,scope='RGBA8 nearest-sampled 2x2 texture / 4x4 framebuffer; not ASTC/ETC2/PBO/aniso/mip performance',hardware='BLOCKED_BY_HARDWARE')
 finally:h.close()
 Path(output).write_text(json.dumps(result,indent=2)+'\n');return result
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--config',required=True);p.add_argument('--output',required=True);a=p.parse_args();r=run(json.loads(Path(a.config).read_text()),a.output);print(r['status']);raise SystemExit(r['status']!='HOST_PASS')
