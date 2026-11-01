package org.example.gleslab;

import android.opengl.EGL14;
import android.opengl.EGLConfig;
import android.opengl.EGLContext;
import android.opengl.EGLDisplay;
import android.opengl.EGLSurface;
import android.opengl.GLES30;
import android.os.Build;
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
        @Override public void onVisibilityChanged(boolean visible) {
            if (visible && getSurfaceHolder().getSurface().isValid()) {
                android.graphics.Rect frame = getSurfaceHolder().getSurfaceFrame();
                loop.attach(getSurfaceHolder().getSurface(), frame.width(), frame.height(), displayCapabilities());
            }
            loop.setVisible(visible);
        }
        private HdrEglOutput displayCapabilities() {
            return Build.VERSION.SDK_INT >= 29
                    ? HdrEglOutput.probeDisplay(getDisplayContext()) : HdrEglOutput.unknown();
        }
        @Override public void onSurfaceChanged(SurfaceHolder holder, int format, int w, int h) {
            super.onSurfaceChanged(holder, format, w, h);
            HdrEglOutput capabilities = displayCapabilities();
            loop.attach(holder.getSurface(), w, h, capabilities);
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
        private SharedLease<EGLDisplay>.Handle displayLease;
        private EGLContext context = EGL14.EGL_NO_CONTEXT;
        private EGLSurface eglSurface = EGL14.EGL_NO_SURFACE;
        private EGLConfig config;
        private Surface window; // Borrowed: SurfaceHolder owns and releases it.
        private boolean visible, stopped, callbackQueued;
        private int width = 1, height = 1, program;
        private float x = .5f, y = .5f;
        private HdrEglOutput output = HdrEglOutput.unknown();
        private boolean pq, forceSdr;
        private String eglExtensions;
        private int outputEncoding; // 0=shader sRGB, 1=hardware sRGB, 2=shader BT2020/PQ
        void start() {
            thread.start(); handler = new Handler(thread.getLooper());
            handler.post(() -> choreographer = Choreographer.getInstance());
        }
        void setVisible(boolean value) { handler.post(() -> { visible = value; schedule(); }); }
        void touch(float px, float py) { handler.post(() -> { x = px / width; y = 1f - py / height; }); }
        void attach(Surface surface, int w, int h, HdrEglOutput capabilities) {
            handler.post(() -> {
                releaseAll(); output = capabilities; forceSdr = false;
                window = surface; width = Math.max(w, 1); height = Math.max(h, 1);
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
            if (displayLease == null) displayLease = WallpaperEglDisplay.acquire();
            display = displayLease.value;
            if (!EGL14.eglBindAPI(EGL14.EGL_OPENGL_ES_API)) throw new IllegalStateException("eglBindAPI");
            eglExtensions = EGL14.eglQueryString(display, EGL14.EGL_EXTENSIONS);
            pq = !forceSdr && HdrOutputPolicy.canAttemptPq(output.displayKnown, output.hdr10, eglExtensions);
            config = HdrEglOutput.chooseConfig(display, pq);
            if (config == null && pq) {
                Log.i("GLESWallpaper", "PQ fallback: no exact RGB10A2 window config");
                pq = false; forceSdr = true; config = HdrEglOutput.chooseConfig(display, false);
            }
            if (config == null) throw new IllegalStateException("no supported RGBA8/RGB10A2 config");
            context = EGL14.eglCreateContext(display, config, EGL14.EGL_NO_CONTEXT,
                    new int[]{EGL14.EGL_CONTEXT_CLIENT_VERSION, 3, EGL14.EGL_NONE}, 0);
            if (context == EGL14.EGL_NO_CONTEXT && pq) {
                Log.w("GLESWallpaper", "PQ context rejected error=" + EGL14.eglGetError());
                pq = false; forceSdr = true; config = HdrEglOutput.chooseConfig(display, false);
                if (config != null) context = EGL14.eglCreateContext(display, config, EGL14.EGL_NO_CONTEXT,
                        new int[]{EGL14.EGL_CONTEXT_CLIENT_VERSION, 3, EGL14.EGL_NONE}, 0);
            }
            if (context == EGL14.EGL_NO_CONTEXT) throw new IllegalStateException("eglCreateContext");
        }
        private void createSurface() {
            if (window == null || !window.isValid()) return;
            try {
                boolean colorspace = HdrOutputPolicy.hasExtension(eglExtensions, "EGL_KHR_gl_colorspace");
                int requested = pq ? HdrOutputPolicy.EGL_GL_COLORSPACE_BT2020_PQ_EXT
                        : HdrOutputPolicy.EGL_GL_COLORSPACE_LINEAR_KHR;
                int[] attributes = colorspace ? new int[]{HdrOutputPolicy.EGL_GL_COLORSPACE_KHR,
                        requested, EGL14.EGL_NONE} : new int[]{EGL14.EGL_NONE};
                eglSurface = EGL14.eglCreateWindowSurface(display, config, window, attributes, 0);
                if (eglSurface == EGL14.EGL_NO_SURFACE)
                    throw new IllegalStateException("eglCreateWindowSurface error=" + EGL14.eglGetError());
                if (!EGL14.eglMakeCurrent(display, eglSurface, eglSurface, context))
                    throw new IllegalStateException("eglMakeCurrent error=" + EGL14.eglGetError());
                int[] actual = {-1}, encoding = {-1};
                boolean queried = colorspace && EGL14.eglQuerySurface(display, eglSurface,
                        HdrOutputPolicy.EGL_GL_COLORSPACE_KHR, actual, 0);
                if (colorspace && !queried) EGL14.eglGetError(); // Consume and report query failure below.
                GLES30.glGetFramebufferAttachmentParameteriv(GLES30.GL_FRAMEBUFFER, GLES30.GL_BACK,
                        GLES30.GL_FRAMEBUFFER_ATTACHMENT_COLOR_ENCODING, encoding, 0);
                boolean encodingOk = GLES30.glGetError() == GLES30.GL_NO_ERROR;
                if (pq && !HdrOutputPolicy.acceptsPqSurface(queried, actual[0], encodingOk, encoding[0]))
                    throw new IllegalStateException("PQ surface/attachment verification rejected");
                if (!encodingOk || (encoding[0] != GLES30.GL_LINEAR && encoding[0] != GLES30.GL_SRGB))
                    throw new IllegalStateException("unknown framebuffer encoding");
                outputEncoding = pq ? 2 : (encoding[0] == GLES30.GL_SRGB ? 1 : 0);
                if (program == 0) program = makeProgram();
                Log.i("GLESWallpaper", "vendor=" + GLES30.glGetString(GLES30.GL_VENDOR)
                        + " renderer=" + GLES30.glGetString(GLES30.GL_RENDERER)
                        + " version=" + GLES30.glGetString(GLES30.GL_VERSION)
                        + " display=" + output.displayId + " hdr10=" + output.hdr10
                        + " wideColor=" + output.wideColor + " queriedColorspace=" + actual[0]
                        + " attachmentEncoding=" + encoding[0]
                        + " output=" + (pq ? "BT2020_PQ_RGB10A2_REQUEST_ACCEPTED" : "SDR_RGBA8")
                        + " physicalHDR=NOT_VERIFIED");
            } catch (RuntimeException failure) {
                if (!pq) throw failure;
                Log.w("GLESWallpaper", "PQ rejected; recreate independent SDR config/context", failure);
                Surface retained = window;
                releaseAll(); window = retained; forceSdr = true;
                ensureContext(); createSurface(); // Bounded: forceSdr prevents another PQ attempt.
            }
        }
        @Override public void doFrame(long nanos) {
            callbackQueued = false;
            if (stopped || !visible || eglSurface == EGL14.EGL_NO_SURFACE) return;
            GLES30.glViewport(0, 0, width, height); GLES30.glUseProgram(program);
            GLES30.glUniform1i(GLES30.glGetUniformLocation(program, "outputEncoding"), outputEncoding);
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
                if (displayLease != null) { displayLease.close(); displayLease = null; }
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
            int fragment = makeShader(GLES30.GL_FRAGMENT_SHADER, "#version 300 es\nprecision highp float;\nin vec2 uv;uniform vec2 touch;uniform float time;uniform int outputEncoding;out vec4 color;\nvec3 srgb(vec3 x){return mix(12.92*x,1.055*pow(max(x,vec3(0.)),vec3(1./2.4))-.055,step(vec3(.0031308),x));}\nvec3 pqEncode(vec3 nits){vec3 p=pow(clamp(nits/10000.,0.,1.),vec3(2610./16384.));return pow((3424./4096.+(2413./128.)*p)/(1.+(2392./128.)*p),vec3(2523./32.));}\nvoid main(){float wave=sin(length(uv-touch)*36.-time*2.)*.03;vec3 scene=max(vec3(.04+wave,.3+uv.y*.3+wave,.5+wave),vec3(0.));float highlight=3.*exp(-200.*dot(uv-touch,uv-touch));scene+=vec3(highlight);if(outputEncoding==2){mat3 to2020=mat3(.627404,.069097,.016392,.329283,.919540,.088013,.043313,.011362,.895595);color=vec4(pqEncode(clamp(to2020*scene*203.,0.,1000.)),1.);}else{vec3 mapped=scene/(vec3(1.)+scene);color=vec4(outputEncoding==1?mapped:srgb(mapped),1.);}}");
            int result = GLES30.glCreateProgram(); GLES30.glAttachShader(result, vertex); GLES30.glAttachShader(result, fragment); GLES30.glLinkProgram(result);
            GLES30.glDeleteShader(vertex); GLES30.glDeleteShader(fragment); int[] ok = new int[1]; GLES30.glGetProgramiv(result, GLES30.GL_LINK_STATUS, ok, 0);
            if (ok[0] == 0) { String log=GLES30.glGetProgramInfoLog(result); GLES30.glDeleteProgram(result); throw new IllegalStateException(log); }
            return result;
        }
    }
}
