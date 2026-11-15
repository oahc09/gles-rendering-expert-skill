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
