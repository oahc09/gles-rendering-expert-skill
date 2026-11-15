# Finite weighted blended OIT representative: quality rejected, baseline retained

Primary reference actually read: McGuire and Bavoil, [Weighted Blended Order-Independent Transparency, JCGT2(2),2013](https://jcgt.org/published/0002/02/09/paper.pdf), Listing3/4 and limitations. Format reference: fixed official [EXT_color_buffer_float](https://raw.githubusercontent.com/KhronosGroup/OpenGL-Registry/1cdd228e34966dd6b95bd203e9f84faba0f371a1/extensions/EXT/EXT_color_buffer_float.txt). Retrieval hashes are archived; neither full paper nor extension prose is vendored. No inference about IP licensing or full implementation conformance is made from reading these documents.

## GLES3 mechanism

This is a bounded adaptation, not a claim to reproduce every weighting scheme in the paper. Three full-screen constant-color translucent layers have fixed depths0,1,3 and positive weights w(z)=1/(1+z), giving1,.5,.25. Colors are straight RGB; accum stores weighted **premultiplied** RGB and alpha sums.

- Accum RGBA16F clear0, first geometry pass: ONE/ONE blending, output vec4(rgb*alpha,alpha)*weight.
- Reveal RGBA16F clear1, second geometry pass: ZERO/ONE_MINUS_SRC_ALPHA blending, output vec4(alpha).
- Resolve separate RGBA8 target: rgb=accum.rgb/max(accum.a,0.0001)*(1-reveal.r); alpha=1-reveal.r. This is compositing over a transparent-black background, not an arbitrary opaque scene.

Separate geometry passes avoid needing indexed independent blending. No pass samples its writable attachment. NEAREST texelFetch avoids filter requirements. Formats are gated by advertised color-buffer support **and actual framebuffer completeness plus additive half-float blend/fetch pixel probe**. RGBA32F blending is not assumed. Unsupported formats stop with exit77 and no OIT acceptance; the present executable's fallback after a quality rejection uses the validated sorted-alpha target. A format-unsupported platform needs its separately validated RGBA8 baseline, which is not exercised by these successful-format host runs.

Independent Python CPU oracle quantizes intermediate arithmetic to IEEE half at each layer, accumulates revealage product, and converts to RGBA8. The datasets use bounded binary-exact values; oracle agreement does not prove all GPU floating-point rounding behavior. Algorithm tolerance1 byte and approximation tolerance2 bytes are fixed **local controls for these new samples**, not replacements or relaxed thresholds for any previous scenario or original plan.

## Actual software results

Each Mesa/ANGLE process ran119 real draws and19 readbacks: one additive-blend probe, two datasets, all6 permutations per dataset, two deterministic invalid-algorithm variants, plus far-to-near sorted-alpha baselines. Both CLI exits0 mean `HOST_CONTRACT_PASS`, **not OIT quality acceptance**.

| Dataset | OIT-vs-CPU max error | Permutation difference | OIT-vs-sorted max byte difference | Selection |
|---|---:|---:|---:|---|
| soft-colored |0|0|19| SORTED_ALPHA |
| high-opacity-colored |0|0|28| SORTED_ALPHA |

Both drivers produced these results. The validated sorted baselines match their separate CPU half-float OVER oracle exactly. Candidate quality fails the local2-byte bound, so both scenes explicitly retain sorted-alpha fallback. This is expected approximation error for contrasting overlap, not a false assertion that the algorithm implementation failed.

Negative variants are actual GPU renders: wrong revealage uses additive instead of multiplicative blend; missing-layer omits the middle layer in both passes. Both match their independently predicted wrong-output oracle but fail the correct-algorithm oracle. No undefined behavior or fabricated missing-barrier result is used as a negative.

## Costs and limits

Per normal3-layer OIT:6 geometry draws,1 resolve draw,2 clears,2RGBA16F intermediates plus RGBA8 output =20 target bytes/pixel. The comparison baseline additionally allocates8bytes/pixel and uses3 geometry draws plus copy resolve. Nominal geometry attachment read+write accounting is6×8×2=96bytes/pixel, excluding clear/resolve traffic, but **is not measured DRAM bandwidth**; compression, cache and tile behavior can change physical traffic. No benefit or free transparency is claimed.

This representative does not replace prior failed baselines. The finite host result does not close W7's entire matrix, establish original workload budgets, or validate provider/physical hardware. Sorting uses known, nonintersecting full-screen layers; per-pixel intersections, refraction, arbitrary backgrounds, large depth ranges, overflow/underflow, temporal stability and mobile energy/bandwidth remain NOT_RUN. Two software backends are not two physical vendors.

```sh
python3 benchmarks/coverage/weighted-oit/run.py --config DRIVER_CONFIG.json --output REPORT.json
python3 -m unittest discover -s benchmarks/coverage/weighted-oit -p 'test_*.py' -v
```

Public artifacts exclude local paths and OS/library fingerprints. `mesa.json` and `angle.json` retain complete final pixel arrays, sorted baselines, permutations, negatives, capability probe and separate quality decisions. Seven tests check independent CPU properties, real evidence, scope, cost and hashes; they are not substitutes for the archived real execution.

For the algebraic limitation of fixed depth-only weights and the finite strict-order guard, see [exact-policy analysis](../../benchmarks/coverage/weighted-oit/exact-policy-analysis.md). It rejects crossing/tied inputs instead of presenting sorted alpha as a universal exact fallback.

For a separately validated finite crossing-layer alternative, see [bounded GLES3 depth peeling](../../benchmarks/coverage/depth-peeling/README.md). Its K+1 overflow proof and depth-domain rejection are mandatory; the original weighted-OIT approximation has not been changed or reclassified.

The [finite integration adapter](transparency-routing.md) executes and validates the full source-bound evidence chain before selecting a route. Exact requests with unavailable evidence, inadequate budget or failed quality remain unavailable rather than silently choosing approximation.
