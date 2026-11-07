# Independent candidate review

Reviewed source, test contracts, GLES semantics, software evidence, research and
release boundaries before publication. Five final confirmed findings were fixed:

1. Material reflection allowed same-offset members with different GLSL types,
   array extents or orientation. Added explicit metadata checks and real GL
   uniform type/size/row-major emission from the C++ runtime.
2. An omitted sampler reflection array bypassed the binding checks. Required
   reflected sampler metadata whenever the material contract declares samplers.
3. Interface precision differences were rejected despite legal GLES linking.
   Removed that false rejection and retained actual type/interpolation checks.
4. Reordering named resources changed ABI identity without a semantic change.
   Canonicalized named block/sampler/interface order while preserving member order.
5. A second access after a cross-context synchronized read was falsely rejected.
   Persisted per-consumer visibility until the next write, with regression tests.

Earlier cross-checks also hardened cache identity and size bounds, unknown input
handling, unresolved multisample sampling, imported-resource alias exclusions and
runtime failure reporting. Full pipeline tests, C++ rebuild, 32 captures and
18 software-version cases passed after the final changes. The aggregate receipt
is regenerated from the final working tree before commit.

No additional actionable finding was confirmed. This is source review and
software reproduction, not an external GitHub approval or physical GPU/model
acceptance. Hardware performance, distinct native driver backends and paired
model evaluation remain open in the release gates.
