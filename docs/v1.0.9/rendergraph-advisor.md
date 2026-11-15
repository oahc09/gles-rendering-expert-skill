# RenderGraph advisory boundary

`tools/rendergraph_optimizer.py` imports the existing `benchmarks/pipeline/rendergraph.py` checker rather than duplicating its resource legality rules. Invalid feedback, discarded attachments, unresolved MSAA, dimensions and dependency cycles are rejected before advice.

The checker is a whole-resource planner, not a driver validator. Barrier/external-lifetime evidence is not representable in its existing schema. Without the explicit caller attestation `--synchronization-reviewed`, recommendations are blocked. Attestation does not prove correctness. Unknown barrier fields are rejected rather than silently ignored.

Current conditional candidates: exact-format disjoint transient storage reuse, dead-output transient review, explicit MSAA resolve review, and adjacent same-attachment pass fusion review. No business renderer or graph is mutated. Each candidate contains preconditions, risk, fallback, hypothesis and a validation command. Final/exported outputs must never be dropped merely because the graph contains no readers.

PostFX rescaling is intentionally not proposed: this model does not encode kernels, downstream resolution contracts or quality budgets. Concrete automated semantic proof and actual device A/B remain NOT_RUN. Candidate generation is not proof of safety or performance.

Validation: `python3 -m unittest discover -s tools -p test_rendergraph_optimizer.py` (14 positive/negative cases).

## PostFX sidecar increment

Supersedes the deferred-PostFX paragraph above. The graph checker remains unchanged;
explicit semantic assertions live in a separate sidecar. An experiment ID must
resolve through a fixed registry to an actual checked-in executable, not arbitrary
text. The runner is never executed implicitly by the advisor.

```
python3 tools/rendergraph_optimizer.py benchmarks/pipeline/postfx_example_graph.json --synchronization-reviewed --postfx-contracts benchmarks/pipeline/postfx_example_contracts.json
python3 benchmarks/pipeline/postfx_quality.py --config DRIVER_JSON --output REPORT_JSON
```

The example proposes a 64×64 → 32×32 private color attachment. The normalized UV,
kernel-rescaling and downstream-resampling flags are caller assertions, not proof.
The example golden is deliberately marked NOT_CAPTURED. No graph rewriting or
quality acceptance occurs. Missing/unsupported contracts, unregistered experiment
IDs, temporal-history and externally-visible outputs are rejected. Input attachment
size validation remains delegated to the inherited checker; non-two-dimensional,
zero, boolean and non-array sizes are rejected before PostFX review.

`postfx-resolution-loss-v1` invokes `benchmarks/pipeline/postfx_quality.py`. It
reuses the existing real texture draw/readback infrastructure: one equivalent
coordinate transform must preserve an independent CPU golden, and one
resolution-collapse variant must fail. This is a finite 2×2 texture → 4×4 image
quality oracle, NOT an implementation or proof of an arbitrary scaled blur,
HDR bloom, dynamic camera, temporal reconstruction or general PostFX pipeline.
Device performance remains NOT_MEASURED. Each actual renderer still needs its
own captures, quality thresholds and matched device A/B before acceptance.

Current advisor tests: 37 positive/negative cases. Finite quality oracle ran
HOST_PASS on Mesa (four actual draws), zero GL errors; not hardware evidence.

## Executable bounded candidate graph replay

`tools/rendergraph_replay.py` now produces an independent copied candidate graph
and preserved fallback, not a mutation of a business renderer. The only executable
transformation is RGBA8 intermediate extent **4x4 → 2x2** in a three-pass
source → nearest sample → present graph. Original source/output remain 4x4.
Graph SHA256 binds each replay, the proposed change and selected fallback.

```
python3 benchmarks/pipeline/candidate_replay.py --config DRIVER_JSON --output REPORT_JSON
python3 -m unittest discover -s benchmarks/pipeline -v
```

The inherited checker runs first. The executable vocabulary then requires exact
producer dependencies, one private whole-resource allocation per texture, distinct
sampled input and framebuffer output, and sequential submission in one context.
Only coherent framebuffer-write → texture-fetch edges exist here: **no explicit
glMemoryBarrier is required**. Arbitrary barrier declarations, compute/imageStore,
SSBO, imported resources, MSAA, aliasing, discard and hidden operations are rejected,
not falsely certified. Incorrect or missing dependency/feedback cases are refused
before calling GLES. Missing barriers for incoherent shader accesses are never run
as undefined-behavior negative controls. This is machine-checkable synchronization
for the closed replay grammar, not proof about caller-supplied arbitrary passes.

Actual GLES replay allocates texture-backed FBOs, compiles shaders and executes all
three passes for each arm. The constant-image case remains within one RGBA8 unit;
the checkerboard case deliberately loses alternating pixels, fails the same image
budget, and selects the baseline graph as fallback. Independent CPU goldens verify
both baseline and transformed output. Each driver executes **12 draws and 4 final
readbacks**. Both software Mesa and pinned ANGLE runs passed; sanitized reports:
`benchmarks/pipeline/evidence/candidate-replay-{mesa,angle}.json`.
No driver/environment fingerprints are serialized.

This closes the absence of *any* executable graph candidate transformation and
replay. It does **not** prove arbitrary blur scaling, temporal/HDR equivalence,
pass fusion, MSAA resolve or alias reuse. Existing generic advice still requires
caller synchronization review. No physical-device time/bandwidth/power gain was
measured, and a passing static image does not authorize renderer replacement.
