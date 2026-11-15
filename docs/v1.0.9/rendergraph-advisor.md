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
