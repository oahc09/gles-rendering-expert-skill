package org.example.gleslab;

import static org.example.gleslab.WallpaperSurfacePolicy.Action.*;

final class WallpaperSurfacePolicyTest {
    private static void expect(WallpaperSurfacePolicy.Action expected, boolean context,
                               boolean drawable, boolean sameWindow, boolean holderChanged,
                               boolean sameOutput) {
        WallpaperSurfacePolicy.Action observed = WallpaperSurfacePolicy.attach(context, drawable,
                sameWindow, holderChanged, sameOutput);
        if (observed != expected) throw new AssertionError(observed + " != " + expected);
    }

    public static void main(String[] args) {
        expect(REPLACE_CONTEXT, false, false, false, true, true);  // first create
        expect(KEEP_DRAWABLE, true, true, true, false, true);      // visibility-only reprobe
        expect(REPLACE_DRAWABLE, true, true, true, true, true);    // same wrapper, event/new drawable
        expect(REPLACE_DRAWABLE, true, false, false, true, true); // after detach
        expect(REPLACE_DRAWABLE, true, true, false, false, true); // changed window on visibility
        expect(REPLACE_DRAWABLE, true, false, true, false, true); // BAD_SURFACE; wait for holder
        expect(REPLACE_CONTEXT, true, true, true, false, false); // incompatible output change
        expect(REPLACE_CONTEXT, false, false, true, false, true); // real context loss
        System.out.println("PASS: 8 owner policy cases");
    }
}
