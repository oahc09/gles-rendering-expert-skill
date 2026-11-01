#!/usr/bin/env python3
"""Actual HTTP input -> native GLES image; explicitly not a browser UI test."""
import hashlib,json,os,socket,subprocess,sys,time,urllib.request,urllib.error
from pathlib import Path
HERE=Path(__file__).resolve().parent
with socket.socket() as sock:sock.bind(('127.0.0.1',0));port=sock.getsockname()[1]
server=subprocess.Popen([sys.executable,str(HERE/'interactive.py'),'--port',str(port)],stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True)
try:
 url=f'http://127.0.0.1:{port}'
 for _ in range(100):
  try:urllib.request.urlopen(url,timeout=.5);break
  except OSError:
   if server.poll() is not None:raise RuntimeError('server exited')
   time.sleep(.05)
 else:raise RuntimeError('server startup timeout')
 rows=[]
 for value in (0,1,-1):
  req=urllib.request.Request(url+'/render',data=json.dumps({'scene':'glass','touch':value}).encode(),headers={'Content-Type':'application/json'},method='POST')
  with urllib.request.urlopen(req,timeout=30) as response:data=response.read();status=response.status
  if not data.startswith(b'\x89PNG\r\n\x1a\n'):raise RuntimeError('not PNG')
  rows.append({'touch':value,'http_status':status,'png_sha256':hashlib.sha256(data).hexdigest(),'bytes':len(data)})
 bad=urllib.request.Request(url+'/render',data=b'{"scene":"glass","touch":5}',headers={'Content-Type':'application/json'},method='POST')
 try:urllib.request.urlopen(bad);raise RuntimeError('bad input accepted')
 except urllib.error.HTTPError as e:rejected=e.code==400
 report={'status':'PASS' if rejected and len({r['png_sha256'] for r in rows})==3 else 'FAIL','scope':'actual localhost HTTP input to native Mesa GLES renders','browser_ui':'SEPARATE_EVIDENCE_browser-validation.json','browser_note':'Chromium normal launch failed IPC socket; reviewed escalation failed environment initialization before command execution; separate normal WPE WebKit test uses an existing authorized current-environment launcher','invalid_input_rejected':rejected,'captures':rows,'binary_sha256':hashlib.sha256(Path('/tmp/gles-system-scenes/effects').read_bytes()).hexdigest(),'server_source_sha256':hashlib.sha256((HERE/'interactive.py').read_bytes()).hexdigest()}
 (HERE/'interaction-validation.json').write_text(json.dumps(report,indent=2)+'\n');print(report['status']);sys.exit(report['status']!='PASS')
finally:server.terminate();server.communicate(timeout=5)
