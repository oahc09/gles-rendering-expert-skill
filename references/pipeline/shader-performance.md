# Shader risk hypotheses, not measured performance

`benchmarks/pipeline/shader_risks.py` scans GLSL text for dynamic sampler indices, possible nonuniform branches, texture sampling frequency/loops, additional MRT outputs, vector-declaration pressure and variant cardinality. Every finding includes shader, stage, one-based line, device condition, hypothesis and A/B experiment. Comment removal preserves source line counts.

This is a lexical scan. It cannot establish uniformity, live ranges, register count, occupancy, dead-code elimination, actual executed taps, unused attachments or a driver bug. It may miss multiline forms, macros and indirect calls. No finding is proof that an optimization helps. Dynamic sampler indexing may be a compile-time legality error rather than a performance issue; run the W1 compiler/link checks first.

## Reproduce and investigate

- `python -m unittest discover -s benchmarks/pipeline -p test_shader_risks.py -v`
- `python benchmarks/pipeline/shader_risks.py path/to/shader.frag --stage fragment --device 'actual device / driver'`
- `benchmarks/pipeline/schemas/shader-risk-report.schema.json` defines emitted static reports.
- `benchmarks/pipeline/cases/shader-risk-experiments.json` contains eight complete A/B GLSL ES 3.00 source pairs, a shared fullscreen vertex shader, explicit input-equivalence conditions and reproducible protocols. Sources are checked in under `benchmarks/pipeline/experiments/shader-risks/`. Each includes expected caveats and null hardware measurements; hardware experiment status is NOT_RUN.

Run `python benchmarks/pipeline/shader_experiments.py --compiler /path/to/glslangValidator` to compile and link all 16 arms. The runner writes `benchmarks/pipeline/reports/shader-experiments.json`, including per-arm vertex/fragment/compiler SHA256, compiler version, exact command, stdout/stderr and expectation status. Fifteen arms must compile/link; SR01-A must produce the specific GLSL ES 3.00 dynamic sampler-array indexing rejection. A rejection from another cause fails the test. Missing tools and timeouts produce a persisted failure, never a skipped pass. The checked-in report records an actual local run, not device performance.

Experiments include a uniform-branch control that may gain nothing, extra unconditional texture work that may regress, and dead variables already eliminated by the compiler. Retain these negative results rather than filtering them from reports. An identical-coordinate tap reduction control does not justify reducing distinct-coordinate filtering taps.

For each device, record GL vendor/renderer/version, driver and extensions, shader variant/cache key, compilation logs, render dimensions and image correctness gate. Warm up, randomize or alternate A/B, reject disjoint timer intervals, retain at least 30 GPU samples per arm, and capture bandwidth counters and thermal state where available. Missing counters remain unavailable, never synthetic zero. Report dispersion, raw samples and timing method. A software renderer result cannot substitute for physical-device GPU bandwidth or thermals.

Reuse `benchmarks/traces/` adapters and `benchmarks/gpu/` capture conventions rather than implementing another trace parser. Attach raw capture paths to the experiment result; static schema intentionally only permits NOT_RUN measurement status. Store measured experiments in the device-lab evidence format with device-specific interpretation, not by relabeling a lexical report.

Sources: [GLSL ES 3.10 specification](https://registry.khronos.org/OpenGL/specs/es/3.1/GLSL_ES_Specification_3.10.pdf) for expression/interface legality (SPEC_CONFIRMED, historical-context); [EXT disjoint timer query](https://registry.khronos.org/OpenGL/extensions/EXT/EXT_disjoint_timer_query.txt) for timer validity and disjoint conditions (extension, historical-context). Optimization proposals are Recommendations until controlled device evidence exists.
