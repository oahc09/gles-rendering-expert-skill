#!/usr/bin/env python3
"""Official libktx UASTC transcode + strict container + real GLES decode/readback."""
import argparse,ctypes as C,hashlib,json,subprocess,tempfile,time
from pathlib import Path
import mechanisms as m
from ktx2_container import parse
from quality_gate import evaluate
from etc2_cpu_oracle import decode_block
ROOT=Path(__file__).resolve().parents[2]
class PayloadHost(m.TextureHost):
 def fn(self,name,restype,args,*extra):
  original=super().fn(name,restype,args,*extra)
  if name!='glTexImage2D' or not getattr(self,'payload',None):return original
  def upload(*unused):
   p=self.payload;raw=(C.c_ubyte*len(p['payload']))(*p['payload'])
   if p['mode']=='rgba':original(0xde1,0,0x8058,p['width'],p['height'],0,0x1908,0x1401,raw)
   else:super(PayloadHost,self).fn('glCompressedTexImage2D',None,[m.U,m.I,m.U,m.I,m.I,m.I,m.I,m.P])(0xde1,0,0x9278 if p['mode']=='etc2' else 0x93b0,p['width'],p['height'],0,len(raw),raw)
  return upload

def run(config,ktx,output,pattern="smooth"):
 rows=[];host=PayloadHost(config)
 try:
  if decode_block(bytes([255]+[0]*15),ktx)!=[2,2,2,255]*16:raise RuntimeError('ETC2 constant-block CPU oracle failed')
  with tempfile.TemporaryDirectory(prefix='gles-ktx109-') as tmp:
   tmp=Path(tmp);binary=tmp/'transcode'
   subprocess.run(['c++','-std=c++17','-I'+str(ktx/'include'),str(ROOT/'examples/texture_pipeline/transcode.cpp'),'-L'+str(ktx/'lib'),'-Wl,-rpath,'+str(ktx/'lib'),'-lktx','-o',str(binary)],check=True,capture_output=True)
   step=8 if pattern=="smooth" else 64
   rgb=bytes(v for y in range(4) for x in range(4) for v in (x*step,y*step,(x+y)*(step//2)));golden=[v for i in range(16) for v in list(rgb[i*3:i*3+3])+[255]]
   ppm=tmp/'original.ppm';ppm.write_bytes(b'P6\n4 4\n255\n'+rgb)
   source=tmp/'source.ktx2'
   subprocess.run([str(ktx/'bin/toktx'),'--t2','--encode','uastc','--threads','1','--assign_oetf','linear',str(source),str(ppm)],check=True,capture_output=True)
   for mode in ['rgba','etc2','astc']:
    if mode=='astc' and not any(x in host.metadata['extensions'] for x in ['GL_KHR_texture_compression_astc_ldr','GL_KHR_texture_compression_astc_hdr']):
     rows.append({'id':mode,'status':'NOT_RUN','reason':'ASTC capability absent'});continue
    start=time.perf_counter_ns();subprocess.run([str(binary),str(source),mode,str(tmp/mode)],check=True,capture_output=True);elapsed=(time.perf_counter_ns()-start)/1e6
    data=(tmp/(mode+'.ktx2')).read_bytes();host.payload=parse(data)
    c={'id':mode,'mode':'direct','source':m.source('texture(tex,gl_FragCoord.xy/4.0)'),'golden':golden,'tolerance':32}
    row=host.execute(c);row['expected']='PASS' if pattern=='smooth' else 'FAIL';row['payload_bytes']=len(host.payload['payload']);row.pop('logical_texture_bytes',None)
    row.update(container_sha256=hashlib.sha256(data).hexdigest(),source_pixels_sha256=hashlib.sha256(rgb).hexdigest(),cpu_process_load_and_transcode_ms=elapsed,quality_budget=32,quality_scope='4x4 original gradient only, lossy tolerance fixed before test',status='EXECUTED',decoded_unique_colors=len({tuple(row['pixels'][i:i+4]) for i in range(0,64,4)}))
    decoded=tmp/(mode+'.rgba')
    if decoded.exists() or mode=='etc2':
     cpu=decode_block(host.payload['payload'],ktx) if mode=='etc2' else list(decoded.read_bytes())
     if len(cpu)!=64:raise RuntimeError('CPU decoded payload size mismatch')
     flipped=[v for y in reversed(range(4)) for v in golden[y*16:y*16+16]]
     row['cpu_decoded_pixels']=cpu
     row['gpu_vs_cpu_decode_max_error']=max(abs(a-b) for a,b in zip(cpu,row['pixels']))
     row['cpu_vs_authored_max_error']=max(abs(a-b) for a,b in zip(cpu,golden))
     row['cpu_vs_vertical_flip_max_error']=max(abs(a-b) for a,b in zip(cpu,flipped))
     if row['gpu_vs_cpu_decode_max_error']>1:raise RuntimeError('GLES decode differs from independent CPU decode')
    else:row['independent_cpu_decode']='NOT_AVAILABLE_FOR_ETC2'
    rows.append(row)
   mutations=[];data=(tmp/'rgba.ktx2').read_bytes()
   for name,offset,value in [('magic',0,0),('dimensions',20,0),('supercompression',44,1),('offset-overlap',80,0),('dfd-mismatch',int.from_bytes(data[48:52],'little')+12,162)]:
    b=bytearray(data);b[offset]=value
    try:parse(bytes(b));rejected=False
    except ValueError:rejected=True
    mutations.append({'case':name,'rejected':rejected})
   decision_gate=evaluate(rows,golden,pattern)
   result={'decision_gate':decision_gate,'etc2_cpu_constant_oracle':'PASS','status':'HOST_PASS' if decision_gate['harness_status']=='HOST_PASS' and all(x['rejected'] for x in mutations) else 'FAIL','experiments':rows,'negative_containers':mutations,'source_pattern':pattern,'expected_quality':'PASS' if pattern=='smooth' else 'FAIL','source_golden_rgba':golden,'performance_status':'NOT_MEASURED','hardware':'BLOCKED_BY_HARDWARE','scope':'Original 4x4 gradient encoded by official UASTC, actual libktx conversion, compressed multicolor GLES readback. CPU process elapsed includes startup and output I/O, not isolated transcoder or GPU performance.'}
 finally:host.close()
 Path(output).write_text(json.dumps(result,indent=2)+'\n');return result
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--config',required=True);p.add_argument('--ktx-root',type=Path,required=True);p.add_argument('--output',required=True);p.add_argument('--pattern',choices=['smooth','steep'],default='smooth');a=p.parse_args();r=run(json.loads(Path(a.config).read_text()),a.ktx_root,a.output,a.pattern);print(r['status']);raise SystemExit(r['status']!='HOST_PASS')
