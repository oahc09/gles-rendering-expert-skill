package org.example.gleslab;

import android.app.Activity;
import android.graphics.Canvas;
import android.graphics.Color;
import android.graphics.Paint;
import android.graphics.SurfaceTexture;
import android.opengl.GLES11Ext;
import android.opengl.GLES30;
import android.opengl.GLSurfaceView;
import android.os.Bundle;
import android.os.Handler;
import android.os.Looper;
import android.util.Log;
import android.view.Choreographer;
import android.view.Surface;
import java.util.concurrent.atomic.AtomicBoolean;
import javax.microedition.khronos.egl.EGLConfig;
import javax.microedition.khronos.opengles.GL10;

/** Reproducible Surface producer -> external texture -> display pipeline, no camera permission. */
public final class ExternalSurfaceActivity extends Activity implements Choreographer.FrameCallback {
    private GLSurfaceView view;
    private final ExternalRenderer renderer = new ExternalRenderer();
    private boolean resumed;
    private final Paint paint = new Paint();

    @Override public void onCreate(Bundle state) {
        super.onCreate(state);
        view = new GLSurfaceView(this); view.setEGLContextClientVersion(3);
        view.setEGLConfigChooser(8, 8, 8, 8, 0, 0);
        view.setPreserveEGLContextOnPause(false); // Resource recreation is an explicit exercise.
        view.setRenderer(renderer); view.setRenderMode(GLSurfaceView.RENDERMODE_WHEN_DIRTY);
        setContentView(view);
        // Display capabilities are observations, NOT proof that the EGL surface is HDR.
        Log.i("GLESSurface", "wideColorDisplay=" + getWindowManager().getDefaultDisplay().isWideColorGamut()
                + " HDRtypes=" + getWindowManager().getDefaultDisplay().getHdrCapabilities().getSupportedHdrTypes().length
                + " chosenOutput=SDR_RGBA8 (HDR/WCG config path NOT_RUN)");
    }
    @Override protected void onResume() {
        super.onResume(); resumed=true; view.onResume(); Choreographer.getInstance().postFrameCallback(this);
    }
    @Override protected void onPause() {
        resumed=false; Choreographer.getInstance().removeFrameCallback(this);
        // Producer on UI thread stops before queueing consumer-side cleanup on GL thread.
        renderer.stopProducer(); view.queueEvent(renderer::releaseCurrentContextResources);
        view.onPause(); super.onPause();
    }
    @Override public void doFrame(long frameTimeNanos) {
        if (!resumed) return;
        Surface surface=renderer.producer;
        if(surface!=null && surface.isValid()) {
            Canvas canvas=null;
            try {
                canvas=surface.lockCanvas(null);
                canvas.drawColor(Color.rgb(12,40,70));
                float phase=(frameTimeNanos%4_000_000_000L)/4e9f;
                paint.setColor(Color.rgb(50,210,180));
                canvas.drawRect(phase*320,60,phase*320+100,160,paint);
                paint.setColor(Color.WHITE);paint.setTextSize(20);canvas.drawText("Surface -> external OES",10,30,paint);
            } catch (RuntimeException error) { Log.w("GLESSurface","producer unavailable",error); }
            finally { if(canvas!=null) { try { surface.unlockCanvasAndPost(canvas); } catch(RuntimeException error) { Log.w("GLESSurface","producer post failed",error); } } }
        }
        Choreographer.getInstance().postFrameCallback(this);
    }

    private final class ExternalRenderer implements GLSurfaceView.Renderer {
        private volatile Surface producer;
        private SurfaceTexture consumer;
        private final AtomicBoolean frameAvailable=new AtomicBoolean();
        private final float[] transform=new float[16];
        private int texture,program;
        private boolean supported, hasImage;
        private final Handler ui = new Handler(Looper.getMainLooper());
        @Override public void onSurfaceCreated(GL10 unused, EGLConfig config) {
            // A lost context owns no reusable names. Java Surface objects still need release.
            stopProducer();if(consumer!=null){consumer.release();consumer=null;}texture=0;program=0;hasImage=false;
            supported=extension("GL_OES_EGL_image_external")&&extension("GL_OES_EGL_image_external_essl3");
            Log.i("GLESSurface","renderer="+GLES30.glGetString(GLES30.GL_RENDERER)+" externalESSL3="+supported);
            if(!supported) return; // Visible SDR clear fallback, not an illegal sampler path.
            int[] names=new int[1];GLES30.glGenTextures(1,names,0);texture=names[0];
            GLES30.glBindTexture(GLES11Ext.GL_TEXTURE_EXTERNAL_OES,texture);
            GLES30.glTexParameteri(GLES11Ext.GL_TEXTURE_EXTERNAL_OES,GLES30.GL_TEXTURE_MIN_FILTER,GLES30.GL_LINEAR);
            GLES30.glTexParameteri(GLES11Ext.GL_TEXTURE_EXTERNAL_OES,GLES30.GL_TEXTURE_MAG_FILTER,GLES30.GL_LINEAR);
            GLES30.glTexParameteri(GLES11Ext.GL_TEXTURE_EXTERNAL_OES,GLES30.GL_TEXTURE_WRAP_S,GLES30.GL_CLAMP_TO_EDGE);
            GLES30.glTexParameteri(GLES11Ext.GL_TEXTURE_EXTERNAL_OES,GLES30.GL_TEXTURE_WRAP_T,GLES30.GL_CLAMP_TO_EDGE);
            consumer=new SurfaceTexture(texture);consumer.setDefaultBufferSize(480,240);
            consumer.setOnFrameAvailableListener(surfaceTexture->{frameAvailable.set(true);view.requestRender();},ui);
            producer=new Surface(consumer);
            String vertex="#version 300 es\nout vec2 uv;uniform mat4 transform;void main(){vec2 p=vec2((gl_VertexID<<1)&2,gl_VertexID&2);uv=(transform*vec4(p,0,1)).xy;gl_Position=vec4(p*2.-1.,0,1);}";
            String fragment="#version 300 es\n#extension GL_OES_EGL_image_external_essl3 : require\nprecision mediump float;in vec2 uv;uniform samplerExternalOES image;out vec4 color;void main(){color=texture(image,uv);}";
            int vs=compile(GLES30.GL_VERTEX_SHADER,vertex),fs=compile(GLES30.GL_FRAGMENT_SHADER,fragment);
            program=GLES30.glCreateProgram();GLES30.glAttachShader(program,vs);GLES30.glAttachShader(program,fs);GLES30.glLinkProgram(program);
            GLES30.glDeleteShader(vs);GLES30.glDeleteShader(fs);int[] ok=new int[1];GLES30.glGetProgramiv(program,GLES30.GL_LINK_STATUS,ok,0);
            if(ok[0]==0)throw new IllegalStateException(GLES30.glGetProgramInfoLog(program));
        }
        @Override public void onSurfaceChanged(GL10 unused,int w,int h){GLES30.glViewport(0,0,w,h);}
        @Override public void onDrawFrame(GL10 unused){
            GLES30.glClearColor(.08f,.12f,.2f,1);GLES30.glClear(GLES30.GL_COLOR_BUFFER_BIT);
            if(!supported||consumer==null)return;
            // SurfaceTexture manages producer acquire synchronization; this must run on the owning GL thread.
            if(frameAvailable.getAndSet(false)){consumer.updateTexImage();consumer.getTransformMatrix(transform);hasImage=true;}
            if(!hasImage)return;
            GLES30.glUseProgram(program);GLES30.glActiveTexture(GLES30.GL_TEXTURE0);
            GLES30.glBindTexture(GLES11Ext.GL_TEXTURE_EXTERNAL_OES,texture);
            GLES30.glUniform1i(GLES30.glGetUniformLocation(program,"image"),0);
            GLES30.glUniformMatrix4fv(GLES30.glGetUniformLocation(program,"transform"),1,false,transform,0);
            GLES30.glDrawArrays(GLES30.GL_TRIANGLES,0,3);
        }
        synchronized void stopProducer(){Surface old=producer;producer=null;if(old!=null)old.release();}
        void releaseCurrentContextResources(){
            stopProducer();if(consumer!=null){consumer.setOnFrameAvailableListener(null);consumer.release();consumer=null;}
            if(texture!=0){GLES30.glDeleteTextures(1,new int[]{texture},0);texture=0;}
            if(program!=0){GLES30.glDeleteProgram(program);program=0;}frameAvailable.set(false);hasImage=false;
        }
        private boolean extension(String wanted){int[] n=new int[1];GLES30.glGetIntegerv(GLES30.GL_NUM_EXTENSIONS,n,0);for(int i=0;i<n[0];i++)if(wanted.equals(GLES30.glGetStringi(GLES30.GL_EXTENSIONS,i)))return true;return false;}
        private int compile(int type,String source){int shader=GLES30.glCreateShader(type);GLES30.glShaderSource(shader,source);GLES30.glCompileShader(shader);int[] ok=new int[1];GLES30.glGetShaderiv(shader,GLES30.GL_COMPILE_STATUS,ok,0);if(ok[0]==0){String log=GLES30.glGetShaderInfoLog(shader);GLES30.glDeleteShader(shader);throw new IllegalStateException(log);}return shader;}
    }
}
