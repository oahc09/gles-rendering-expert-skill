# LongRunCapture v1 — sampling is not thermal/power proof

Reuse DeviceLab's device/driver/backend identity and scene source hashes. The JSON
capture records schema_version/provenance/clock, device (device, SoC, GPU, driver,
OS/API, backend, refresh, resolution, power mode), scene SHA, sampling coverage,
optional power/thermal/frequency provenance, events and ordered samples.
Each sample has monotonic `t_s`, foreground, quality_level, refresh_hz, optional
frame_ms and positive budget_ms, thermal status, temperature °C, CPU/GPU frequency
Hz, CPU-submit/GPU-work durations ms, calibrated bandwidth utilization [0,1], and
instrument power mW. Unknown fields are **null**, never zero-as-unknown.

`provenance` is `device_capture`, `host_workload_iterations`, or `synthetic_fixture`.
Host workload elapsed time includes process launch, GL context setup, compilation
inside that process and readback; it is **not display frame duration or GPU time**.
The host runner controls software EGL and retains raw stdout/stderr, executable,
scene and runner SHA. It writes atomic progress checkpoints, returns failure on
nonzero/timeout, and makes no thermal/power measurements. The driver snapshot in
raw scene stdout is separate from unavailable host device identity fields.

```sh
# Explicit executable, no shell command expansion. A real 10-minute host run:
python benchmarks/longrun/capture.py --duration 600 --interval 2 \
  --scene-source examples/scenes/scene_lab.cpp --output /tmp/longrun.json -- \
  /absolute/path/scene-lab S01 /tmp/longrun.ppm 96 64 baseline
python benchmarks/longrun/analyze.py /tmp/longrun.json --output /tmp/summary.json
# Same procedure supports --duration 1800 for a real 30-minute capture.
```

## Device protocol (not executed by host runner)

Use an explicitly authorized native/ANGLE device adapter, not a renderer-string
inference. Capture actual frame events, thermal-status API samples and source-
identified counters on one monotonic clock; retain raw trace plus conversion hash.
Run 600s functional and 1800s sustained profiles separately, cold and thermally
steady starts, fixed scene/quality/refresh/resolution and power mode. Record
interaction bursts, foreground/background and refresh transitions as events;
segment analysis around those transitions. Do not turn off thermal protection or
force frequencies. Report median/quantile distributions, sample coverage and jank
ratio definition. Repeat and retain failures; do not mistake 1800 synthetic seconds
for a 30-minute actual device run. Current cold/steady physical runs: NOT_RUN_DEVICE.

## Analysis limits

The empirical quantiles interpolate adjacent sorted samples. Jank is the fraction
of **sampled foreground frame durations** above their recorded budget, not a claim
about unobserved display frames. Drift is OLS ms/min; frequency correlation is
Pearson, undefined with zero variance. Hypotheses require ≥30 co-observed samples
within a stable foreground/refresh/quality segment. Thermal/frequency, CPU-submit
and bandwidth hypotheses remain falsifiable correlations, not universal causality.
Missing channels produce INSUFFICIENT_EVIDENCE. No GPU counter means no bandwidth
savings claim. Power stays null unless an explicit raw instrument artifact is
hash-bound with matching samples, units, instrument identity and operator-supplied
calibration reference (`--power-file`). Calibration authenticity is not certified.
No battery-saving percentage is inferred.

Five authored fixtures cover thermal, CPU submission, GPU bandwidth, unknown and
configuration confounding. They contain synthetic 600/1800-second timelines and
background/foreground events. They are not physical traces or actual elapsed runs.

Device captures additionally require nonempty device/SoC/GPU/driver/OS/API/power
identity, positive refresh/resolution, COMPLETE status, measured wall duration at
least requested duration and a raw-trace SHA. These are declared provenance checks,
not independent proof that hardware records are authentic. Failed captures are
rejected; an in-progress host capture cannot produce bottleneck hypotheses.
