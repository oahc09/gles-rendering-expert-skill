# Fragment image repair pipeline

Status: HOST_PASS

4x4 RGBA8, one-code-value CPU+peer tolerance.
Provider BLOCKED_BY_PROVIDER; no model quality score.
- uv-swizzle / repair: PASS
- uv-swizzle / original: FAIL
- uv-swizzle / wrong_repair: FAIL
- color-swizzle / repair: PASS
- color-swizzle / original: FAIL
- color-swizzle / wrong_repair: FAIL
- premultiplied-alpha / repair: PASS
- premultiplied-alpha / original: FAIL
- premultiplied-alpha / wrong_repair: FAIL
- alpha-output / repair: PASS
- alpha-output / original: FAIL
- alpha-output / wrong_repair: FAIL
