# Independent follow-up: why fixed depth weights cannot assure exact OVER

This follow-up preserves `run.py`, original Mesa/ANGLE evidence and their19/28-byte failures unchanged. No threshold is widened. `exact_policy.py` and `exact_replay.py` add a restricted exact-operator path, not another claim of precise weighted OIT.

## Algebraic obstruction

Let F be a foreground layer with independent color cF and opacity aF, and B a background layer with cB,aB; background is transparent black. Sorted OVER RGB is:

`cF*aF + cB*aB*(1-aF)`.

Weighted OIT RGB is:

`(cF*aF*wF + cB*aB*wB)/(aF*wF+aB*wB) * (1-(1-aF)*(1-aB))`.

For nonzero opacities and independent colors, equality of the two color-coefficient ratios requires `wF/wB=1/(1-aF)`. For unchanged depths but foreground opacity1/4 versus3/4, the necessary ratio changes from4/3 to4. No fixed depth-only weight ratio can satisfy both. Thus current `w(z)=1/(1+z)` cannot guarantee exact OVER across inputs. This is an analytic counterexample, not a statement that every input fails, or a proof all possible transparency methods are impossible.

## Restricted fallback rule

The new policy admits only a finite full-coverage grid with complete finite normalized window-depth arrays in[0,1], valid bounded straight RGBA, distinct layer IDs and a strict common order for every pair at every pixel. It constructs the far-to-near order rather than trusting a caller-provided order. Missing values, NaNs, ties or any crossing reject with UNAVAILABLE. This is sufficient for global sorted OVER for the described sampled layers; it is not a universal mesh intersection theorem.

For the actual experiment, arrays are derived from fixed analytic planes `z(x)=a+b*(x+0.5)` used in the fragment shader. They are not measurements exported from arbitrary scenes. An application cannot present fabricated arrays and thereby obtain verified mesh correctness: trusted geometry/depth provenance, viewport/coverage correspondence and temporal updates would first need an independently checked capture. The policy alone does not authenticate data provenance.

## Actual verification

Each software driver executed24 draws and8 readbacks (four scenes × two orders × two layer draws plus one copy). A separate CPU oracle sorts every sample by its own analytic depth, composites in half precision and quantizes RGBA8. Depth testing is intentionally disabled for ordered transparency; shader gl_FragDepth represents the finite analytic plane but no claim of actual depth-buffer sorting or captured depth proof is made.

- Constant nonintersecting planes: derived order matches CPU with0-byte error; reversed order fails.
- Sloped nonintersecting planes: same result, no reliance on constant depth alone.
- Crossing planes: both possible global orders fail some pixels; policy returns `CROSSING_PER_PIXEL_ORDER` and selects no exact global fallback.
- Equal planes: deterministic CPU tie ordering is only a diagnostic convention; policy rejects ambiguous tie instead of inventing a geometric order.

Both actual CLIs exit0 `HOST_POLICY_PASS`. That means the positive restricted path and negative rejection contracts hold. It does not mean the old weighted approximation became accurate. This finite exact OVER operator still has floating-point/format rounding; tolerance remains1 byte for CPU correctness and2 bytes as the unchanged negative separation, not mathematical infinite-precision equivalence for arbitrary data.

RGBA16F renderability is gated through actual FBO completeness and supported color-buffer extension; actual blend output is validated. Samples are full coverage, scalar opacity, no refraction, no opaque occlusion, no per-sample MSAA, no texture filtering, no temporal changes. Arbitrary intersecting meshes, per-pixel sorting, depth peeling, A-buffer allocation/overflow and device performance remain NOT_RUN. A rejected graph requires a separately validated per-pixel method or an explicit quality relaxation by the owner, not automatic use of global sorting.

```sh
python3 benchmarks/coverage/weighted-oit/exact_replay.py --config DRIVER_CONFIG.json --output REPORT.json
python3 -m unittest discover -s benchmarks/coverage/weighted-oit -p 'test_exact*.py' -v
```

Ten tests cover analytic necessity, derived order, incomplete/tie/crossing rejection, both real reports and preservation of original failed evidence. Original OIT evidence is unchanged; no SDK, physical target or provider claim was added.
