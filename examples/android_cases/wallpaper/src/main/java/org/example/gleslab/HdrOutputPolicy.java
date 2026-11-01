package org.example.gleslab;

/** Pure decision helpers. An advertised display capability is never surface acceptance. */
final class HdrOutputPolicy {
    static final int EGL_GL_COLORSPACE_KHR = 0x309D;
    static final int EGL_GL_COLORSPACE_LINEAR_KHR = 0x308A;
    static final int EGL_GL_COLORSPACE_BT2020_PQ_EXT = 0x3340;
    private HdrOutputPolicy() {}

    static boolean hasExtension(String list, String name) {
        if (list == null || name == null || name.isEmpty()) return false;
        for (String token : list.trim().split("\\s+")) if (token.equals(name)) return true;
        return false;
    }

    static boolean canAttemptPq(boolean displayKnown, boolean hdr10, String eglExtensions) {
        return displayKnown && hdr10
                && hasExtension(eglExtensions, "EGL_KHR_gl_colorspace")
                && hasExtension(eglExtensions, "EGL_EXT_gl_colorspace_bt2020_pq");
    }

    static boolean isRgb10A2(int red, int green, int blue, int alpha) {
        return red == 10 && green == 10 && blue == 10 && alpha == 2;
    }

    static boolean acceptsPqSurface(boolean querySucceeded, int colorspace,
                                     boolean encodingQuerySucceeded, int glEncoding) {
        // BT2020_PQ uses GL_LINEAR attachments: the shader, not GL, encodes PQ.
        return querySucceeded && colorspace == EGL_GL_COLORSPACE_BT2020_PQ_EXT
                && encodingQuerySucceeded && glEncoding == 0x2601; // GL_LINEAR
    }
}
