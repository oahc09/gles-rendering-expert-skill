# W7 evidence

`run.py` builds and exercises libktx at runtime; optional `--gles-sdk` adds actual
software EGL upload/sampling/readback. `evidence/report.json` distinguishes host
CPU costs, software GL quality, and physical-device NOT_RUN. It is not a model or
mobile performance report. `test_pipeline.py` tests capability/color/protection
policy and negative cases. No protected buffers are captured.

`selection-test.json` exercises automatic capability-based selection with the real
DeviceLab software snapshot; unit tests separately cover synthetic fallback
capability combinations. `tool-receipt.json` verifies the official KTX download.
