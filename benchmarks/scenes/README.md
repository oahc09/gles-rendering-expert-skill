# Eight deterministic GLES scene workloads

This is **actual rendering source**, not eight renamed static screenshots or synthetic
GPU traces. `examples/scenes/scene_lab.cpp` creates EGL + GLES 3.1, allocates real
resources, executes shaders/draws and reads an RGB8 framebuffer. The shared executable
has eight independently selected render paths. These are compact deterministic
workloads, not complete commercial games or physical-device performance acceptance.

## Reproduce

```sh
# Debian/Ubuntu dependencies: C++17 compiler, libegl-dev, libgles-dev, Mesa EGL runtime
EGL_PLATFORM=surfaceless LIBGL_ALWAYS_SOFTWARE=1 MESA_SHADER_CACHE_DISABLE=true \
  examples/scenes/run-host.sh S01 /tmp/S01.ppm 96 64 baseline
EGL_PLATFORM=surfaceless LIBGL_ALWAYS_SOFTWARE=1 MESA_SHADER_CACHE_DISABLE=true \
  python3 benchmarks/scenes/run.py --sweep --output /tmp/gles-scenes-verification
python3 -m unittest discover -s benchmarks/scenes -p 'test_*.py' -v
```

Optional `GLES_SDK_ROOT=/path/to/extracted/usr` locates local headers/libraries;
`GLES_SCENE_BUILD_DIR` selects the compiled binary directory. Pass that executable as
`run.py --binary /path/to/scene-lab`. Renderer CLI:
`scene-lab S01 output.ppm size instances baseline|control|degraded`.
Size range 16–2048, instance scale 16–4096; fixed seed 1337. Golden size is 96×96
and scale 64; sweep additionally executes 64×64/32 and 128×128/128. S08 uses four
times the instance scale; S02/S04 use scale/4+1 objects. Single representative
animation poses are fixed (skinning bone angles 0.3 and -0.6 radians, water phase
0.7/-0.4), making output repeatable rather than dependent on wall clock.

## Real work and controls

| Scene | Real GPU path | Control strategy | Deliberate regression |
|---|---|---|---|
| S01 cards | Instanced alpha blending, atlas and four dynamic updates | Partial 4×4 uploads instead of whole 16×16 atlas updates | Disable blending |
| S02 water | Color/depth FBO, refracted texture lookup, procedural normal/caustic overlay | highp vs mediump normal calculation | 12× refraction displacement |
| S03 soft particles | Instanced quads, streamed VBO, background depth sampling and soft intersection | Direct buffer upload vs orphan+subdata | Remove depth softening |
| S04 bloom | RGBA16F scene, half-resolution threshold, quarter-resolution blur, tone mapping and gamma | Remove blur consumption (an intentionally failed optimization) | Omit output gamma |
| S05 MSAA | 4× MSAA color/depth-stencil, depth-tested instancing, stencil writes, resolve | Depth prepass + transient depth/stencil invalidation | Disable depth test |
| S06 skinning | Two std140 UBO bones, vertex weighted skinning, instancing, buffer upload | Orphan+subdata vs direct UBO upload | Invalid bone rotation |
| S07 shared data | Compute fills SSBO and indirect command, storage+command barriers, indirect instanced draw | CPU-produced identical SSBO and command | Zero indirect instance count |
| S08 overlays | Hundreds of Gaussian splats, mediump alpha, transparency overdraw | Discard negligible Gaussian tails | Overweight opacity |

No strategy is declared faster. S04's control is **expected to fail** the visual
contract and is retained as an optimization-failure sample. All eight degraded
variants are also expected to fail image comparison. A process crash/GL error is
not counted as a successful negative image control.

## Goldens and evidence

`golden/*.ppm` are **real Mesa llvmpipe outputs**, with source/driver hashes in
`golden/manifest.json`. They are regression references, not an independent artistic
oracle or proof that an algorithm is physically accurate. All eight were visually
inspected: distinct nonblank card, water, particle, bloom, MSAA, skinned, compute-grid
and Gaussian images. `run.py` normally never writes goldens. Initial or intentional
reviewed changes require explicit `--accept-goldens`, which reports
`BASELINES_CREATED`, never a test PASS. A subsequent independent execution verifies
the frozen references. This flag is not a CI command.

Image contract: top-to-bottom RGB8; explicit shader gamma where used, **not universal
sRGB framebuffer or display HDR/WCG certification**. Allowed MAE ≤1.5/255,
maximum channel error ≤48/255 and ≤2% channels differing by >8/255. These declared
limits accommodate small software/driver differences; a different backend must be
reviewed, not silently regenerate references. Size-mismatched/truncated images fail.
The sweep tests execute/read back, but do not have independent size-specific goldens.

## Capability and resource limits

All paths require GLES3.1 because the executable includes S07; no version is inferred
from OS or GPU names. S04 separately checks advertised half-float renderability
extension and actual FBO completeness. S05 queries MAX_SAMPLES then validates the
actual 4× RGBA8/DEPTH24_STENCIL8 FBO. Unsupported prerequisites return nonzero,
`BLOCKED_BY_CAPABILITY`, not a fabricated SDR/CPU pass. A production fallback can
skip S04 for SDR or S07 for CPU simulation, but must label that as another path.

The scenes use bounded resource allocation and create/delete GL objects while their
context is current. Context loss, Android surfaces, ANGLE, Windows and embedded
backend coverage are **NOT_RUN** here. The executable uses EGL_DEFAULT_DISPLAY;
backend creation/selection belongs to the separate device lab, not renderer-string
substring inference.

## Physical-device measurement protocol (not executed)

For each device/backend/build/driver/resolution and scale: warm up at least 60 frames,
run ≥3 randomized A/B repetitions of ≥300 frames under stable recorded thermal/power
conditions, capture CPU submit separately from GPU timer queries (check disjoint),
p50/p95 frame time and dispersion, and platform bandwidth/fragment/tiler counters.
Trace identifiers and units must bind raw hashed artifacts. Record unsupported
counters as missing, never zero. Compare images before discussing performance.
Counterexamples: extra prepass geometry, added discard, orphaning overhead and
higher-precision register pressure may outweigh any benefit.

The present program emits one-shot `cpu_wall_including_compile_readback_ms`, which
includes compilation, driver initialization work and synchronous readback. It is
**not GPU time, steady-state frame time or a benchmark speedup metric**. GPU time
and bandwidth are null/NOT_COLLECTED; two real device configurations remain
BLOCKED_BY_HARDWARE. Feed actual target captures through existing
`benchmarks/gpu/capture.py`, not the software wall-time field.

Primary API basis: [GLES3.1 specification](https://registry.khronos.org/OpenGL/specs/es/3.1/es_spec_3.1.pdf),
[glMemoryBarrier](https://registry.khronos.org/OpenGL-Refpages/es3.1/html/glMemoryBarrier.xhtml),
[glBlitFramebuffer](https://registry.khronos.org/OpenGL-Refpages/es3.0/html/glBlitFramebuffer.xhtml).
