# Target GPU experiment capture

Nine experiment specifications cover the eight W3 minimum scenes plus C12's branchless texture-fetch counterexample. This runner does not pretend to implement a phone renderer in Python. A target renderer adapter executes a selected scene on a physical device and emits the documented capture contract. Existing host EGL smoke is correctness-only.

```sh
# No target: writes explicit BLOCKED_BY_HARDWARE; exit 3, not PASS.
python3 benchmarks/gpu/capture.py --scenario GPU01 --output /tmp/gpu01-blocked.json
# Validate a real capture and its raw trace hashes; zero means structural validity only.
python3 benchmarks/gpu/capture.py --input device-capture.json --output /tmp/gpu01-reviewed.json
# Target adapter gets scenario JSON on stdin, returns capture JSON on stdout.
python3 benchmarks/gpu/capture.py --scenario GPU01 --adapter '["/path/to/target-runner"]' --output /tmp/gpu01.json
python3 -m unittest discover -s benchmarks/gpu -p 'test_*.py'
```

The adapter is an explicit argv array (no shell interpolation); nonzero exit, timeout and malformed JSON are failures, never blocked-success. No device/root changes or remote uploads occur. Captures must include `status=MEASURED`, `hardware_kind=physical`, `evidence_origin=target_device`, `scenario_id`, device/model/GPU/OS/driver/backend/resolution/refresh/thermal/build identity, correctness method and PASS, warmup/order and >=3 independent runs, fallback and negative observations. Each arm supplies >=3 finite nonnegative CPU/GPU/frame samples in ms, raw trace path and SHA256, and named/unit/source/value counters (or explicit unavailable reason). Trace paths must stay within the capture directory (symlink escapes are rejected); copy the evidence there explicitly. No trace is uploaded by the tool.

Start from [capture-template.json](capture-template.json); change status only after actual execution and remove the UNMEASURED conclusion (the tool will still require human review).

Fields and metadata are supplied by the operator: passing schema cannot authenticate a device or prove a causal speedup. The output computes descriptive statistics and signed GPU-time change, but deliberately retains **REVIEW_REQUIRED** rather than automatically declaring a win. Keep per-run samples and trace details for review; do not pool thermal transitions to hide regressions. See [experiment protocol](../../references/playbooks/gpu-bandwidth.md). The JSON template there describes evidence requirements; capture field names here (`*_time_ms`, `counters`, trace path/hash) are the executable adapter contract.

No physical mobile runner/device is available in this environment: real scene execution and quantitative acceptance are **BLOCKED_BY_HARDWARE**, not completed by these validator unit tests.
