# Production pipeline runtime lab (C++17 / GLES)

This adds a separate executable and does not modify old scene APIs. It reuses
`examples/system_scenes/common.hpp` / `examples/scenes/scene_lab.cpp` for EGL,
shader compile/link, FBO ownership, GL error handling and P6 readback.

## Reproduce on Linux Mesa

Requires C++17, EGL/GLES development headers and libraries and a usable EGL driver
(e.g. `libegl1-mesa-dev`, `libgles2-mesa-dev`, `libgl1-mesa-dri`).

```sh
examples/pipeline/build.sh
export EGL_PLATFORM=surfaceless LIBGL_ALWAYS_SOFTWARE=1 MESA_SHADER_CACHE_DISABLE=true
python3 benchmarks/pipeline/runtime.py
python3 benchmarks/pipeline/runtime.py --mesa-version-matrix
python3 -m unittest discover -s benchmarks/pipeline -p test_runtime.py -v
```

For a locally extracted SDK set `GLES_SDK_ROOT` before building and export
`LD_LIBRARY_PATH=$GLES_SDK_ROOT/lib/x86_64-linux-gnu` before running. Build output
is `/tmp/gles-pipeline-lab/pipeline-lab`, overridden by `GLES_PIPELINE_BUILD_DIR`.
The build script uses the Linux EGL runtime SONAME, allowing extracted SDKs whose
unversioned EGL symlink points outside the SDK. For another platform compile
`pipeline_lab.cpp` with its standard EGL/GLES linker flags.

Run a single capture with `pipeline-lab S03 capture.ppm injected`. A success JSON
means its **runtime assertions** passed; it does not by itself prove pixel
correctness. `runtime.py` additionally compares all 32 captures to independent
CPU numeric oracles and requires all six deliberately broken color images fail.
Unknown modes/scenes and unavailable capabilities exit nonzero.

| Scenario | Actual runtime work | Negative test |
|---|---|---|
| S01 | Link 300/310/320 GLSL when context supports them | Compiler rejects required nonexistent extension; variant checker separately rejects version/feature mismatches |
| S02 | Retrieve and reload driver binary; three stale identities recompile | Corrupt binary fails load, source fallback draws successfully |
| S03 | Reflect std140 size/member offsets; bind real UBO + sampler | Host offset 12 versus reflected 16; sampler unit 1 versus required 0 rejected and repaired |
| S04 | Four-FBO bloom chain and readback | Omitted bloom fails oracle; graph cycle/read-before-write negatives are in graph checker |
| S05 | Compute writes SSBO, vertex fetch consumes same buffer | Missing vertex-attrib barrier rejected before consumption, then correct barrier issued |
| S06 | Blend in RGBA8 MSAA renderbuffer, resolve, tonemap | Unequal proposed resolve dimensions rejected before GL call |
| S07 | Two premultiplied glass/particle layers | Repeated alpha multiplication fails oracle |
| S08 | sRGB input decode, linear lighting, sRGB FBO encode | Extra gamma fails oracle |
| S09 | Two material parameter sets; swapped ABI shader reflected | Incompatible roughness offset 20 versus 16 rejected before binding |
| S10 | Source compile/link and binary-load/fallback host timing | Corrupt-cache and source-invalidation cause classified fallback |

C01-C06 are six frozen independent CPU-reference color/material images. C03 adds
actual RGBA16F HDR storage and tonemapping. C05/C06 visual injections also change
a material parameter / omit tonemapping so the image comparator itself is tested.

GLES3.0 paths never dispatch compute. The Mesa override matrix executes S01/S03/
S05/S06/C01/C03 on 3.0/3.1/3.2 and requires S05 to be blocked on 3.0. This tests
version-safe routing on **one driver**, not three physical devices.

## Evidence boundaries

- The committed software report is llvmpipe correctness evidence, not physical
  GPU speed, bandwidth, power, startup guarantees or display calibration.
- Timings are host wall clock, not GPU timestamps. No claim of cold driver cache
  is made, even when `MESA_SHADER_CACHE_DISABLE=true` is set.
- Cache is an in-memory teaching roundtrip, not production persistence/security.
  Exact source, macro, compile-option, vendor/renderer/version/driver and sorted
  extension identities gate reuse. A differing envelope falls back to source.
- Missing barriers and invalid resolves are diagnosed **before** undefined GL
  consumption. Running undefined code and obtaining the right image proves nothing.
- MSAA tests full-coverage premultiplied blending and resolve. Polygon-edge sample
  coverage and display-side blending appearance need separate physical-backend
  capture and are explicitly not certified here.
- Binary format support and RGBA16F renderability are queried; unavailable
  capabilities fail explicitly instead of silently substituting a CPU renderer.
