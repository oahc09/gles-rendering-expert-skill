# RenderGraph advisory boundary

`tools/rendergraph_optimizer.py` imports the existing `benchmarks/pipeline/rendergraph.py` checker rather than duplicating its resource legality rules. Invalid feedback, discarded attachments, unresolved MSAA, dimensions and dependency cycles are rejected before advice.

The checker is a whole-resource planner, not a driver validator. Barrier/external-lifetime evidence is not representable in its existing schema. Without the explicit caller attestation `--synchronization-reviewed`, recommendations are blocked. Attestation does not prove correctness. Unknown barrier fields are rejected rather than silently ignored.

Current conditional candidates: exact-format disjoint transient storage reuse, dead-output transient review, explicit MSAA resolve review, and adjacent same-attachment pass fusion review. No business renderer or graph is mutated. Each candidate contains preconditions, risk, fallback, hypothesis and a validation command. Final/exported outputs must never be dropped merely because the graph contains no readers.

PostFX rescaling is intentionally not proposed: this model does not encode kernels, downstream resolution contracts or quality budgets. Concrete automated semantic proof and actual device A/B remain NOT_RUN. Candidate generation is not proof of safety or performance.

Validation: `python3 -m unittest discover -s tools -p test_rendergraph_optimizer.py` (14 positive/negative cases).
