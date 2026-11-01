#!/usr/bin/env python3
"""Local interactive slider -> actual native GLES -> PNG. No remote service."""
import argparse
from http.server import BaseHTTPRequestHandler,HTTPServer
import json
import math
import os
from pathlib import Path
import struct
import subprocess
import tempfile
import zlib
import sys
sys.path.append(str(Path(__file__).resolve().parents[1]/'visual_quality'))
from compare import read_ppm
HTML=b'''<!doctype html><meta charset="utf-8"><title>GLES system interaction</title><style>body{background:#142532;color:#eee;font:18px sans-serif;max-width:700px;margin:30px auto}img{width:480px;image-rendering:pixelated}input{width:80%}</style><h1>GLES native interaction</h1><p>Move the glass center: each input renders native GLES offscreen, not a prerecorded animation.</p><input id="touch" type="range" min="-1" max="1" step=".05" value="0"><p id="status"></p><img id="frame"><script>const touch=document.getElementById("touch"),frame=document.getElementById("frame"),label=document.getElementById("status");let pending=false;async function draw(){if(pending)return;pending=true;try{const r=await fetch('/render',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({touch:Number(touch.value),scene:'glass'})});if(!r.ok)throw Error(await r.text());const b=await r.blob();const old=frame.src;frame.src=URL.createObjectURL(b);if(old)URL.revokeObjectURL(old);label.textContent='Rendered '+touch.value;}catch(e){label.textContent=e;}finally{pending=false;}}touch.oninput=draw;draw();</script>'''
def png(path):
 w,h,data=read_ppm(path)
 def chunk(tag,data):return struct.pack('>I',len(data))+tag+data+struct.pack('>I',zlib.crc32(tag+data)&0xffffffff)
 raw=b''.join(b'\0'+data[y*w*3:(y+1)*w*3] for y in range(h))
 return b'\x89PNG\r\n\x1a\n'+chunk(b'IHDR',struct.pack('>IIBBBBB',w,h,8,2,0,0,0))+chunk(b'IDAT',zlib.compress(raw))+chunk(b'IEND',b'')
def render(binary,body):
 if not isinstance(body,dict) or set(body)!={'scene','touch'}:raise ValueError('Only scene and touch accepted')
 value=body['touch'];scene=body['scene']
 if type(value) not in (int,float) or not math.isfinite(value) or not -1<=value<=1:raise ValueError('touch must be finite [-1,1]')
 if scene not in ('glass','sand','particle','shadowwater','forwardplus'):raise ValueError('scene not allowlisted')
 with tempfile.TemporaryDirectory(prefix='gles-interaction-') as tmp:
  path=Path(tmp)/'image.ppm';r=subprocess.run([str(binary),scene,str(path),'baseline',str(value)],capture_output=True,text=True,timeout=30)
  if r.returncode:raise RuntimeError(r.stderr)
  return png(path)
def serve(binary,port):
 class Handler(BaseHTTPRequestHandler):
  def do_GET(self):
   if self.path!='/':self.send_error(404);return
   self.send_response(200);self.send_header('Content-Type','text/html; charset=utf-8');self.send_header('Content-Length',str(len(HTML)));self.end_headers();self.wfile.write(HTML)
  def do_POST(self):
   if self.path!='/render':self.send_error(404);return
   try:
    length=int(self.headers.get('Content-Length','0'))
    if not 1<=length<=1024:raise ValueError('Body size')
    result=render(binary,json.loads(self.rfile.read(length)))
   except (ValueError,RuntimeError,subprocess.TimeoutExpired) as error:self.send_error(400,str(error));return
   self.send_response(200);self.send_header('Content-Type','image/png');self.send_header('Content-Length',str(len(result)));self.end_headers();self.wfile.write(result)
 HTTPServer(('127.0.0.1',port),Handler).serve_forever()
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--binary',type=Path,default=Path('/tmp/gles-system-scenes/effects'));p.add_argument('--port',type=int,default=8766);a=p.parse_args();serve(a.binary,a.port)
