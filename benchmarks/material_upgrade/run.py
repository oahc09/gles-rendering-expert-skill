#!/usr/bin/env python3
"""Compile real GLES 3.0 scene and compare readback with CPU analytic golden."""
import argparse,os,subprocess,json,hashlib,sys,tempfile
from pathlib import Path
from model import ROOT,rgb
sys.path.insert(0,str(ROOT/'benchmarks/pipeline'))
from runtime import quantize
p=argparse.ArgumentParser();p.add_argument('--output',default='/tmp/gles-film-report');a=p.parse_args();out=Path(a.output);out.mkdir(parents=True,exist_ok=True)
source=ROOT/'examples/material_upgrade/film.frag';binary=out/'film'
env=dict(os.environ,EGL_PLATFORM='surfaceless',LIBGL_ALWAYS_SOFTWARE='1',MESA_SHADER_CACHE_DISABLE='true',LP_NUM_THREADS='2')
include=os.environ.get('GLES_SDK_ROOT','');flags=['-I'+include+'/include'] if include else []
lib=os.environ.get('GLES_LIBRARY_DIR');flags+=['-L'+lib,'-Wl,-rpath,'+lib] if lib else []
report={'status':'UNKNOWN','scope':'software GLES only; no hardware or perceptual-equivalence claim','captures':[]}
try:
 subprocess.run(['c++','-std=c++17','-Wall','-Wextra','-Werror',*flags,str(ROOT/'examples/material_upgrade/film.cpp'),'-l:libEGL.so.1','-l:libGLESv2.so.2','-o',str(binary)],check=True,capture_output=True,timeout=60)
 for precision,tolerance in [('highp',1),('mediump',3)]:
  shader=out/(precision+'.frag');shader.write_text(source.read_text().replace('precision highp','precision '+precision));ppm=out/(precision+'.ppm')
  r=subprocess.run([str(binary),str(shader),str(ppm)],check=True,text=True,capture_output=True,timeout=30,env=env)
  header,data=ppm.read_bytes().split(b'\n255\n',1);assert header==b'P6\n64 64' and len(data)==64*64*3
  golden=bytes(quantize(c) for y in range(63,-1,-1) for x in range(64) for c in rgb(1200*(x+.5)/64,.05+.95*(y+.5)/64))
  (out/'cpu-golden.ppm').write_bytes(b'P6\n64 64\n255\n'+golden)
  error=max(abs(x-y) for x,y in zip(data,golden));report['captures'].append({'precision':precision,'renderer':r.stdout.strip(),'max_absolute_code_error':error,'tolerance':tolerance,'pass':error<=tolerance,'sha256':hashlib.sha256(ppm.read_bytes()).hexdigest()})
 report['status']='PASS' if all(c['pass'] for c in report['captures']) else 'FAIL'
except (subprocess.SubprocessError,OSError,AssertionError) as e:report['error']=str(e)+str(getattr(e,'stderr',''))
report['sources']={str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest() for p in [source,ROOT/'examples/material_upgrade/film.cpp',ROOT/'benchmarks/material_upgrade/model.py',Path(__file__)]}
(out/'report.json').write_text(json.dumps(report,indent=2));(out/'report.md').write_text('# Thin-film host validation\n\n'+report['status']+'\n\n'+json.dumps(report,indent=2));print(json.dumps(report,indent=2));sys.exit(0 if report['status']=='PASS' else 1)
