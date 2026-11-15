# Four-fetch bilinear far reconstruction

```sh
python3 benchmarks/overlap_scenes/far_reconstruction.py --config DRIVER_JSON --output REPORT_JSON
python3 -m unittest discover -s benchmarks/overlap_scenes -p test_far_reconstruction.py -v
```

This new A/B keeps the original far-resolution scene, camera poses, fixed
full-resolution CPU target and thresholds. It does not modify the historical
nearest-reconstruction failures. The far pass really renders to32×32; no hidden
64×64 far render or full-resolution analytical compensation is used for the
candidate. Foreground is still independently rendered at64×64 after composition.

The reconstruction shader fetches four neighboring far texels, clamps their
coordinates, and bilinearly weights them at
`position = gl_FragCoord.xy / scale - 0.5`. It writes premultiplied far color/alpha
with blending disabled, then draws foreground with source-over. Independent CPU
bilinear interpolation quantizes toRGBA8 before independently compositing the
foreground. The mechanism oracle verifies the pipeline, but acceptance always
uses the original64×64 target, never the reconstructed target.

## Real dual-driver results

Each run has three cameras × baseline/bilinear/foreground-drop arms, nine actual
readbacks. The unchanged gates are color max4 codes, silhouette disagreement<=2,
centroid/parallax error<=0.1 pixel. The deliberate foreground-drop negatives are
rejected in all views.

| Driver | Candidate max color errors | Candidate silhouette mismatches | Global strategy |
|---|---|---|---|
| Mesa | 3 / 2 / 3 | 1 / 3 / 1 | baseline |
| ANGLE | 3 / 2 / 2 | 1 / 2 / 2 | far_bilinear |

ANGLE passes for this finite camera set. Mesa's center camera still exceeds the
unchanged silhouette budget, so the entire candidate is rejected and every view
uses baseline; there is no camera-dependent strategy switching. Both baselines
and both pipelines' mechanism-oracle checks pass. The remaining Mesa mismatch
is consistent with a quantization-sensitive alpha threshold, not evidence of a
proved driver bug. We do not modify the golden to make it pass.

Verified CLI results: Mesa default exit1 / contract-only exit0; ANGLE default and
contract-only exit0. Contract-only retains Mesa report statusFAIL, tests complete
readbacks, negative rejection, mechanism correctness and global fallback policy.
Missing, empty or duplicate camera records cannot produce an accepted strategy;
a baseline failure makes selection UNAVAILABLE. Saved-report tests verify the
serialized contract, thresholds and actual selected-camera image mappings.

## Cost and limits

Four-fetch reconstruction adds work versus the old nearest copy. The report
records a source-level upper bound of16384 texel fetches and81920 logical
read/write bytes for the4096-pixel reconstruction pass. This is not measured
texture traffic: compiler optimizations, cache, tiling and actual DRAM behavior
are unknown. Both baseline and candidate still have8 draw calls. Candidate far
attachment area is1024 rather than4096 pixels, but no GPU-time or bandwidth
improvement is claimed. Verification renders baseline separately as an A/B
control; it is not secretly used to produce the candidate.

The JSON and deterministic ZIP retain every original-target, mechanism-golden,
actual and negative image, plus executed shader/source hashes. Extract alongside
the report. Only this authored Gaussian/UI input and the three tested cameras
are accepted on ANGLE. Broader content, camera trajectories and physical GPU
performance remain unvalidated. No new full-resolution edge compensation was
added because the finite bilinear route already supplies a useful measured
quality result and an honest remaining failure.
