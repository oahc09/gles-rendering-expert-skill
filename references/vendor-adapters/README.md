# Conditional vendor adapters

Four explicit adapters retain Mali/Immortalis, Adreno, PowerVR/IMG and Vivante/etnaviv coverage. Each has 11 scoped hypotheses: tile load/store, GMEM-like on-chip storage, LRZ/early-Z, HSR, tile budget, depth prepass, MSAA, fetch/PLS, texture bandwidth, blend/overdraw and target switches. **Mechanism labels do not imply that all vendors expose Qualcomm GMEM/LRZ or IMG HSR under those names.** Applicability needs the exact architecture, driver and profiler definition.

Each entry declares a condition, metric family, counterexample, fallback and null measured evidence. The aliases are not real vendor counter IDs. Resolve IDs/units from the current official profiler for the actual device; never manufacture a missing hardware counter. Existing vendor-specific rules remain the detailed architecture references; these adapters constrain experimental claims instead of replacing legitimate old scenarios.

Use scene S01/S08 for blending, S02/S04 for target traffic, S03/S06 for geometry/streaming, S05 for MSAA/depth and S07 for compute synchronization. Record real captures through `benchmarks/gpu/capture.py`, triage exported rows through `benchmarks/traces/analyze.py`, then test a single-variable A/B with fixed seed/build/thermal state. No adapter asserts that an optimization is always faster or that a software pbuffer measures mobile bandwidth.
