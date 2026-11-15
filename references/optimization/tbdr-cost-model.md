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

## Explicit lifecycle model v1

Supply `lifecycle` to select the event model instead of legacy supplied pass counts.
Each attachment declares id, dimensions, format, samples and optional
`initially_defined`. Events are begin(load/clear/discard per attachment), draw
(explicit full_overwrite or partial), switch(same attachment set/new FBO name),
resolve, end(store/discard per attachment), and external consume outside a pass.

The state machine rejects nested/unterminated passes, undefined loads, partial
writes to undefined contents, discarded external consumption and single-sample
resolve. Every logical transfer is attributed to its event. Texture sample
estimates are added separately. Unknown formats/texel sizes propagate UNKNOWN.

`driver_condition.fbo_switch` defaults to unknown. Unknown/flushes_tile includes
one full logical spill/reload of defined attachments at each switch; preserves_tile
omits that conditional transfer. Non-unknown conditions require explicit device,
GPU, driver, backend and source scope. These declarations are not authenticated:
the report explicitly says NOT_AUTHENTICATED. No default tile size is assumed.

This is a finite logical envelope under declared events, not a universal bus
upper bound. No tile residency, compression, cache transactions or physical DRAM
is inferred. Draw coverage is a caller contract, not derived from geometry.
Resolve is separately counted and does not imply source invalidation. The model
does not represent arbitrary partial subresources, aliased memory, implicit
driver passes or hardware counters. Calibration remains optional and requires
comparable scoped counters; no mobile device is claimed tested.

Reproduce the executable boundary/negative cases:
`python3 -m unittest discover -s tools -p test_attachment_lifecycle.py -v`.
