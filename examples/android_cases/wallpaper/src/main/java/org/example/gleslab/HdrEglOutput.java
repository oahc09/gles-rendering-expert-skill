package org.example.gleslab;

import android.content.Context;
import android.opengl.EGL14;
import android.opengl.EGLConfig;
import android.opengl.EGLDisplay;
import android.os.Build;
import android.view.Display;
import android.view.WindowManager;

/** Capability/config probes only. Does not certify compositor or physical luminance. */
final class HdrEglOutput {
    final boolean displayKnown, hdr10, wideColor;
    final int displayId;
    HdrEglOutput(boolean known, boolean hdr, boolean wide, int id) {
        displayKnown = known; hdr10 = hdr; wideColor = wide; displayId = id;
    }
    static HdrEglOutput unknown() { return new HdrEglOutput(false, false, false, -1); }

    @SuppressWarnings("deprecation")
    static HdrEglOutput probeDisplay(Context engineDisplayContext) {
        // Caller uses Engine.getDisplayContext(), never the service's default display.
        WindowManager manager = engineDisplayContext.getSystemService(WindowManager.class);
        Display display = manager == null ? null : manager.getDefaultDisplay();
        if (display == null || !display.isValid()) return unknown();
        int[] types = Build.VERSION.SDK_INT >= 34
                ? display.getMode().getSupportedHdrTypes()
                : display.getHdrCapabilities().getSupportedHdrTypes();
        boolean hdr10 = false;
        for (int type : types) if (type == Display.HdrCapabilities.HDR_TYPE_HDR10) hdr10 = true;
        return new HdrEglOutput(true, hdr10, display.isWideColorGamut(), display.getDisplayId());
    }

    static EGLConfig chooseConfig(EGLDisplay display, boolean pq) {
        int[] attributes = {EGL14.EGL_RENDERABLE_TYPE, 0x40, // EGL_OPENGL_ES3_BIT
                EGL14.EGL_SURFACE_TYPE, EGL14.EGL_WINDOW_BIT,
                EGL14.EGL_COLOR_BUFFER_TYPE, EGL14.EGL_RGB_BUFFER,
                EGL14.EGL_RED_SIZE, pq ? 10 : 8, EGL14.EGL_GREEN_SIZE, pq ? 10 : 8,
                EGL14.EGL_BLUE_SIZE, pq ? 10 : 8, EGL14.EGL_ALPHA_SIZE, pq ? 2 : 8,
                EGL14.EGL_NONE};
        int[] count = new int[1];
        if (!EGL14.eglChooseConfig(display, attributes, 0, null, 0, 0, count, 0)
                || count[0] <= 0) return null;
        EGLConfig[] configs = new EGLConfig[count[0]];
        if (!EGL14.eglChooseConfig(display, attributes, 0, configs, 0, configs.length, count, 0)) return null;
        for (int i = 0; i < count[0]; ++i) {
            EGLConfig config = configs[i];
            int r = channel(display, config, EGL14.EGL_RED_SIZE);
            int g = channel(display, config, EGL14.EGL_GREEN_SIZE);
            int b = channel(display, config, EGL14.EGL_BLUE_SIZE);
            int a = channel(display, config, EGL14.EGL_ALPHA_SIZE);
            if (pq ? HdrOutputPolicy.isRgb10A2(r, g, b, a) : r == 8 && g == 8 && b == 8 && a == 8)
                return config;
        }
        return null; // No floating-point/P3/HLG inference from a different config.
    }
    private static int channel(EGLDisplay display, EGLConfig config, int attribute) {
        int[] value = new int[1];
        return EGL14.eglGetConfigAttrib(display, config, attribute, value, 0) ? value[0] : -1;
    }
}
