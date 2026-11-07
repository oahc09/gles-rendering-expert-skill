# RenderGraph planning for GLES

This standalone planner models **whole resource objects**, not Vulkan render passes,
subpasses, layouts or synchronization primitives. Run a raw graph through
`python benchmarks/pipeline/rendergraph.py graph.json`. The machine-readable contract
is `benchmarks/pipeline/schemas/rendergraph.schema.json`. Fixture files wrap a raw
graph in `input` and include expected outcomes; run them using:

```
python -m unittest discover -s benchmarks/pipeline -p 'test_rendergraph.py' -v
```

`depends_on` edges determine a stable topological order, with input order breaking
otherwise unconstrained ties. The checker does not invent producer edges: readers
must explicitly order their producer or follow it in this execution plan. Imported
resources start defined. Writes initialize the entire allocation; partial writes,
load/store region semantics and conditional execution must be expanded or inspected
outside this restricted model. Discard makes contents undefined. Rule diagnostics
include a JSON-style path; cycles include the dependency path.

Rules: `RG_CYCLE`, `RG_DEPENDENCY`, `RG_UNDEFINED_READ`, `RG_UNKNOWN_RESOURCE`,
`RG_FEEDBACK`, `RG_ATTACHMENT_SHAPE`, `RG_FORMAT`, `RG_RESOLVE`, `RG_DISCARD`.
Equal attachment dimensions are a conservative **planner contract**, not a claim
that every dimension mismatch is a GLES completeness violation. Runtime must call
`glCheckFramebufferStatus`, verify format renderability, sample counts, layer and
mip attachments and device limits. RG_FEEDBACK conservatively rejects same-object
read/write; subrange declarations are explicitly rejected rather than implying
that different mip/layer views are always safe.

MSAA resolve is deliberately restricted to equal size and format, multisample
source, single-sample destination, NEAREST filter. Depth/stencil aspect masks and
integer color classes still need runtime validation. Ordinary sequential FBO write
then texture sample in a later draw requires **no glMemoryBarrier**. An attachment
feedback loop within a draw is not repaired by glMemoryBarrier.

Reads denote sampled reads except a declared resolve source; unresolved multisample
sampling is rejected (this model does not support multisample samplers). Imported
resources cannot be alias candidates, even when marked transient.

The output includes first/last use and compatible nonoverlapping transient alias
candidates. These are planning hints, not automatic GLES memory aliasing. A backend
may recycle an identical texture allocation once its previous lifetime ends.
`RG_INVALIDATE_HINT` recommends discarding dead attachment contents; it is not a
correctness error. GLES 3.x `glInvalidateFramebuffer` promises contents can be lost,
not a speedup. FBO switching reduction and grouping compatible resolves must preserve
ordering and attachment identities; the planner does not reorder these operations
for performance. Device bandwidth, GPU time and thermal A/B remain **NOT_RUN**.

Evidence: 14 authored graph fixtures, including cycles, undefined/discarded reads,
feedback, format/shape violations, valid/invalid resolve and unknown resources.
This CPU model is not GPU execution evidence. Pair with the pipeline EGL smoke
examples for actual supported-device checks; physical device coverage is separate.

Normative historical context (not new 90-day findings):
- [GLES 3.0 specification](https://registry.khronos.org/OpenGL/specs/es/3.0/es_spec_3.0.pdf), framebuffer completeness, blitting, texture feedback and invalidation.
- [GLES 3.1 specification](https://registry.khronos.org/OpenGL/specs/es/3.1/es_spec_3.1.pdf), shader memory access.
