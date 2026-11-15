# Two finite W3 optimization A/B families

```sh
python3 benchmarks/shader_ab/optimization_pairs.py --config DRIVER_JSON --output REPORT_JSON
python3 -m unittest discover -s benchmarks/shader_ab -p test_optimization_pairs.py -v
```

## Repeated texture sampling → common sample

The baseline source actually calls `texture(tex, uv)` twice and averages the two values; the candidate evaluates that identical sample once. An 8×8 RGBA8 texture uses NEAREST/CLAMP_TO_EDGE at pixel-centre UVs. Four nonuniform inputs cover a two-dimensional gradient, checker, sharp quadrant edges and varying alpha. An X-mirrored lookup is the rendered incorrect candidate. CPU golden is the authored texel array, independent of either shader's result.

This proves the finite identical-coordinate, identical-sampler pure expression rewrite. The compiler may already merge the baseline's redundant sampling, so source operation count **does not imply fewer executed texture instructions, bandwidth or faster GPU time**. It does not establish equivalence for different gradients/LOD, offsets, sampler states, side effects or sampling across control-flow/derivative discontinuities.

## Compute intermediate → direct fragment evaluation

The baseline dispatches an actual 8×8 compute workgroup, writes 64 highp vec4 results into a 1024-byte std430 SSBO, issues GL_SHADER_STORAGE_BARRIER_BIT, then draws a fullscreen triangle whose fragment shader reads the indexed intermediate. The candidate draws directly and evaluates the same finite pure per-pixel function without allocating the intermediate or dispatching compute. Four frame parameters produce distinct output distributions. A wrong-channel candidate renders a deliberately incorrect result. CPU scalar formulas independently compute the final RGBA8 golden; baseline and optimized outputs must also agree.

The eliminated intermediate is 32-bit float SSBO storage; there is **no intermediate half-float/UNORM quantization**. Inputs are binary-exact fractions, with a fixed one-code RGBA8 output allowance. The source has no atomics, inter-invocation communication, texture derivatives, history, side effects or reuse of results by another consumer. These exclusions are essential: this is a narrowly valid fusion/elimination transformation, not a general compute/draw fusion rule. The baseline always retains its required barrier; the direct candidate has no shared compute writes and therefore needs no such barrier. No missing-barrier undefined behavior is executed.

## Actual verification

Mesa and ANGLE each execute eight experiments × three arms = **24 draw/readbacks**, plus four actual compute dispatches for the fusion baselines. Per driver, 16 correct baseline/candidate outputs pass independent CPU goldens, eight incorrect outputs fail, and all eight baseline/candidate pairs agree. Reports in `evidence/optimization-pairs-mesa.json` and `optimization-pairs-angle.json` contain all output bytes, CPU goldens and shader hashes, with no environment metadata. Both report HOST_PASS. Sixteen unit tests pass.

No physical timing, synchronization duration, memory residency, power or speedup is measured. Runtime command/draw counts establish the authored pipeline shape, not implementation-level optimization or target-device benefit.
