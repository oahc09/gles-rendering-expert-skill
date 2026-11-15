# Fixed-function interleaved software capture

The coordinator invokes only `shader_ab/optimization_pairs.Host.draw`, not
arbitrary commands, shaders or plugins. Two registered workloads are repeated:
sampling CSE on the ramp texture; pure compute-intermediate→fragment fusion at
frame1. Each has a positive optimized arm and deliberate wrong-output arm.

For each of four tracks: two warmup draws, followed by four AB pairs in strict
ABABABAB order, with three actual draw/readbacks per run. Both Mesa and ANGLE
execute104 draws/readbacks (8 warmup+96 recorded samples) per invocation. Each
sample is checked independently against the existing CPU golden, not merely
against the other arm. Vertex/fragment/compute source hashes, order, raw pixels
and recomputed quality results are retained. Invalid baseline, source/order
mismatch, malformed samples or execution failure fail the harness. Negative
candidate quality yields REJECTED_BY_QUALITY; a correct candidate yields only
INSUFFICIENT_EVIDENCE. Neither can enter performance acceptance.

```sh
python benchmarks/interleaved_capture/run.py --config DRIVER.json --output REPORT.json
python -m unittest discover -s benchmarks/interleaved_capture -v
```

Both saved driver reports HOST_PASS. Negative-control rejection is a harness
success, not optimization success. No GPU timer is collected; gpu_ms=null and
NOT_MEASURED are mandatory. CPU durations are not measured or used as GPU data.
The reused draw helper recompiles/setup/cleans resources per observation: this is
not a steady-state performance harness and requires redesign before timing.

This safe software schema is intentionally **not** the physical
`device_portability` protocol. It does not supply the latter's60 warmup frames,
30 GPU elapsed samples per run, thermal/frequency stability, physical identity,
reviewed capture provenance or independent physical performance acceptance.
No conversion fabricates those fields. Reports contain no local paths, host/OS
metadata or executable fingerprints. Driver processes must remain isolated.
