# GPU resource lifecycle and memory-pressure triage

## Evidence boundary

Record logical asset ID, owning thread/share group, context generation, object kind,
allocation estimate, last consumer and fence state. GLES has no portable exact
VRAM-residency query: width × height × format bytes is an **engine allocation
estimate**, excluding alignment, tiling, compression, driver caches and hidden
copies. Zero application handles after cleanup is not zero driver memory.

The W4 [executable](../../examples/resource_pressure/stress.cpp) and
[runner](../../benchmarks/resource_pressure/README.md) reuse the previous EGL harness.
Their stress report separates actual software GL results, synthetic Pending/Failed
policy inputs, controlled context replacement and missing device evidence.

## Ownership, submission and cancellation

- **MUST (API)**: map/use buffers according to access and synchronization rules.
  Never upload from a still-mapped PBO; never consume unfinished readback storage.
- **SHOULD (engine)**: use owner-thread deletion queues and generation-tagged logical
  handles. A replacement context can reuse numeric names; stale names are not
  automatically valid assets. Retain CPU descriptions needed for reconstruction.
- **SHOULD (engine)**: a canceled request suppresses publication, but cancellation
  does not undo commands already submitted. Keep its slot unavailable until its
  fence completes; handle WAIT_FAILED/context loss as recovery, not success.
- **MUST (shared-context visibility)**: preserve the producer/consumer ordering and
  relevant object visibility operations. A producer flush plus synchronized CPU
  publication and consumer wait/rebind is the established cross-context pattern.
  This new stress test is single GL-owner thread; use the prior shared-context
  regression separately rather than claiming new cross-thread GPU coverage.

Specification sources: [GLES 3.0.6 §§2.10, 5.2 and appendix D](https://registry.khronos.org/OpenGL/specs/es/3.0/es_spec_3.0.pdf),
[EGL 1.5 context/surface lifecycle](https://registry.khronos.org/EGL/specs/eglspec.1.5.pdf).

## Budget and pressure policy

Keep an essential/pinned tier and an evictable LRU tier. Reject or defer requests
that exceed the budget when no safe victim exists; never silently exceed a claimed
hard estimate. Eviction is permitted only after all consumers release ownership.
A low-memory signal should drop optional residency, cancel unneeded publications
and retain reconstruction metadata. An upload burst needs bounded in-flight slots
in addition to the texture budget. Report render-target formats and mip/sample
counts separately when estimating a production allocation; this tiny fixture uses
base-level RGBA8 and no multisampling and does not generalize its estimate formula.

## AHardwareBuffer / external-image recovery

Reuse [v1.0.4 native AHB case](../../examples/android_cases/surfacevideo/src/main/cpp/ahb_texture.cpp)
and [Java external producer](../../examples/android_cases/surfacevideo/src/main/java/org/example/gleslab/ExternalSurfaceActivity.java).
Keep buffer reference ownership, EGLImage lifetime, imported GL texture ownership,
producer/consumer fence ownership and surface lifecycle distinct. Cross-compilation
cannot validate device-specific allocation/import formats or asynchronous safety.
AHardwareBuffer lifetime contracts are documented by the
[Android NDK reference](https://developer.android.com/ndk/reference/group/a-hardware-buffer).
The new host stress does not emulate AHB and does not upgrade that device gate.

## Diagnose, then verify

1. Symptom: repeatable growth, stale texture after resume, busy ring or map failure.
2. Capture real renderer/driver, active generation, live handle counts, estimated
   texture bytes, submission/completion timeline, cancellation and error logs.
3. Separate app-owned leaks from driver caching and actual system pressure.
4. Reproduce with fixed asset IDs and 100 scene cycles, preserving raw observations.
5. Compare before/after handle slopes and exact readback correctness. For a device
   leak conclusion also collect platform memory/driver evidence under the same
   workload; no unsupported conversion of object counts into physical bytes.
6. Real Android context loss, surface callbacks and native-fence tests require a
   device. Until exercised label `NOT_RUN_DEVICE`, not PASS from simulated teardown.
