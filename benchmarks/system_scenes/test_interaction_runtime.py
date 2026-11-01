#!/usr/bin/env python3
"""Real browser range-input -> HTTP -> native GLES -> displayed PNG smoke test."""
import os
import hashlib
import json
from pathlib import Path
import socket
import subprocess
import sys
import tempfile
import time
import urllib.request
ROOT=Path(__file__).resolve().parents[2]
def main():
 from playwright.sync_api import sync_playwright
 output=Path('/tmp/gles-system-interaction');output.mkdir(exist_ok=True)
 with socket.socket() as sock:sock.bind(('127.0.0.1',0));port=sock.getsockname()[1]
 command=[sys.executable,str(Path(__file__).parent/'interactive.py'),'--port',str(port)]
 server=subprocess.Popen(command,stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True)
 try:
  url=f'http://127.0.0.1:{port}/'
  for _ in range(100):
   if server.poll() is not None:raise RuntimeError('Local renderer server exited')
   try:urllib.request.urlopen(url,timeout=.5);break
   except OSError:time.sleep(.05)
  else:raise RuntimeError('Local renderer startup timeout')
  errors=[]
  with sync_playwright() as p:
   known=Path('/workspace/scratch/62d43a81bbde/browser-runtime/run-webkit-local-deps.sh')
   browser=p.webkit.launch(executable_path=os.environ.get('GLES_WEBKIT_PATH') or (str(known) if known.exists() else None),headless=True)
   page=browser.new_page(viewport={'width':900,'height':800});page.on('pageerror',lambda e:errors.append(str(e)));page.goto(url);page.wait_for_function("document.getElementById('frame').naturalWidth===96 && document.getElementById('status').textContent==='Rendered 0'")
   before=page.locator('#frame').screenshot(path=str(output/'before.png'))
   page.locator('#touch').focus();page.locator('#touch').press('End');page.wait_for_function("document.getElementById('status').textContent==='Rendered 1'");page.wait_for_function("document.getElementById('frame').complete && document.getElementById('frame').naturalWidth===96")
   after=page.locator('#frame').screenshot(path=str(output/'after.png'));version=browser.version;browser.close()
  report={'status':'PASS' if not errors and before!=after else 'FAIL','scope':'actual WPE WebKit UI event to native Mesa GLES rendering; not Android device UI','browser':version,'screenshots':'INTERNAL_ONLY_TMP_NOT_SOURCE_OR_LIBRARY','server_command':command,'before_sha256':hashlib.sha256(before).hexdigest(),'after_sha256':hashlib.sha256(after).hexdigest(),'page_errors':errors,'server_source_sha256':hashlib.sha256((Path(__file__).parent/'interactive.py').read_bytes()).hexdigest(),'harness_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),'native_binary_sha256':hashlib.sha256(Path('/tmp/gles-system-scenes/effects').read_bytes()).hexdigest()}
  (output/'report.json').write_text(json.dumps(report,indent=2)+'\n');print(report['status']);return report['status']!='PASS'
 finally:
  server.terminate();server.communicate(timeout=5)
if __name__=='__main__':sys.exit(main())
