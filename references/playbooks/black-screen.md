# Black screen / flicker diagnostic

1. **Symptom**: distinguish no presented frames from clear-only output, wrong attachment, stale video frame and intermittent corruption. Save logs/timestamp, not just a screenshot.
2. **Snapshot**: GL/EGL versions/strings/extensions, backend, window/surface/context generation, dimensions, framebuffer binding, viewport/scissor, draw/read buffers and shader logs.
3. **Minimal repro**: remove assets and postprocessing; clear the current draw surface to magenta, present, then draw one known triangle. Use the [EGL smoke harness](../../examples/validation/egl_smoke.cpp) offscreen as an independent correctness control, not proof of compositor success.
4. **Confirm/exclude**: check failed `eglMakeCurrent`/`eglSwapBuffers` and read `eglGetError` immediately; check FBO completeness, compile and link status, vertex attributes/VAO, output location, depth/cull/scissor/color masks and sRGB/color path. Isolate sampler completeness and feedback loops. Do not blame GPU vendor before evidence.
5. **Minimal fix**: one confirmed cause at a time. Do not insert `glFinish` everywhere as a production fix; use it only as a deliberate diagnostic with its cost recorded.
6. **Before/after**: same build settings, frame captures/readback and error stream; explain why the failure vanished. Reference C01/C02/C04/C05/C06 and the rule inventory IDs from the integrated catalog.
7. **Regression**: cold start, resize, background/foreground, surface recreation, unsupported-format fallback, sustained scene. Android presentation remains device-only.

Sources: [GLES 3.0 specification](https://registry.khronos.org/OpenGL/specs/es/3.0/es_spec_3.0.pdf), [EGL 1.5](https://registry.khronos.org/EGL/specs/eglspec.1.5.pdf).
