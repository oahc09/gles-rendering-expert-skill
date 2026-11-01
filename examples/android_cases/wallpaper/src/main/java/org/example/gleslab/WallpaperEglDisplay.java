package org.example.gleslab;

import android.opengl.EGL14;
import android.opengl.EGLDisplay;
import android.util.Log;

/** All wallpaper Engines cooperate here; unrelated EGL users must join this owner policy. */
final class WallpaperEglDisplay {
    private WallpaperEglDisplay() {}
    private static final SharedLease<EGLDisplay> POOL = new SharedLease<>(() -> {
        EGLDisplay display = EGL14.eglGetDisplay(EGL14.EGL_DEFAULT_DISPLAY);
        int[] version = new int[2];
        if (display == EGL14.EGL_NO_DISPLAY || !EGL14.eglInitialize(display, version, 0, version, 1))
            throw new IllegalStateException("shared eglInitialize error=" + EGL14.eglGetError());
        return display;
    }, display -> {
        if (!EGL14.eglTerminate(display)) Log.w("GLESWallpaper", "eglTerminate error=" + EGL14.eglGetError());
    });
    static SharedLease<EGLDisplay>.Handle acquire() { return POOL.acquire(); }
}
