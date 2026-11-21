#!/usr/bin/env python3
"""Filtered application-only KHR/core debug output; no driver log harvesting."""
import argparse,ctypes as C,hashlib,importlib.util,json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[3]
s=importlib.util.spec_from_file_location('debug_host',ROOT/'benchmarks/differential/run.py');d=importlib.util.module_from_spec(s);s.loader.exec_module(d)
U=d.U;I=d.I;P=d.P;B=C.c_ubyte
APP=0x824a;OTHER=0x8251;LOW=0x9148;HIGH=0x9146;NOTE=0x826b;DONT=0x1100
MESSAGES={901:b'finite-start',902:b'finite-blocked-id',903:b'finite-high-blocked',904:b'finite-low-allowed',905:b'finite-group',906:b'finite-low-in-group',907:b'finite-low-restored',908:b'finite-after-unregister'}
SIGNATURES={'glDebugMessageCallback':[P,P],'glDebugMessageControl':[U,U,U,I,P,B],'glDebugMessageInsert':[U,U,U,U,I,C.c_char_p],'glPushDebugGroup':[U,U,I,C.c_char_p],'glPopDebugGroup':[],'glObjectLabel':[U,U,I,C.c_char_p],'glGetObjectLabel':[U,U,I,P,P],'glGetPointerv':[U,P]}
def route(version,extensions,disabled=False):
 if disabled:return None
 if version>=(3,2):return 'core'
 if 'GL_KHR_debug' in extensions:return 'KHR'
 return None

def run(config,disabled=False):
 h=d.Host(config);buffer=U();callback=None;funcs={};registered=False;records=[]
 report={'schema_version':1,'status':'FAIL','source_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),'execution_class':'SOFTWARE_HOST','physical_device':'NOT_RUN','performance':'NOT_MEASURED','driver_messages_recorded':False,'force_disabled':disabled}
 def check():
  e=h.error()
  if e:raise RuntimeError('UNEXPECTED_GL_ERROR_'+str(e))
 try:
  major=I();minor=I();h.fn('glGetIntegerv',None,[U,P])(0x821b,C.byref(major));h.fn('glGetIntegerv',None,[U,P])(0x821c,C.byref(minor));selected=route((major.value,minor.value),h.metadata['extensions'],disabled);report.update(route=selected,api_version=[major.value,minor.value],KHR_advertised='GL_KHR_debug' in h.metadata['extensions'])
  if selected is None:
   row=h.execute({'id':'safe-no-debug','kind':'fbo_pixels','color':[1,0,0,1]});report['fallback']={'pixels':row['pixels'],'gl_error':row['harness_gl_error'],'debug_functions_called':0};report['status']='SAFE_FALLBACK_PASS' if row['pixels']==[255,0,0,255]*16 and row['harness_gl_error']==0 else 'FAIL';return report
  suffix='' if selected=='core' else 'KHR'
  for name,args in SIGNATURES.items():
   ptr=h.fn('eglGetProcAddress',P,[C.c_char_p],True)((name+suffix).encode())
   if not ptr:raise RuntimeError('MISSING_ROUTE_ENTRYPOINT')
   funcs[name]=C.CFUNCTYPE(None,*args)(ptr)
  report['entrypoints']=[name+suffix for name in SIGNATURES]
  control=funcs['glDebugMessageControl'];insert=funcs['glDebugMessageInsert'];cb=funcs['glDebugMessageCallback']
  # Disable all categories BEFORE callback or debug output is enabled.
  h.fn('glDisable',None,[U])(0x92e0);control(DONT,DONT,DONT,0,None,0)
  signature=C.CFUNCTYPE(None,U,U,U,U,I,P,P)
  token=I(713)
  @signature
  def sink(source,typ,ident,severity,length,message,user):
   # Inspect pointer only for known application IDs/length; never call GL here.
   expected=MESSAGES.get(ident)
   if source!=APP or expected is None or length!=len(expected) or not message:return
   content=C.string_at(message,length)
   if content!=expected:return
   records.append({'source':source,'type':typ,'id':ident,'severity':severity,'message':content.decode('ascii'),'user_matches':user==C.addressof(token)})
  callback=sink;cb(C.cast(callback,P),C.byref(token));registered=True
  function=P();param=P();funcs['glGetPointerv'](0x8244,C.byref(function));funcs['glGetPointerv'](0x8245,C.byref(param));report['callback_registration_matches']=function.value==C.cast(callback,P).value and param.value==C.addressof(token)
  h.fn('glEnable',None,[U])(0x8242);h.fn('glEnable',None,[U])(0x92e0);control(APP,DONT,DONT,0,None,1);check()
  def emit(ident,severity=LOW):insert(APP,OTHER,ident,severity,len(MESSAGES[ident]),MESSAGES[ident]);check()
  emit(901);report['synchronous_return_observed']=any(x['id']==901 for x in records)
  ids=(U*1)(902);control(APP,OTHER,DONT,1,ids,0);emit(902)
  control(APP,OTHER,HIGH,0,None,0);emit(903,HIGH);emit(904)
  before=I();inside=I();after=I();h.fn('glGetIntegerv',None,[U,P])(0x826d,C.byref(before))
  funcs['glPushDebugGroup'](APP,905,len(MESSAGES[905]),MESSAGES[905]);h.fn('glGetIntegerv',None,[U,P])(0x826d,C.byref(inside));control(APP,OTHER,LOW,0,None,0);emit(906);funcs['glPopDebugGroup']();h.fn('glGetIntegerv',None,[U,P])(0x826d,C.byref(after));emit(907);report['group_depth']=[before.value,inside.value,after.value]
  h.fn('glGenBuffers',None,[I,P])(1,C.byref(buffer));h.fn('glBindBuffer',None,[U,U])(0x8892,buffer);label=b'finite-owned-buffer';funcs['glObjectLabel'](0x82e0,buffer,len(label),label)
  full=C.create_string_buffer(64);truncated=C.create_string_buffer(6);length=I();shortlen=I();funcs['glGetObjectLabel'](0x82e0,buffer,64,C.byref(length),full);funcs['glGetObjectLabel'](0x82e0,buffer,6,C.byref(shortlen),truncated);check();report['label']={'full':full.value.decode('ascii'),'length':length.value,'truncated':truncated.value.decode('ascii'),'truncated_length':shortlen.value,'null_terminated':truncated.raw[-1]==0}
  negatives=[]
  for name,fn,args,expected in [('control-id-wildcard-source',control,(DONT,OTHER,DONT,1,ids,1),0x502),('insert-api-source',insert,(0x8246,OTHER,901,LOW,len(MESSAGES[901]),MESSAGES[901]),0x500),('pop-default-group',funcs['glPopDebugGroup'],(),0x504),('label-invalid-identifier',funcs['glObjectLabel'],(0xdead,buffer,len(label),label),0x500),('query-negative-buffer-size',funcs['glGetObjectLabel'],(0x82e0,buffer,-1,C.byref(length),full),0x501)]:
   fn(*args);negatives.append({'id':name,'expected_error':expected,'gl_error':h.error()})
  report['negative_cases']=negatives
  h.fn('glFinish',None,[])();cb(None,None);registered=False;funcs['glGetPointerv'](0x8244,C.byref(function));funcs['glGetPointerv'](0x8245,C.byref(param));count=len(records);emit(908);report['callback_unregister']={'pointer_null':function.value is None,'user_null':param.value is None,'no_callback_after_unregister':len(records)==count};h.fn('glDisable',None,[U])(0x92e0);control(DONT,DONT,DONT,0,None,0);check()
  report['application_messages']=records
  expected=[(901,OTHER,LOW),(904,OTHER,LOW),(905,0x8269,NOTE),(905,0x826a,NOTE),(907,OTHER,LOW)]
  actual=[(x['id'],x['type'],x['severity']) for x in records]
  ok=actual==expected and all(x['user_matches'] for x in records) and all(x['gl_error']==x['expected_error'] for x in negatives) and report['group_depth']==[1,2,1] and full.value==label and report['label']['length']==len(label) and report['label']['null_terminated'] and shortlen.value==5 and truncated.value==label[:5] and report['callback_registration_matches'] and report['synchronous_return_observed'] and all(report['callback_unregister'].values())
  report['status']='HOST_PASS' if ok else 'FAIL'
 finally:
  # Keep ctypes callback + user token strongly referenced until explicit unregister.
  if registered:funcs['glDebugMessageCallback'](None,None)
  if funcs:h.fn('glDisable',None,[U])(0x92e0)
  if buffer.value:h.fn('glBindBuffer',None,[U,U])(0x8892,0);h.fn('glDeleteBuffers',None,[I,P])(1,C.byref(buffer))
  h.close()
 return report
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--config',type=Path,required=True);p.add_argument('--output',type=Path,required=True);p.add_argument('--disable-debug',action='store_true');a=p.parse_args()
 try:r=run(json.loads(a.config.read_text()),a.disable_debug)
 except Exception as e:r={'status':'FAIL','diagnostic':str(e) if str(e).startswith(('UNEXPECTED_GL_ERROR','MISSING_ROUTE')) else type(e).__name__}
 a.output.parent.mkdir(parents=True,exist_ok=True);a.output.write_text(json.dumps(r,indent=2)+'\n');raise SystemExit(0 if r['status'] in ('HOST_PASS','SAFE_FALLBACK_PASS') else 1)
