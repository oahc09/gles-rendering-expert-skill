# W4 external-image finite semantic coverage

Primary sources (fixed revisions and hashes in `benchmarks/coverage/external-image/sources.json`):
- [KHR_image_base](https://raw.githubusercontent.com/KhronosGroup/EGL-Registry/8e56e86e65687697ef54114cdb1afabdfac756bf/extensions/KHR/EGL_KHR_image_base.txt): preserved source content; destroying image handle does not invalidate existing siblings.
- [KHR_gl_image family](https://raw.githubusercontent.com/KhronosGroup/EGL-Registry/8e56e86e65687697ef54114cdb1afabdfac756bf/extensions/KHR/EGL_KHR_gl_image.txt): texture2D source name cast to client buffer, context/level constraints.
- [OES_EGL_image_external](https://raw.githubusercontent.com/KhronosGroup/OpenGL-Registry/1cdd228e34966dd6b95bd203e9f84faba0f371a1/extensions/OES/OES_EGL_image_external.txt): external binding and sampler restrictions.
- [external ESSL3](https://raw.githubusercontent.com/KhronosGroup/OpenGL-Registry/1cdd228e34966dd6b95bd203e9f84faba0f371a1/extensions/OES/OES_EGL_image_external_essl3.txt): samplerExternalOES in ESSL3.
- [external wrap modes](https://raw.githubusercontent.com/KhronosGroup/OpenGL-Registry/1cdd228e34966dd6b95bd203e9f84faba0f371a1/extensions/EXT/EXT_EGL_image_external_wrap_modes.txt): relaxes base OES wrap restriction; ANGLE's actual REPEAT acceptance is expected, not driver failure.

Real source/import/sample/destroy/sample loop is in the new experiment. A nonsymmetric CPU byte oracle detects axis reversal and channel errors. Success applies only to RGBA8 same-context software hosts. AHB/protected/native producer synchronization and physical performance remain NOT_RUN. This adds runtime semantics beyond static W4 extension advertising; it does not complete general platform ingestion.
