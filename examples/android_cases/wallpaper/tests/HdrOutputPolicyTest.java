package org.example.gleslab;

/** Plain Java policy execution: not an EGL driver or Android display test. */
public final class HdrOutputPolicyTest {
    private static int checks;
    private static void check(boolean condition) {
        checks++;
        if (!condition) throw new AssertionError("HDR policy check " + checks);
    }
    public static void main(String[] args) {
        String both = "EGL_KHR_gl_colorspace EGL_EXT_gl_colorspace_bt2020_pq";
        check(HdrOutputPolicy.canAttemptPq(true, true, both));
        check(!HdrOutputPolicy.canAttemptPq(false, true, both));
        check(!HdrOutputPolicy.canAttemptPq(true, false, both));
        check(!HdrOutputPolicy.canAttemptPq(true, true, "EGL_EXT_gl_colorspace_bt2020_pq"));
        check(!HdrOutputPolicy.canAttemptPq(true, true, "EGL_KHR_gl_colorspace"));
        check(!HdrOutputPolicy.canAttemptPq(true, true, null));
        check(!HdrOutputPolicy.hasExtension("EGL_EXT_gl_colorspace_bt2020_pq_FAKE", "EGL_EXT_gl_colorspace_bt2020_pq"));
        check(HdrOutputPolicy.hasExtension("\tEGL_KHR_gl_colorspace\n", "EGL_KHR_gl_colorspace"));
        check(!HdrOutputPolicy.hasExtension("", ""));
        check(HdrOutputPolicy.isRgb10A2(10, 10, 10, 2));
        check(!HdrOutputPolicy.isRgb10A2(8, 8, 8, 8));
        check(!HdrOutputPolicy.isRgb10A2(16, 16, 16, 16));
        check(!HdrOutputPolicy.isRgb10A2(10, 8, 10, 2));
        check(HdrOutputPolicy.acceptsPqSurface(true, 0x3340, true, 0x2601));
        check(!HdrOutputPolicy.acceptsPqSurface(false, 0x3340, true, 0x2601));
        check(!HdrOutputPolicy.acceptsPqSurface(true, 0x308A, true, 0x2601));
        check(!HdrOutputPolicy.acceptsPqSurface(true, 0x3340, false, 0x2601));
        check(!HdrOutputPolicy.acceptsPqSurface(true, 0x3340, true, 0x8C40));
        System.out.println("HDR_POLICY_CHECKS=" + checks + " PASS; Android/EGL/device=NOT_RUN");
    }
}
