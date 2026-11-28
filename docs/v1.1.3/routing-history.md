# Historical capability routing and evidence boundaries

## v1.0.7 shader/material/pipeline routing (candidate, not released)

For complete multi-material or multi-pass GLES work, start with the
[pipeline contract tools](../../benchmarks/pipeline/README.md), then select the
[variant/cache](../../references/pipeline/shader-variants.md),
[material ABI](../../references/pipeline/material-abi.md),
[RenderGraph](../../references/pipeline/rendergraph-gles.md),
[resource hazard](../../references/pipeline/resource-hazards.md),
[color pipeline](../../references/pipeline/color-pipeline.md) and
[diagnostic](../../references/pipeline/diagnostics.md) references.
Keep GLES Core, capability-gated extensions, implementation-specific binaries and
performance recommendations distinct. Reject unsupported version/extension paths
before use; validate linked-program ABI and sampler state, not only shader syntax.
Use the [actual C++17/EGL lab](../../examples/pipeline/README.md) for compile/link,
reflection, binary fallback, compute-to-draw, MSAA and analytic image controls.
Treat [static shader risks](../../references/pipeline/shader-performance.md) as hypotheses,
not measurements. A valid whole-resource graph is not proof of dynamic GL state,
intra-dispatch race freedom or physical memory aliasing.
Preserve all earlier cases and [recursive release gates](../../docs/v1.0.7-release-gates.json).
The [30 new Agent tasks](../../benchmarks/agent/V107_CASES.md) have no live model results;
software images are not calibrated displays or mobile performance. Metadata stays
1.0.2 until every inherited gate and release authorization passes.

## v1.0.6 system-engineering routing (candidate, not released)

Use [cross-API and multi-Surface lab](../../examples/system_android/README.md) for
AHB/native-fence ownership and shared EGL lifecycle; [system scenes](../../benchmarks/system_scenes/README.md)
for compute/CPU parity, transparency, lighting and precision; [texture/video pipeline](../../examples/texture_pipeline/README.md)
for actual runtime transcoding and protected-input rejection; [driver compatibility](../../benchmarks/driver_compat/README.md)
for conditional identity-based decisions; and [fault reduction](../../benchmarks/reducer/README.md)
for stable, auditable failure predicates. [Agent2 cases](../../benchmarks/agent/V106_CASES.md)
remain unevaluated until an authorized live provider supplies evidence. Software rendering,
NDK/Java compilation, authored faults and controlled rebuilds never certify physical devices.
Preserve [all predecessor gates](../../docs/v1.0.6/release-gates.json); metadata remains 1.0.2.

## v1.0.5 sustained-quality routing (candidate, not released)

For longrun sampling and thermal/power evidence use [the sustained capture contract](../../benchmarks/longrun/README.md).
Use [quality policy](../../benchmarks/quality_policy/README.md) for deterministic recommendations,
[precision and visual regressions](../../benchmarks/visual_quality/README.md) for numeric/region/temporal gates,
[resource stress](../../benchmarks/resource_pressure/README.md) for owned-object estimates and recovery,
and [Trace SQL](../../benchmarks/traces/sql/README.md) for schema-probed evidence with explicit unknowns.
Do not convert synthetic time, software correctness, source compilation or fixture scores into
physical-device or real-model acceptance. Preserve prior triggers, APIs and [release dependencies](../../docs/v1.0.5/acceptance.md).

## v1.0.4 implementation routing (not released)

For device identity and native/ANGLE comparisons use [DeviceLab](../../benchmarks/device_lab/README.md).
For actual workload correctness and visual error use [SceneLab](../../benchmarks/scenes/README.md).
For exported trace triage use [trace manifests](../../benchmarks/traces/README.md); report hypotheses,
missing counters and falsifiable A/B tests, never a single-utilization bottleneck conclusion.
For Diagnose → Patch → Validate use the existing [repair benchmark](../../benchmarks/agent/REPAIR_WORKFLOW.md).
Keep original version/platform triggers. New functionality does not waive old release gates;
[full traceability](../../docs/v1.0.4-traceability.md) separates local, CI, target and provider evidence.

## Candidate validation and evidence routing

This candidate keeps metadata **1.0.2** until the v1.0.3 full acceptance gates pass.
For executable correctness checks use [host validation](../../examples/validation/README.md).
Engineering routes: [rule contracts](../../benchmarks/rules/README.md),
[Agent benchmark](../../benchmarks/agent/README.md), [capability matrices](../../references/matrices/),
and [release gates](../../docs/release-gates.json). Static contract tests, live model behavior,
host GL correctness and real-device GPU measurements are separate evidence classes.
`MUST` denotes a version/extension-specific normative requirement; `SHOULD` denotes
an engineering default; `CONDITIONAL` requires capability checks and device evidence.
Optimization prose below is not a portable speed guarantee. Software rendering tests
prove only their asserted correctness properties, not real mobile GPU performance.

## v1.1.0 frozen coverage routing (candidate, not released)

For exact GLES 2.0-3.2 or EGL 1.4/1.5 API/extension membership, use `../../references/coverage/source-manifest.json` and the generated catalogs. INDEXED_ONLY is not semantic legality, compiler success, runtime support or device validation. Resolve the exact version/extension, callable entrypoint, dependencies and parameter probe before enabling a path; aliases do not imply interchangeable entrypoints.

For shader-language and EGL lifecycle boundaries, read `../../references/coverage/glsl-es-matrix.md` and `../../references/coverage/egl-matrix.md`. For format/interaction, vendor and scenario limits, select only the relevant coverage matrix. Consult `docs/v1.1.0/release-gates.json` before describing acceptance; inherited failures, physical targets and model evaluation cannot be waived by index completeness.

For distance-field edge errors, compare sampler precision and filtering separately before widening tolerances; see `../../references/coverage/distance-text.md`. For exact transparency requests, weighted OIT is an approximation: require a validated per-sample ordering condition before selecting sorted alpha, and reject crossing or ambiguous order; see `benchmarks/coverage/weighted-oit/exact-policy-analysis.md`. Finite host probes do not establish arbitrary-scene correctness or free bandwidth.

For crossing transparent layers that invalidate global sorting, the [bounded depth-peeling lab](../../references/coverage/depth-peeling.md) demonstrates a GLES3 alternative with explicit depth-domain and layer-count limits. Require the extra overflow pass; never silently truncate layers or advertise its multipass/query cost as a speed improvement.

For end-to-end acceptance of the registered transparency controls, use [finite transparency routing](../../references/coverage/transparency-routing.md). It validates source, input, budget and actual pixels together; it deliberately rejects unregistered geometry and cannot certify arbitrary caller-supplied scene data.

For core/KHR debug output, see [filtered callback lifecycle validation](../../references/coverage/debug-output.md). Select exact version/extension entrypoints, retain callback state until unregister, avoid calling GL from the callback, and collect only the task-approved diagnostic categories rather than indiscriminately publishing driver messages.

For timer-query evidence, see [EXT timer lifecycle validation](../../references/coverage/timer-query.md). Check result availability, disjoint interval and counter-width/overflow limits before interpreting samples. Never treat software timer availability or absence of a disjoint flag as proof of a hardware performance gain.
