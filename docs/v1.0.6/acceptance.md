# v1.0.6 candidate acceptance and traceability

## Baseline and delivery decision

Exact107-line/10069-byte plan is [development-plan.md](development-plan.md); source identity/hash and the original gap ledger are in [baseline-and-gap.md](baseline-and-gap.md). Live baseline main `e8a4b9a94d69f30e897f31cc6a01f8dd7544305b` is the user's merge of PR3. Sole observed tag is `1.0.0` at `02942f16a86bf04077ca116c8c77aa85a5251a0f`. v103/104/105 are implemented candidates, **not accepted releases**. Unsubmitted predecessor work was absent. The current task uses one integration Draft PR with package-sized commits rather than five mutually dependent unmerged PRs; all packages retain explicit traceability. This changes review organization, not the single v1.0.6 target or acceptance bar.

Metadata remains **1.0.2**. No Actions run, tag, deployment, merge, new physical device, external model service or separate cloud environment was invoked. Manual-only workflow definition is extended, not automatically enabled. Current `release-gates.json` recursively depends on v105/v104/v103 and keeps release authorization false.

## Requirement → source → actual evidence → remaining

| W | Implementation | Evidence and interpretation | Remaining acceptance |
|---|---|---|---|
|0|baseline-and-gap; original plan; preserved gates|live GitHub/main/permissions + tag read, early source checkpoint|prior release dependencies remain|
|1|`examples/system_android/interop_roundtrip.cpp`|actual NDK API26 arm64 compile/link and independent ownership review; complete Vk→fence→GL→fence→Vk source|no physical AHB/fence/512-pixel roundtrip executed|
|2|`examples/system_android/multi_surface.hpp`, Java app/JNI|actual4software pbuffers,40serial+80worker frames, pixel checks, two-lab lifetime, retired-surface isolation,7controlled generations; Java/API35 +NDK shared library|APK assembly attempted and failed AGP dependency resolution; no APK/device lifecycle/reset/Perfetto|
|3|`examples/system_scenes/simulation.cpp`|particles/boids/waves, deterministic CPU/GPU/negative comparisons; real readback and GPU-output draw, CPU fallback|software driver only; no physical cross-driver validation|
|4|`benchmarks/driver_compat`|actual software probe plus exact identity/extension/expiry tests|Mali/Adreno/PVR/Vivante/ANGLE remain unavailable; confirmed-driver-issue list intentionally empty|
|5|`examples/system_scenes/effects.cpp`|glass/sand/particles actual multipass images, weighted OIT and sorted comparison, refraction/thickness approximation|not production fluid physics/physical light transport; physical MSAA/driver/performance unverified|
|6|same effects module, budgets/dependencies|Forward+ tile list and all-lights reference; two orthographic depth maps/PCF, water depth and approximate caustics; real browser slider via local native rendering|not production stabilized CSM or full depth-clustered lighting; budgets are logical estimates|
|7|`examples/texture_pipeline`; existing Android SurfaceTexture Activity +new guard|real libktx UASTC LDR runtime transcode, ASTC/ETC2/RGBA softwareGL sampling/readback, sRGB format checks, malformed/unsupported resource negatives; Java guard wired before producer|not arbitrary KTX/HDR loader; no Android video execution; protected input rejected rather than exposed|
|8|`examples/system_scenes/precision.cpp`, numeric oracle|12numeric/image positive-negative groups isolating storage/ALU/blend/attachment/transfer; old precision suites retained|CPU expression oracle is not exact GPU spec; physical FP16/mediump distribution unknown|
|9|`benchmarks/reducer`; `examples/repro/state_fixture.cpp`|10authored missing-identifier compiler faults, bounded domain-preserving ddmin,3repeats each,10fixed compiles; actual missing-FBO→complete/pixel snapshot|not ten vendor bugs; not semantic global minimum; original-driver replay unavailable|
|10|142-case corpus/scorer, manual workflow, research ledger, recursive gate|exact112prefix +30authored hard cases; infrastructure tests; no-adapter142 probe exits2; date-bound official-source radar|zero live provider calls; annotations require independent model evaluation; no release|

## Detailed evidence

- `system-validation.json`:7 actual host compile/run and Android compile/link checks, with source/binary/log identities.
- `evidence/legacy-android-source-compile.json`: actual compilation of updated prior Android code plus native examples. This is not an APK.
- `benchmarks/system_scenes/software-validation.json`:57 report rows from69 executable calls;5effects,12precision pairs,27simulation cases. Calls/rows are not distinct requested features. Exact shader and image hashes are retained.
- `benchmarks/system_scenes/{shader-validation,android-compile-validation,browser-validation,interaction-validation}.json`: standalone shader compilation,3NDK source links and actual localhost HTTP/browser slider checks. Browser screenshots are internal only and excluded from repository/Library backup; native GL goldens and heatmaps are deliverable artifacts.
- `benchmarks/texture_pipeline/evidence/report.json`: actual runtime transcoder and three software GL paths. Host wall-time/RSS is **not** mobile GPU performance/VRAM/power. `source-validation.json` records Java/GLSL checks. Rejection tests include synthetic header mutations explicitly labeled, not real HDR device captures.
- `benchmarks/reducer/evidence/report.json`: exact compiler diagnostic trials; partial/unknown/crash outcomes cannot establish minimality.
- `evidence/test-suite.json` and log hashes: full current unit/contract suite; count summarized in final receipt after source freeze. These infrastructure tests do not constitute live Agent pass rates.
- `evidence/rules.json`:112 normalized input contracts across30distinct rules, not112rules or source compiler tests. `evidence/shaders.json`:16actual original compiler/link positive-negative controls.
- `evidence/provider-blocked-final-lf/summary.json`: real no-provider probe for142cases, zero responses. Prior600-second host workload and synthetic1800-second timelines remain historical v105 evidence, not rerun physical30-minute acceptance.
- `evidence/apk-assembly.log` and `.exit`: current new Android app assembly failure while resolving AGP8.7.3. No fabricated APK or runtime success.

## Defects found and corrected in this iteration

Independent W1/W2 review reproduced premature EGL display termination when two labs coexist and resurrection of retired surfaces across group rebuild. Shared display leasing and permanent retired entries were patched and actual software regressions rerun. Reducer review found unknown deletion results falsely establishing minimality; timeout/crash/I/O failures now invalidate that conclusion, tool version probing is bounded, and fixture path escapes are rejected. Parent review tightened texture capability metadata and LDR input/output contracts. New golden manifests now require exact five-image inventory and metadata, avoiding the prior generation's omitted-entry weakness.

Review is scoped engineering QA, not a hardware certification. The final source manifest and outside-repository independent review bind the inspected candidate; successful bookkeeping is never reported as full release acceptance.
