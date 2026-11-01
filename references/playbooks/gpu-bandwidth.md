# GPU bandwidth / W3 experiment protocol (C06–C08, C12)

**Status: BLOCKED_BY_HARDWARE.** These experiments are designs, not measured speedups. The software EGL harness checks API correctness only. Preserve unfavorable results. Each scene uses the same deterministic camera, geometry, resolution, input seed and frame count for A/B; change one factor at a time. Compare images before interpreting speed.

## Collect before optimizing

Capture device/model, SoC/GPU, OS build, driver, GL/EGL snapshot, API/backend, build SHA, resolution/refresh rate, thermal state and power policy. Warm to stable thermal behavior, alternate A/B order, repeat independent runs; retain frame-time samples (not only mean), CPU submission time, GPU timer samples (discard disjoint queries) and profiler raw trace with counter units. Report p50/p95/p99 and run-to-run spread or confidence interval. If bandwidth counters are unavailable use `null`; an estimate from bytes/pixel is not a hardware counter.

| ID / factor | Baseline A → variant B | Correctness test | Counters / possible regression and fallback |
|---|---|---|---|
| GPU01 clear/load/store | Preserve attachment then overwrite → full clear at pass start | Identical initialized output; respect scissor/masks in both | External read/write bytes, tiles, GPU time; partial redraw still needs preserved pixels, retain load when content survives |
| GPU02 depth/stencil invalidate | Store dead depth/stencil → invalidate only after final use | Color readback identical; later depth read intentionally forbidden | Store bytes/transaction counters; never invalidate sampled/preserved attachment; keep it if later used |
| GPU03 MSAA resolve | Offscreen multisample then blit → supported multisampled-render-to-texture path | Edge sample coverage, FBO completeness, matched format/size | Resolve/store cost, tile spills, time; extension-dependent, high sample count may regress; lower samples or core blit |
| GPU04 alpha discard | Alpha-tested foliage → comparable alternative (coverage/prepass) | Alpha edges and depth ordering within defined tolerance | Fragment invocations, early/late-Z kills, texture reads; prepass repeats work; retain discard when cheapest correct path |
| GPU05 draw order | State-sorted opaque → coarse front-to-back | Same final pixels; transparency still separately ordered | CPU sorting/submission, shaded fragments, early-Z/HSR, bandwidth; extra state churn or effective HSR may erase benefit |
| GPU06 FBO switches | Interleaved targets → grouped complete passes | No dependency violation, same postprocessing result | Tile load/store, external bytes, CPU/GPU time; grouping must respect producer-consumer order |
| GPU07 compression | RGBA8 textures → supported ETC2/EAC or probed ASTC | Error metric and edge inspection at matched mip levels | Texture bytes, cache misses, GPU time, package/transcode cost; quality or unsupported format requires fallback |
| GPU08 precision | highp calculations → bounded mediump subset | Stress large coordinates/tiny differences/HDR, numerical max error | Shader register pressure, occupancy, ALU/GPU time; keep highp where range or error requires; no assumed FP16 speedup |
| GPU09 branchless | Uniform/coherent branch selecting one texture → unconditional two samples + mix | Same intended colors including LOD/derivative behavior | Texture requests/cache/bandwidth, ALU/time; duplicated fetches often outweigh branch removal; restore branch when measured worse |

## Vendor interpretation (CONDITIONAL, not MUST)

* Mali: architecture-generation-specific counters and tile behavior; use [Arm best practices](https://developer.arm.com/documentation/102643/latest/) and the matching Streamline counter documentation. Counter access was not available here. A smaller attachment may improve bandwidth without proving ALU savings.
* Adreno: test GMEM vs direct/system-memory behavior and available LRZ/early-Z counters using the actual profiler/device documentation. Do not assume every draw uses GMEM or every driver exposes equivalent counters. MSAA attachments can change tile occupancy.
* PowerVR: [HSR guidance](https://docs.imgtec.com/performance-guides/graphics-recommendations/html/topics/z-pre-pass-and-powervr.html) gives a counterexample to universal Z-prepass recommendations. [HSR efficiency](https://docs.imgtec.com/tools-manuals/pvrtune-manual/html/pvrtune-manual/topics/counters/hsr-efficiency.html) must be interpreted with scene opacity; low rejection is normal when overdraw is low. Do not apply opaque HSR assumptions to blended/discard-heavy geometry.
* Vivante / Mesa etnaviv is a compatibility target, not evidence that Mali/Adreno/PowerVR heuristics transfer.

Use [gpu-result-template.json](gpu-result-template.json). Fill `status` with `MEASURED` only with actual device evidence. Rejected performance hypothesis is an acceptable measured result. If correctness fails, speed is not an accepted optimization.
