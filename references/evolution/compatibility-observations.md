# Compatibility observations — 2026-11-01

* `VERIFIED_SOURCE`: Khronos lists Oct 25 GLES 3.0 submissions 1131/1132 for NXP i.MX 8M Quad/Plus, Vivante GC7000 revisions 6214/6204 and specific Mesa etnaviv configurations. Add an embedded-Linux compatibility target; **do not** infer support on all Vivante devices or claim local tests.
* `VERIFIED_SOURCE`, historical context: Oct 1 NVIDIA Windows-on-Arm GLES 3.2 submissions show that OS/CPU architecture does not determine GPU vendor. Date lies outside this 30-day window.
* `VERIFIED_SOURCE`: Filament 1.78/1.79 material/API evolution merits revision-keyed shader/material caches. It does not alter GLES GLSL version rules.
* `REJECTED` as GLES feature evidence: October Vulkan CTS release tags. Track GLES CTS independently; latest inspected GLES patch is July 21 and therefore historical here.
* `UNVERIFIED` on local hardware: ANGLE backend/native-driver equivalence, native-buffer formats, mobile counters, HDR output and protected-video behavior. Query actual capabilities on each path.

Sources and original timestamps are recorded in [evidence.csv](../research/2026-11-01/evidence.csv). These are public-source observations, not a device-support certification by this repository.
