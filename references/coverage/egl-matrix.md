# EGL lifecycle closure: actual host vs platform gaps

Normative source: [EGL1.5 specification](https://registry.khronos.org/EGL/specs/eglspec.1.5.pdf).
The demo at `examples/closure/egl-lifecycle/run.py` uses the existing trusted
software EGL loader, not a synthetic state fixture. Both Mesa and ANGLE actual
runs pass finite lifecycle checks:

- Initialize/display/config discovery; original4×4 and second8×8 pbuffer.
- Shared GLES context reads the original context's texture bytes; independent
  context cannot see the texture name. Shared object visibility is not inferred.
- Concurrent second-thread acquisition of current context fails EGL_BAD_ACCESS;
  a distinct shared context on its own pbuffer succeeds in another thread and
  reads the expected pixel. Synchronization uses explicit glFinish and join.
- Pause/unbind/resume; pbuffer swap; invalid surface and attribute errors followed
  by valid MakeCurrent recovery.
- Resize means destroy an unused immutable pbuffer and create16×16 replacement;
  actual width query and pixel readback verify it.
- Surfaceless MakeCurrent, EGL1.5 fence/client wait/destroy, texture-backed EGLImage
  create/destroy and invalid-image-target negative.
- Restore original context and destroy extra contexts/surfaces before host cleanup.

Pbuffer swap is **not** native-window presentation or frame-timing evidence.
Injected bad handles/attributes are **not** real compositor surface loss or GPU
context reset. Texture-backed EGLImage creation is **not** Android AHardwareBuffer
or DMA-BUF native import/export. Thread joins are not throughput measurements.

Android Java+NDK actual installation/activity/surface lifecycle, Windowsx64/ARM64,
GBM/Wayland/X11 native windows, real context reset and platform native image paths
remain NOT_RUN/BLOCKED_BY_HARDWARE. Existing platform modules may be reused later;
this finite host demo does not pretend to supply missing devices/build artifacts.

```
python3 examples/closure/egl-lifecycle/run.py --config DRIVER_JSON --output REPORT_JSON
python3 -m unittest discover -s benchmarks/coverage/egl -v
```

Safe public evidence contains error codes/pixels/source hashes without raw
platform identities, executable/library fingerprints or local paths.
