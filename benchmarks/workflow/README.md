# Minimal real software end-to-end workflow with the existing Advisor

This is an executable connection of existing v1.0.9 components, **not another
standalone GPU control and not a general optimization agent**:

`authored workload descriptor -> fingerprint -> graph-derived logical cost ->
closed experiment registry -> actual GLES graph replay -> archive/hash/source
revalidation -> CPU image quality -> optimization_advisor.advise/decide ->
explicit fallback/evidence result`.

```
python3 benchmarks/workflow/run.py benchmarks/workflow/request.json --config MESA_JSON --backend mesa-software --output-dir captures/mesa
python3 benchmarks/workflow/run.py benchmarks/workflow/request.json --config ANGLE_JSON --backend angle-software --output-dir captures/angle
python3 -m unittest discover -s benchmarks/workflow -v
```

Driver configuration is trusted local operator input, using the existing host's
library-loading mechanism. It is not accepted inside a workload request. The
request contract is closed; command, argv, code and arbitrary experiment names are
rejected before dispatch. Registry dispatch calls a fixed in-process Python
collector; no subprocess shell, exec or eval. No input-selected module is loaded.

## Scope and evidence

The single registered experiment `rgba8-graph-scale-replay-v1` uses existing
`pipeline/candidate_replay.py` through `device_portability/scene_collector.py`.
It renders the baseline 4x4 intermediate and candidate 2x2 intermediate through
three real texture-backed framebuffer passes, preserving 4x4 source/output.
Constant and checkerboard patterns are both executed. Graph/shader hashes bind
execution to the costed scene; independently computed CPU pixels and A/B pixels
are checked again after reading the archived result.

The descriptor is explicitly **synthetic/authored**. It is not measured application
profiling: the fingerprint honestly returns UNKNOWN without invented counters.
The fixed experiment is chosen as an explicit user-requested finite experiment,
not inferred from UNKNOWN as an optimization recommendation. Cost is the existing
uncompressed logical envelope plus explicit nearest-fetch count; it is neither
DRAM traffic nor a physical timing result. Reduced logical cost does not establish
speed, bandwidth or power improvement.

Both supplied software-driver executions completed, with 12 draws/4 readbacks each.
Constant passed finite image quality; checkerboard lost alternating pixels and was
rejected with baseline fallback. Even for the constant pass, **production selection
stays baseline** because physical performance and independent release review are
absent. The workflow never mutates a business renderer. `HOST_WORKFLOW_PASS` means
the finite workflow, including expected rejection, executed correctly; it is not
VERIFIED_IMPROVEMENT and not release acceptance.

`evidence/mesa` and `evidence/angle` contain actual sanitized captures, source/graph
bindings, decisions and grouped revalidation results. They contain no environment
metadata or local driver paths. File hashes prove integrity, not authenticity.
Physical-device/provider integration remains BLOCKED_BY_HARDWARE; Agent model
provider is NOT_RUN. Full application tracing, arbitrary graph transformations,
dynamic quality and measured performance acceptance remain outside this CLI.

## Actual shared Advisor decision path

`tools/optimization_experiments.py` registers the finite scene CLI. After archived
quality revalidation, workflow constructs candidates carrying the actual quality
result, fixed CPU golden/thresholds, baseline fallback and explicitly software-only
measurement provenance. It calls **existing `optimization_advisor.advise`**, which
calls its unchanged `decide`; no parallel performance classifier is implemented.
Constant returns `INSUFFICIENT_EVIDENCE` because physical measurement provenance is
absent. Checkerboard returns `REJECTED_BY_QUALITY` before performance evaluation.
These exact Advisor inputs/results/reasons are archived. Production selection uses
that shared status and remains baseline for both. Estimated performance range and
confidence are zero because no supported numerical gain prediction was collected.
Tests recompute the shared Advisor results from the archived inputs.
