package org.example.gleslab;

import android.opengl.EGL14;
import android.opengl.EGLContext;
import android.opengl.GLES30;
import android.util.Log;

/** GL-thread-only owned native AHB import, with deterministic pixel validation. */
final class NativeHardwareBufferDisplay {
    private static final boolean libraryAvailable;
    static {
        boolean loaded;
        try { System.loadLibrary("gles_ahb_case"); loaded=true; }
        catch (UnsatisfiedLinkError error) { loaded=false; Log.w("GLES-AHB","Native library unavailable; external-texture fallback",error); }
        libraryAvailable=loaded;
    }
    private long handle;
    private int program;
    private EGLContext owner=EGL14.EGL_NO_CONTEXT;
    boolean active(){return handle!=0;}
    void onContextRecreated(){
        // Explicit generation boundary: do not delete stale GL names even if native handles are recycled.
        if(handle!=0&&libraryAvailable)nativeRelease(handle,false);
        handle=0;program=0;owner=EGL14.EGL_NO_CONTEXT;
    }
    boolean create(){
        if(!libraryAvailable)return false;
        owner=EGL14.eglGetCurrentContext();handle=nativeCreate();
        if(handle==0){Log.w("GLES-AHB",nativeError());return false;}
        if(!nativeCheckPattern(handle)){Log.w("GLES-AHB",nativeError());release();return false;}
        String vertex="#version 300 es\nout vec2 uv;void main(){vec2 p=vec2((gl_VertexID<<1)&2,gl_VertexID&2);uv=p;gl_Position=vec4(p*2.-1.,0,1);}";
        String fragment="#version 300 es\nprecision highp float;in vec2 uv;uniform sampler2D image;out vec4 color;void main(){color=texture(image,uv);}";
        int vs=0,fs=0;
        try {
            vs=compile(GLES30.GL_VERTEX_SHADER,vertex);fs=compile(GLES30.GL_FRAGMENT_SHADER,fragment);
            program=GLES30.glCreateProgram();GLES30.glAttachShader(program,vs);GLES30.glAttachShader(program,fs);GLES30.glLinkProgram(program);
            int[] ok=new int[1];GLES30.glGetProgramiv(program,GLES30.GL_LINK_STATUS,ok,0);
            if(ok[0]==0)throw new IllegalStateException(GLES30.glGetProgramInfoLog(program));
            Log.i("GLES-AHB","Real AHB EGLImage RGBA8 16x16 readback PASS on current device; not performance proof");
            return true;
        } catch(RuntimeException error){Log.w("GLES-AHB","shader path failed; fallback",error);release();return false;}
        finally{if(vs!=0)GLES30.glDeleteShader(vs);if(fs!=0)GLES30.glDeleteShader(fs);}
    }
    void draw(){
        if(handle==0||!owner.equals(EGL14.eglGetCurrentContext()))return;
        GLES30.glUseProgram(program);GLES30.glActiveTexture(GLES30.GL_TEXTURE0);
        GLES30.glBindTexture(GLES30.GL_TEXTURE_2D,nativeTexture(handle));GLES30.glUniform1i(GLES30.glGetUniformLocation(program,"image"),0);
        GLES30.glDrawArrays(GLES30.GL_TRIANGLES,0,3);
    }
    void release(){
        boolean current=owner.equals(EGL14.eglGetCurrentContext());
        if(handle!=0&&libraryAvailable)nativeRelease(handle,current);
        if(program!=0&&current)GLES30.glDeleteProgram(program);
        handle=0;program=0;owner=EGL14.EGL_NO_CONTEXT;
    }
    private static int compile(int type,String source){int s=GLES30.glCreateShader(type);GLES30.glShaderSource(s,source);GLES30.glCompileShader(s);int[] ok=new int[1];GLES30.glGetShaderiv(s,GLES30.GL_COMPILE_STATUS,ok,0);if(ok[0]==0){String log=GLES30.glGetShaderInfoLog(s);GLES30.glDeleteShader(s);throw new IllegalStateException(log);}return s;}
    private static native long nativeCreate();
    private static native int nativeTexture(long handle);
    private static native boolean nativeCheckPattern(long handle);
    private static native void nativeRelease(long handle,boolean ownerAlive);
    private static native String nativeError();
}
