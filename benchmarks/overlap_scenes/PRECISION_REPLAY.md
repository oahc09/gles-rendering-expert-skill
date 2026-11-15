# Precision capability, logical-budget and fixed-target replay

```sh
python3 benchmarks/overlap_scenes/precision_replay.py --config DRIVER_JSON --output REPORT_JSON
python3 -m unittest discover -s benchmarks/overlap_scenes -p test_precision_replay.py -v
```

This finite verifier uses the existing real GLES RGBA8/16F/32F paths and the
`precision_policy.choose` pure policy. It does not silently upgrade the target:
`original_unorm` uses the original per-layer RGBA8 CPU reference; `linear` uses
independent ideal linear accumulation then final RGBA8. Each format's quality is
computed separately for each target using unchanged color/mask/centroid gates.

## Actual execution and budgets

Four inputs: 8 and 48 billboards, cameras 0 and 0.3. Twelve actual format probes
run first, with an independently bounded verification workload. **These probes
are not constrained by the later simulated admission budgets.** This is not a
production no-overhead format switcher. It creates explicit verification targets;
shader/driver/internal allocations are not estimated by the policy.

Then 48 policy scenarios (four inputs × two contracts × six scenarios) evaluate:
full budget, RGBA8-only allocation, conservatively masked float capabilities,
zero transfer budget, zero storage, and an undersized renderbuffer limit.
The actual GL_MAX_RENDERBUFFER_SIZE is queried for ordinary scenarios; the
undersized case is an explicitly simulated stricter limit, not a driver claim.
Masked capabilities are likewise deliberate conservative tests, not actual
absence assertions.

**Only after selection** does replay draw the chosen format again and recheck
against the same fixed golden. `UNAVAILABLE` causes zero further draw/allocation;
there is no implicit RGBA8 fallback when its target quality failed. Candidate
extension, quality, allocation and transfer rejection reasons/costs are retained.
An advertised format encountering GL/FBO/compile failure is a hard failure.

Costs are whole-attachment logical estimates: allocation `w*h*bpp` plus final
RGBA8 output for float; transfer upper bound `2*w*h*bpp*layers` plus float resolve
read/write. They are not actual residency, DRAM bytes, bandwidth, timing or
measured energy. No speedup is claimed.

## Verified result

Both driver runs pass the **admission/replay contract**, not all candidate
quality checks:

| Driver | Probe readbacks / draw calls | Selected replays / draw calls | Unavailable |
|---|---:|---:|---:|
| Mesa | 12 / 336 | 14 / 192 | 34 |
| ANGLE | 12 / 336 | 20 / 480 | 28 |

For the 48-object original_UNORM target, Mesa rejects all formats and returns
UNAVAILABLE even with full budget; ANGLE selects original RGBA8. For the same
48-object **linear** target, both select admitted RGBA16F with full budget but
reject instead of secretly falling back to failed RGBA8 when float allocation
or capabilities are disallowed. The 8-object cases can choose lower-cost RGBA8
where the independently evaluated target gate passes. These are tolerance-gated
finite results, not general format equivalence. RGBA32F was actually probed but
not selected here because a lower-cost admitted format exists when available.

Each JSON includes all independent quality metrics, decisions, selected redraw
results and counts. Its deterministic ZIP contains full probe, target-golden and
selected pixels (64×64 bottom-up RGBA8). Extract beside the report. Rejected
candidate images remain present; previous tiered/half-float FAIL reports are
unchanged. Physical-GPU performance acceptance remains NOT_MEASURED.
