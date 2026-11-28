package org.example.gleslab;

/** Choosing which EGL objects need replacement; no Android/GPU evidence is implied. */
final class WallpaperSurfacePolicy {
    enum Action { KEEP_DRAWABLE, REPLACE_DRAWABLE, REPLACE_CONTEXT }

    private WallpaperSurfacePolicy() {}

    static Action attach(boolean haveContext, boolean haveDrawable, boolean sameWindow,
                         boolean holderChanged, boolean sameOutput) {
        if (!haveContext || !sameOutput) return Action.REPLACE_CONTEXT;
        // SurfaceHolder may wrap a new buffer queue in the same Java Surface.
        if (holderChanged || !haveDrawable || !sameWindow) return Action.REPLACE_DRAWABLE;
        return Action.KEEP_DRAWABLE;
    }
}
