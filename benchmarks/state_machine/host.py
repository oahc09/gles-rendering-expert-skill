#!/usr/bin/env python3
"""Small bounded real GLES3/EGL probes. Run in a timeout-isolated subprocess."""
import argparse
import ctypes as C
import json
import os
from pathlib import Path

U=C.c_uint; I=C.c_int; P=C.c_void_p

def run(library):
    os.environ.setdefault('EGL_PLATFORM','surfaceless');os.environ.setdefault('LIBGL_ALWAYS_SOFTWARE','1')
    egl=C.CDLL('libEGL.so.1');gl=C.CDLL(library)
    def fn(lib,name,restype,args):
        f=getattr(lib,name);f.restype=restype;f.argtypes=args;return f
    getdisplay=fn(egl,'eglGetDisplay',P,[P]);initialize=fn(egl,'eglInitialize',U,[P,C.POINTER(I),C.POINTER(I)])
    choose=fn(egl,'eglChooseConfig',U,[P,C.POINTER(I),C.POINTER(P),I,C.POINTER(I)])
    create=fn(egl,'eglCreateContext',P,[P,P,P,C.POINTER(I)])
    surface=fn(egl,'eglCreatePbufferSurface',P,[P,P,C.POINTER(I)])
    current=fn(egl,'eglMakeCurrent',U,[P,P,P,P]);geterr=fn(egl,'eglGetError',I,[])
    destroy_surface=fn(egl,'eglDestroySurface',U,[P,P]);destroy_context=fn(egl,'eglDestroyContext',U,[P,P]);terminate=fn(egl,'eglTerminate',U,[P])
    getstring=fn(gl,'glGetString',C.c_char_p,[U]);error=fn(gl,'glGetError',U,[])
    proc=fn(egl,'eglGetProcAddress',P,[C.c_char_p]);rows=[];d=getdisplay(None);s=c=None
    def check(ok,label):
        if not ok: raise RuntimeError(label+' EGL error '+hex(geterr()))
    try:
        check(initialize(d,None,None),'initialize')
        cfg=P();count=I();attrs=(I*9)(0x3033,1,0x3040,0x40,0x3024,8,0x3023,8,0x3038)
        check(choose(d,attrs,C.byref(cfg),1,C.byref(count)) and count.value,'choose GLES3 config')
        c=create(d,cfg,None,(I*3)(0x3098,3,0x3038));check(c,'create context')
        s=surface(d,cfg,(I*5)(0x3057,4,0x3056,4,0x3038));check(s,'create surface');check(current(d,s,s,c),'make current')
        def test(label,name,args,types,expected=0):
            if error()!=0: raise RuntimeError('dirty GL error before '+label)
            fn(gl,name,None,types)(*args);actual=error()
            rows.append(dict(id='HOST-%03d'%(len(rows)+1),label=label,expected_error=expected,observed_error=actual,classification='EXPECTED_ERROR' if expected else 'PASS',status='PASS' if actual==expected else 'FAIL',evidence='HOST_REPRODUCED'))
        test('valid viewport','glViewport',[0,0,4,4],[I]*4)
        test('negative viewport width','glViewport',[0,0,-1,4],[I]*4,0x501)
        test('valid pack alignment','glPixelStorei',[0xd05,4],[U,I])
        test('invalid pack alignment','glPixelStorei',[0xd05,3],[U,I],0x501)
        test('invalid enable capability','glEnable',[0xdead],[U],0x500)
        test('negative scissor width','glScissor',[0,0,-1,4],[I]*4,0x501)
        test('valid clear','glClear',[0x4000],[U])
        test('invalid clear bit','glClear',[1],[U],0x501)
        for plural,binder,target in [('Buffers','glBindBuffer',0x8892),('Textures','glBindTexture',0xde1),('Framebuffers','glBindFramebuffer',0x8d40),('Renderbuffers','glBindRenderbuffer',0x8d41)]:
            value=U();fn(gl,'glGen'+plural,None,[I,C.POINTER(U)])(1,C.byref(value))
            try:
                test(plural+' bind',binder,[target,value.value],[U,U])
                test(plural+' invalid target',binder,[0xdead,value.value],[U,U],0x500)
                if plural=='Buffers':
                    test('VBO allocate bounded 64 bytes','glBufferData',[target,64,None,0x88e4],[U,C.c_ssize_t,P,U])
                    test('VBO negative allocation','glBufferData',[target,-1,None,0x88e4],[U,C.c_ssize_t,P,U],0x501)
                    test('VBO range overflow','glBufferSubData',[target,65,1,C.cast(C.create_string_buffer(b'a'),P)],[U,C.c_ssize_t,C.c_ssize_t,P],0x501)
                if plural=='Textures':
                    test('texture bounded storage','glTexStorage2D',[target,1,0x8058,4,4],[U,I,U,I,I])
                    test('immutable texture redefinition','glTexStorage2D',[target,1,0x8058,4,4],[U,I,U,I,I],0x502)
                if plural=='Framebuffers':
                    status=fn(gl,'glCheckFramebufferStatus',U,[U])(target)
                    rows.append(dict(id='HOST-%03d'%(len(rows)+1),label='missing attachment',classification='EXPECTED_ERROR',expected_error=0x8cd7,observed_error=status,status='PASS' if status==0x8cd7 else 'FAIL',evidence='HOST_REPRODUCED'))
            finally:
                fn(gl,'glDelete'+plural,None,[I,C.POINTER(U)])(1,C.byref(value))
                if error(): raise RuntimeError('object cleanup error')
        test('unbind program','glUseProgram',[0],[U])
        # No fake pointer handles: EGL_NO_SURFACE is a defined invalid swap argument.
        swap=fn(egl,'eglSwapBuffers',U,[P,P]);ok=swap(d,None);actual=geterr() if not ok else 0x3000
        rows.append(dict(id='HOST-%03d'%(len(rows)+1),label='swap EGL_NO_SURFACE',classification='EXPECTED_ERROR',expected_error=0x300d,observed_error=actual,status='PASS' if not ok and actual==0x300d else 'FAIL',evidence='HOST_REPRODUCED'))
        getint=fn(gl,'glGetIntegerv',None,[U,C.POINTER(I)]);getindexed=fn(gl,'glGetStringi',C.c_char_p,[U,U]);n=I();getint(0x821d,C.byref(n))
        extensions=[getindexed(0x1f03,j).decode() for j in range(n.value)]
        probes=[]
        for ext,names in [('GL_KHR_robustness',['glGetGraphicsResetStatusKHR','glReadnPixelsKHR']),('GL_EXT_robustness',['glGetGraphicsResetStatusEXT','glReadnPixelsEXT']),('GL_KHR_debug',['glDebugMessageCallbackKHR','glDebugMessageInsertKHR'])]:
            entries={name:bool(proc(name.encode())) for name in names};supported=ext in extensions and all(entries.values())
            probe=dict(extension=ext,advertised=ext in extensions,entrypoints=entries,status='SUPPORTED' if supported else 'UNSUPPORTED')
            if supported and 'robustness' in ext:
                pointer=proc(names[0].encode());probe['reset_status']=C.CFUNCTYPE(U)(pointer)();probe['actual_device_reset']=False
            probes.append(probe)
        return dict(schema_version=1,status='PASS' if all(r['status']=='PASS' for r in rows) else 'FAIL',scope='actual bounded host GLES/EGL calls, not physical GPU validation',vendor=getstring(0x1f00).decode(),renderer=getstring(0x1f01).decode(),version=getstring(0x1f02).decode(),extensions=extensions,capabilities=probes,cases=rows,device_status='BLOCKED_BY_HARDWARE')
    finally:
        if d:
            current(d,None,None,None)
            if s: destroy_surface(d,s)
            if c: destroy_context(d,c)
            terminate(d)

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--gles-library',default='libGLESv2.so.2');p.add_argument('--output',type=Path,required=True);a=p.parse_args()
    try: report=run(a.gles_library)
    except OSError as e: report=dict(schema_version=1,status='UNSUPPORTED',error=str(e))
    except Exception as e: report=dict(schema_version=1,status='HARNESS_FAILURE',error=str(e))
    a.output.parent.mkdir(parents=True,exist_ok=True);a.output.write_text(json.dumps(report,indent=2)+'\n');print(report['status']);raise SystemExit(0 if report['status']=='PASS' else 1)
