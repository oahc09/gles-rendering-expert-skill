# Logical traffic envelope, not DRAM prediction

Run `python tools/estimate_gpu_cost.py benchmarks/gpu_cost/example.json`.
The attachment upper envelope is width × height × bytes per texel × sample count ×
2 × declared load/store passes. Initial clear and final invalidate each eliminate
one logical transfer; a separately materialized resolve adds multisample read +
single-sample write. These are explicit **model assumptions**, not driver promises.
The lower envelope is zero because cache/tile residency/compression can avoid
external traffic. Unknown formats keep the upper total unknown. No fixed tile size
or vendor behavior is assumed. External consumers prohibit invalidation.

Texture fetch upper bytes use a caller-supplied total sample count and logical
bytes per sample (including filtering taps); they do not estimate cache-line or bus
traffic. Blend read/write, transaction amplification, texture compression, implicit
resolves, hidden passes and residency must be separately measured. FBO changes do
not prove a flush: `passes` must reflect an explicitly assumed load/store model.

Calibration accepts only a comparable **logical** counter, scoped to device, GPU,
driver, backend and raw trace. Relative error is unknown for a zero denominator.
Actual DRAM counter comparison requires a validated device-specific conversion,
which this tool intentionally does not implement. All supplied cases are synthetic.
