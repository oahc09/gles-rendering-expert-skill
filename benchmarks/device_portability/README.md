# v1.0.9 device portability protocol

`python3 benchmarks/device_portability/protocol.py capture.json --artifact-root captures`
validates captured records and summarizes interleaved A/B distributions. It does not
run devices or authenticate provenance. It deliberately returns
PAIRED_CAPTURE_REVIEW_REQUIRED, never verified improvement. Physical device data is
NOT_RUN in matrix.json; software tests are infrastructure fixtures only.

Capture exact device model, GPU, driver, OS, backend and API; fix workload and both
build SHAs; warm up at least 60 frames; collect >=4 alternating A/B pairs with >=30
valid GPU elapsed samples per run. Reject disjoint timers, missing clocks, unstable
thermal state or >2 C drift. Retain raw trace hash, frequency state and independent
image-quality review. CPU time and GPU time may overlap and cannot be summed.
Compare only within identical groups; a good result on one GPU never licenses a
vendor-wide rule. Use baseline if quality fails or measured confidence is absent.
The host adapter/device snapshot infrastructure remains benchmarks/device_lab/.

## Executable scene collection and grouped quality gate

`scene_collector.py` connects the actual three-pass candidate-graph replay to
hash-bound capture records. It does not wrap a static fixture as an executed scene.
Run one collector process per software implementation:

```
python3 benchmarks/device_portability/scene_collector.py collect --config MESA_JSON --backend mesa-software --output-dir captures
python3 benchmarks/device_portability/scene_collector.py collect --config ANGLE_JSON --backend angle-software --output-dir captures
python3 benchmarks/device_portability/scene_collector.py group captures/mesa-software-record.json captures/angle-software-record.json --artifact-root captures --output captures/grouped.json
```

The collector runs actual GLES shader compilation, texture-FBO rendering and pixel
readback. Each backend runs 12 draws and 4 final readbacks. Both the constant-image
positive and checkerboard resolution-loss negative are required. Ingestion checks
the scene file hash and exact graph/source/pass/synchronization bindings, then
recalculates CPU goldens and A/B pixel quality instead of trusting pass flags.
The failed checkerboard candidate selects baseline fallback; this is intentional
quality rejection, not a successful optimization.

Groups are separated by software backend, workload and both graph hashes. Group
summaries do not average different drivers or infer a GPU-family rule. No timing,
thermal, power or physical-device identity is manufactured. Safe evidence from two
actual software runs is in `evidence/`; `grouped.json` is SOFTWARE_QUALITY_ONLY.
Raw environment metadata is never serialized by this collector. Hash checking
establishes integrity, not independent capture authenticity.

The existing `protocol.py` remains the physical paired-timing gate and rejects
software records. Conversely, this collector rejects physical records rather than
relabeling software as a device. Physical scenario execution, physical image oracle,
GPU timer/thermal collection and authenticated provider integration remain
BLOCKED_BY_HARDWARE. These records cannot satisfy physical W8/release gates, and
the existing `matrix.json` physical NOT_RUN entries are deliberately unchanged.

Tests: `python3 -m unittest discover -s benchmarks/device_portability -v`.
