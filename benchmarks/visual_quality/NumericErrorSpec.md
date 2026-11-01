# NumericErrorSpec v1 — exact experiment, not universal precision marketing

| Field | Contract |
|---|---|
| Reference expression | Start at 16; add rounded `0.001` 1024 times; round each operation using Python `struct` binary32 (`f`) or binary16 (`e`) |
| Reference implementation | `run.py::oracle`; expected binary32=17.0234375, binary16=16.0 |
| Actual GPU experiment | `examples/precision/precision_lab.cpp` compute shader/SSBO readback; highp, explicit pack/unpack half quantization and mediump measured independently |
| Acceptance | highp absolute error≤0.002 versus binary32 reference; explicit half result equals binary16 reference; mediump output is reported, not assumed equal to either |
| Device identity | Each capture retains renderer/version, mediump range/precision query; source/runner/binary hashes in report |
| Numerical meaning | Explicit half quantization is not proof of native FP16 ALU execution, register savings or speed |
| Visual reference | Frozen24 P6 RGB8 images,8 scenes×3 fixed times, seed1337; metadata/hash/dimensions validated before comparison |
| Color domain | Encoded RGB8; HDR signal is tone-mapped to SDR, not WCG/PQ display capture or calibrated nits |
| Error | Per-channel absolute error in 8-bit units [0,255], multiscale MAE and local8×8 SSIM per `compare.py`; no unimplemented perceptual DeltaE claim |
| Region masks | Reference-derived edge, shadow, glow and P06 transparent masks in `compare.py`; separate region tolerances in `thresholds.json`; empty masks are NOT_APPLICABLE |
| Temporal tolerance | Three fixed samples, compare reference/candidate temporal deltas; constant spatial bias and alternating injected flicker tested separately |
| Rejection | P01/P03 mediump and P03 reduced-resolution outputs fail; retain highp/baseline, do not relax thresholds to pass |
| Unverified | Physical-driver precision/visual tolerances, sustained flicker on display, GPU timing/energy and art signoff |

The numerical and image gates are both necessary for this experiment, neither
sufficient for physical performance acceptance. `quality_and_pareto` keeps missing
p95 time, power, memory and thermal evidence null/NOT_MEASURED. A visually safe
software candidate is not an optimized device configuration.
