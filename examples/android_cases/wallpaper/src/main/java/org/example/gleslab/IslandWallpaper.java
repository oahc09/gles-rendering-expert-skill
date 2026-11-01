package org.example.gleslab;

import android.opengl.EGL14;
import android.opengl.EGLConfig;
import android.opengl.EGLContext;
import android.opengl.EGLDisplay;
import android.opengl.EGLSurface;
import android.opengl.GLES30;
import android.os.Handler;
import android.os.HandlerThread;
import android.os.Looper;
import android.service.wallpaper.WallpaperService;
import android.util.Log;
import android.view.Choreographer;
import android.view.MotionEvent;
import android.view.Surface;
import android.view.SurfaceHolder;

/** Independent EGL owner per Engine: preview/home instances never share GL names. */
public final class IslandWallpaper extends WallpaperService {
    @Override public Engine onCreateEngine() { return new IslandEngine(); }

    private final class IslandEngine extends Engine {
        private final RenderLoop loop = new RenderLoop();
        IslandEngine() { loop.start(); }
        @Override public void onCreate(SurfaceHolder holder) { super.onCreate(holder); setTouchEventsEnabled(true); }
        @Override public void onVisibilityChanged(boolean visible) { loop.setVisible(visible); }
        @Override public void onSurfaceChanged(SurfaceHolder holder, int format, int w, int h) {
            super.onSurfaceChanged(holder, format, w, h);
            loop.attach(holder.getSurface(), w, h);
        }
        @Override public void onSurfaceDestroyed(SurfaceHolder holder) {
            loop.detach(); super.onSurfaceDestroyed(holder);
        }
        @Override public void onTouchEvent(MotionEvent event) {
            loop.touch(event.getX(), event.getY()); super.onTouchEvent(event);
        }
        @Override public void onDestroy() { loop.shutdown(); super.onDestroy(); }
    }

    private static final class RenderLoop implements Choreographer.FrameCallback {
        private final Object ownerCompletion = new Object();
        private boolean ownerExited;
        private final HandlerThread thread = new HandlerThread("wallpaper-egl-owner") {
            @Override public void run() {
                try { super.run(); }
                finally {
                    synchronized (ownerCompletion) {
                        ownerExited = true;
                        ownerCompletion.notifyAll();
                    }
                }
            }
        };
        private Handler handler;
        private Choreographer choreographer;
        private EGLDisplay display = EGL14.EGL_NO_DISPLAY;
        private EGLContext context = EGL14.EGL_NO_CONTEXT;
        private EGLSurface eglSurface = EGL14.EGL_NO_SURFACE;
        private EGLConfig config;
        private Surface window; // Borrowed: SurfaceHolder owns and releases it.
        private boolean visible, stopped, callbackQueued;
        private int width = 1, height = 1, program;
        private float x = .5f, y = .5f;
        void start() {
            thread.start(); handler = new Handler(thread.getLooper());
            handler.post(() -> choreographer = Choreographer.getInstance());
        }
        void setVisible(boolean value) { handler.post(() -> { visible = value; schedule(); }); }
        void touch(float px, float py) { handler.post(() -> { x = px / width; y = 1f - py / height; }); }
        void attach(Surface surface, int w, int h) {
            handler.post(() -> {
                releaseSurface(); window = surface; width = Math.max(w, 1); height = Math.max(h, 1);
                try { ensureContext(); createSurface(); schedule(); }
                catch (RuntimeException error) { Log.e("GLESWallpaper", "attach failed", error); releaseAll(); }
            });
        }
        void detach() {
            // SurfaceHolder.Callback contract: do not return until rendering no
            // longer touches the borrowed Surface. An asynchronous post is unsafe.
            final boolean[] acknowledged = {false};
            Runnable release = () -> {
                try {
                    if (choreographer != null) choreographer.removeFrameCallback(this);
                    callbackQueued = false;
                    releaseSurface();
                    window = null;
                } finally {
                    synchronized (ownerCompletion) {
                        acknowledged[0] = true;
                        ownerCompletion.notifyAll();
                    }
                }
            };
            if (Looper.myLooper() == handler.getLooper()) {
                release.run(); // Never block the owner waiting for itself.
                return;
            }
            boolean posted = handler.post(release);
            boolean interrupted = false;
            synchronized (ownerCompletion) {
                // A stopped/rejected Handler is safe only after the owner has
                // actually exited. Its finally block also wakes us after failure.
                while (!ownerExited && (!posted || !acknowledged[0])) {
                    try { ownerCompletion.wait(); }
                    catch (InterruptedException error) { interrupted = true; }
                }
            }
            // Preserve cancellation without violating Surface destruction safety.
            if (interrupted) Thread.currentThread().interrupt();
        }
        void shutdown() { handler.post(() -> { stopped = true; if (choreographer != null) choreographer.removeFrameCallback(this); releaseAll(); thread.quitSafely(); }); }
        private void schedule() {
            if (!stopped && visible && eglSurface != EGL14.EGL_NO_SURFACE && !callbackQueued) {
                callbackQueued = true; choreographer.postFrameCallback(this);
            }
        }
        private void ensureContext() {
            if (context != EGL14.EGL_NO_CONTEXT) return;
            display = EGL14.eglGetDisplay(EGL14.EGL_DEFAULT_DISPLAY);
            int[] version = new int[2];
            if (!EGL14.eglInitialize(display, version, 0, version, 1)) throw new IllegalStateException("eglInitialize");
            if (!EGL14.eglBindAPI(EGL14.EGL_OPENGL_ES_API)) throw new IllegalStateException("eglBindAPI");
            int[] attributes = {EGL14.EGL_RENDERABLE_TYPE, 0x40, EGL14.EGL_SURFACE_TYPE, EGL14.EGL_WINDOW_BIT,
                    EGL14.EGL_RED_SIZE, 8, EGL14.EGL_GREEN_SIZE, 8, EGL14.EGL_BLUE_SIZE, 8, EGL14.EGL_NONE};
            EGLConfig[] configs = new EGLConfig[1]; int[] count = new int[1];
            if (!EGL14.eglChooseConfig(display, attributes, 0, configs, 0, 1, count, 0) || count[0] != 1) throw new IllegalStateException("eglChooseConfig");
            config = configs[0]; context = EGL14.eglCreateContext(display, config, EGL14.EGL_NO_CONTEXT,
                    new int[]{EGL14.EGL_CONTEXT_CLIENT_VERSION, 3, EGL14.EGL_NONE}, 0);
            if (context == EGL14.EGL_NO_CONTEXT) throw new IllegalStateException("eglCreateContext");
        }
        private void createSurface() {
            if (window == null || !window.isValid()) return;
            eglSurface = EGL14.eglCreateWindowSurface(display, config, window, new int[]{EGL14.EGL_NONE}, 0);
            if (eglSurface == EGL14.EGL_NO_SURFACE) throw new IllegalStateException("eglCreateWindowSurface");
            if (!EGL14.eglMakeCurrent(display, eglSurface, eglSurface, context)) throw new IllegalStateException("eglMakeCurrent");
            if (program == 0) program = makeProgram();
            Log.i("GLESWallpaper", "vendor=" + GLES30.glGetString(GLES30.GL_VENDOR)
                    + " renderer=" + GLES30.glGetString(GLES30.GL_RENDERER)
                    + " version=" + GLES30.glGetString(GLES30.GL_VERSION) + " output=SDR_RGBA8");
        }
        @Override public void doFrame(long nanos) {
            callbackQueued = false;
            if (stopped || !visible || eglSurface == EGL14.EGL_NO_SURFACE) return;
            GLES30.glViewport(0, 0, width, height); GLES30.glUseProgram(program);
            GLES30.glUniform2f(GLES30.glGetUniformLocation(program, "touch"), x, y);
            GLES30.glUniform1f(GLES30.glGetUniformLocation(program, "time"), (nanos % 60_000_000_000L) / 1e9f);
            GLES30.glDrawArrays(GLES30.GL_TRIANGLES, 0, 3);
            if (!EGL14.eglSwapBuffers(display, eglSurface)) {
                int error = EGL14.eglGetError();
                Log.e("GLESWallpaper", "swap error=" + error);
                if (error == EGL14.EGL_CONTEXT_LOST) {
                    // Old object names are invalid: no glDelete against the lost context.
                    program = 0; Surface retained = window; releaseAll(); window = retained;
                    try { ensureContext(); createSurface(); } catch (RuntimeException fail) { releaseAll(); }
                } else if (error == EGL14.EGL_BAD_SURFACE || error == EGL14.EGL_BAD_NATIVE_WINDOW) {
                    releaseSurface(); // Wait for a new SurfaceHolder callback, no busy retry.
                } else { visible = false; }
            }
            schedule();
        }
        private void releaseSurface() {
            if (display != EGL14.EGL_NO_DISPLAY) {
                EGL14.eglMakeCurrent(display, EGL14.EGL_NO_SURFACE, EGL14.EGL_NO_SURFACE, EGL14.EGL_NO_CONTEXT);
                if (eglSurface != EGL14.EGL_NO_SURFACE) EGL14.eglDestroySurface(display, eglSurface);
            }
            eglSurface = EGL14.EGL_NO_SURFACE;
        }
        private void releaseAll() {
            if (program != 0 && context.equals(EGL14.eglGetCurrentContext())) GLES30.glDeleteProgram(program);
            program = 0; releaseSurface();
            if (display != EGL14.EGL_NO_DISPLAY) {
                if (context != EGL14.EGL_NO_CONTEXT) EGL14.eglDestroyContext(display, context);
                EGL14.eglTerminate(display);
            }
            context = EGL14.EGL_NO_CONTEXT; display = EGL14.EGL_NO_DISPLAY;
        }
        private static int makeShader(int type, String source) {
            int shader = GLES30.glCreateShader(type); GLES30.glShaderSource(shader, source); GLES30.glCompileShader(shader);
            int[] ok = new int[1]; GLES30.glGetShaderiv(shader, GLES30.GL_COMPILE_STATUS, ok, 0);
            if (ok[0] == 0) { String log = GLES30.glGetShaderInfoLog(shader); GLES30.glDeleteShader(shader); throw new IllegalStateException(log); }
            return shader;
        }
        private static int makeProgram() {
            int vertex = makeShader(GLES30.GL_VERTEX_SHADER, "#version 300 es\nout vec2 uv;void main(){vec2 p=vec2((gl_VertexID<<1)&2,gl_VertexID&2);uv=p;gl_Position=vec4(p*2.-1.,0.,1.);}");
            int fragment = makeShader(GLES30.GL_FRAGMENT_SHADER, "#version 300 es\nprecision highp float;in vec2 uv;uniform vec2 touch;uniform float time;out vec4 color;void main(){float wave=sin(length(uv-touch)*36.-time*2.)*.03;color=vec4(.04+wave,.3+uv.y*.3+wave,.5+wave,1.);}");
            int result = GLES30.glCreateProgram(); GLES30.glAttachShader(result, vertex); GLES30.glAttachShader(result, fragment); GLES30.glLinkProgram(result);
            GLES30.glDeleteShader(vertex); GLES30.glDeleteShader(fragment); int[] ok = new int[1]; GLES30.glGetProgramiv(result, GLES30.GL_LINK_STATUS, ok, 0);
            if (ok[0] == 0) { String log=GLES30.glGetProgramInfoLog(result); GLES30.glDeleteProgram(result); throw new IllegalStateException(log); }
            return result;
        }
    }
}
