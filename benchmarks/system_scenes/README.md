# v1.0.6 system rendering / compute lab

Owns W3, W5, W6 and W8 incremental examples. The existing `scene_lab.cpp` is included through `common.hpp` with its entry renamed; original examples, thresholds and goldens are untouched. Image comparison imports v1.0.5's multiscale MAE/SSIM/region implementation.

## Run (current software-driver setup)

```sh
export GLES_SDK_ROOT=/tmp/gles-local-deps/root/usr
export LD_LIBRARY_PATH="$GLES_SDK_ROOT/lib/x86_64-linux-gnu"
export EGL_PLATFORM=surfaceless LIBGL_ALWAYS_SOFTWARE=1 MESA_SHADER_CACHE_DISABLE=true
examples/system_scenes/build.sh
python benchmarks/system_scenes/run.py --output /tmp/gles-system-check
python benchmarks/system_scenes/validate_shaders.py
python -m unittest discover -s benchmarks/system_scenes -p 'test_*.py' -v
python benchmarks/system_scenes/validate_http.py
python benchmarks/system_scenes/interactive.py --port 8766
# Open http://127.0.0.1:8766 and move the glass slider.
```

CLI contracts:

- `simulation particle|boids|wave STEPS gpu|cpu|degraded OUTPUT.json`: deterministic seed1337; bounded1..1000 steps. GPU path produces both complete numeric states and `OUTPUT.json.ppm` using the actual compute output. CPU path has no GL context requirement, making the simulation usable by GLES3.0 clients; it does not silently replace a failed GPU test.
- `effects glass|sand|particle|shadowwater|forwardplus OUTPUT.ppm baseline|degraded|sorted|fallback TOUCH`: touch in[-1,1]. Sorted transparency and its `fallback` alias are actual ES3.0 RGBA8-only paths for sand/particle. OIT probes RGBA16F framebuffer completeness; unsupported capability exits3 with that fallback recommendation. Forward+ fallback is a real all-lights GLSL ES3.00 uniform-array path, without compute or SSBO allocation.
- `precision GROUP positive|negative OUTPUT.ppm`: twelve isolated pairs below.

## What is actually implemented

| Scene | Actual passes / mechanisms | Intentional limitation |
|---|---|---|
| glass | background/depth; front/back orthographic thickness; screen refraction and absorption | analytic single convex volume, not general mesh/thick multi-layer transport |
| sand | weighted accumulation RGBA16F; revealage RGBA8; composition, plus sorted fallback | elongated grain sprite visual, not fluid/granular physics |
| particle | weighted blended OIT with two geometry passes and real blending | approximate ordering, no opaque mesh occluder or MSAA validation |
| shadowwater | two rendered depth maps, 3x3 PCF, screen depth attenuation and procedural caustics | fixed orthographic cascades, not production stabilized CSM or physically traced caustics |
| forwardplus | compute tile/light lists -> fragment SSBO reads; all-lights reference | planar circle/tile culling, not depth-clustered 3D culling |

All five have frozen actual Mesa images, interaction changes and visible fault injections. Forward+ must match its all-lights path; sorted transparency differences are recorded, **not assumed equivalent to OIT**. P5/P6 do not claim a full production renderer merely from a screenshot.

Budgets in `budgets.json` enumerate logical formats/bytes, instance counts and passes, with physical memory, GPU timing, power and tile load/store measurements explicitly null. `dependencies.json` documents actual producer/consumer hazards. The three simulations use separate CPU/GPU implementations and ping-pong resources; Boids includes cohesion/alignment/separation, water uses a 16x16 periodic finite-difference height equation, particles include gravity and wall collision. Workload sizes are deliberately bounded for correctness.

## W8 twelve precision pairs

| Group | Axis | Positive | Negative |
|---|---|---|---|
| 1 | input storage | RGBA32F small residual | RGBA16F quantization |
| 2 | input storage | RGBA32F residual | RGBA8 quantization |
| 3 | input encoding | actual SRGB8_ALPHA8 decode | RGBA8 missing decode |
| 4 | ALU | highp 1024-addition accumulation | explicit half packing each addition |
| 5 | ALU | highp large-number subtraction | explicit half input conversion to subtraction |
| 6 | ALU | normalized specular direction | quantized normal |
| 7 | blend | straight RGB + SRC_ALPHA | wrongly use ONE |
| 8 | blend | premultiplied RGB + ONE | double-multiply via SRC_ALPHA |
| 9 | blend color space | blend linear then encode | blend encoded values |
| 10 | attachment | RGBA16F HDR before tonemap | RGBA8 HDR clipping |
| 11 | attachment RGB | exact 1/1024 additive increments into RGBA16F | RGBA8 loses increments |
| 12 | attachment alpha | same exact increment in alpha channel | RGBA8 alpha quantization |

`numeric_reference.py` supplies independent CPU positive-expression oracles with MAE<=1.5 and max channel error<=4 in encoded RGB8. These tolerances account for rounding/transcendental differences; CPU round-to-nearest is not declared the GLES blend specification. Negative pairs must also exceed the existing visual thresholds. Explicit binary16 packing is not a claim that mediump always maps to FP16; v1.0.5's actual qualifier probes remain the relevant separate test. Positive and negative captures are retained under `precision-captures/`.

## Evidence / acceptance meaning

`software-validation.json` contains 57 result rows from 69 executable invocations: 18 advanced-scene comparisons, 12 precision pairs (24 invocations), 27 simulation cases (3 kinds x3 step counts xCPU/GPU/injected fault). It includes raw numeric state output and commands. A harness PASS means good cases match and faults are detected—not that sorted OIT is identical, optimizations are faster, or all GPUs are supported.

`shader-validation.json` compiles exact runtime-dumped GLSL with glslang, deduplicates identical stage SHA values, and reports both unique and total stage counts. The software execution independently compiles/links actual programs. `android-compile-validation.json` is actual NDK arm64 API26 strict compilation/linking, not device execution. `capability-fallback-validation.json` additionally exercises actual Mesa GLES3.0-restricted contexts for both sorted transparency and all-lights rendering, rejects compute in that context, and exercises an explicitly synthetic missing16F hook. This is not physical ES3.0 hardware evidence.

`interaction-validation.json` proves real localhost HTTP inputs produce distinct native-rendered PNGs and rejects invalid input. Initial Chromium attempts were blocked by IPC restrictions (reviewed escalation also failed before execution). A separately identified, already installed current-environment WPE WebKit launcher then ran normally without elevation or sandbox-disabling flags. `browser-validation.json` records the actual slider keyboard input, changed native-rendered image, browser version and absence of page errors. Before/after browser screenshots are internal inspection only in `/tmp/gles-system-interaction/`; they are excluded from source/Library delivery. Their hashes remain in the test report. No external task/service was created.

Golden creation requires explicit `--accept-goldens` and returns BASELINES_CREATED_NOT_VALIDATED. Normal tests enforce the exact five-scene inventory, per-image capture metadata, actual PPM dimensions, color/seed/interaction contract and comparison-configuration hash before execution; they never silently replace reference images. Manifest preserves original producer hashes; optional shader dumping later changes helper source without changing pixels. Actual capture metadata includes renderer, seed, interaction and explicit RGB8 output contract. The author inspected the five-panel reference contact sheet; independent art and physical-device reviews remain unrun.

## Remaining boundaries

Software Mesa is L1 only. No Mali/Adreno/PowerVR, physical ES3.0 device, Android runtime, HDR/WCG display, production MSAA/OIT integration, GPU performance or power result is claimed. Selecting a fallback is explicit and never changes an unsupported GPU test into a GPU PASS. Check `references/playbooks/system-effects.md` for official specification and primary algorithm references.
