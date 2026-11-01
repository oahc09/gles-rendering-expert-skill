# QualityPolicy — deterministic, capability- and visual-gated recommendations

`policy.py` consumes monotonic time, foreground, recent-window p95 and budget,
optional thermal status/trend, backend identity, preference and known capabilities.
The caller computes its recent-window quantile from measured samples; do not use
host process iteration duration as a display frame input. Replay input explicitly
contains those aggregates and is deterministic.

NORMAL → PRESSURED → DEGRADED → RECOVERING uses 3s sustained pressure, 8s stable
recovery, minimum 10s residency/cooldown and sample-gap reset (>2s). A spike or
alternating near-threshold input cannot force per-frame changes. No background
quality change. Disabled policy retains the selected level, recommends no action,
and clears pressure/recovery history. Floor bounds the amount of degradation.
Presets are examples, not validated recommendations for every scene/device:

|Level|Scale|MSAA ceiling|Shadow|Post|Particles|LOD bias|Anisotropy ceiling|
|---|---|---|---|---|---|---|---|
|0|1.0|4|2048|tone map+bloom|2000|0|8|
|1|0.85|2|1024|tone map|1200|1|4|
|2|0.7|1|512|tone map|600|2|1|

MSAA is intersected with supplied sample capabilities; absent data gives no legal
recommendation, not invented support. Texture limits bound shadows. Anisotropy
falls back to 1 without an extension-backed capability (no extension call emitted).
Particles/LOD/shadow/bloom alter silhouettes, temporal stability, transparency and
highlight energy: W6 per-scene visual validation is required. `approved_levels`
must come from those results; absence makes `may_apply=false`, even when timing
suggests degradation. Scale visual approval does **not** approve the complete
preset's MSAA/shadow/particle/LOD changes—validate the complete configuration before
supplying its approval. No GLES/ANGLE/Vulkan/OS API is invoked by this module.

```sh
python benchmarks/quality_policy/replay.py benchmarks/quality_policy/fixture.json --output /tmp/replay.json
python -m unittest discover -s benchmarks/quality_policy -v
```

Performance-visual acceptance remains a measured Pareto decision. Recommendations
do not guarantee speed, energy savings or unchanged appearance.
