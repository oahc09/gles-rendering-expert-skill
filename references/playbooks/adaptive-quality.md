# Adaptive quality: preserve correctness before promising optimization

Use [QualityPolicy](../../benchmarks/quality_policy/README.md). Apply recommendations
only on the renderer owner after complete capability checks and per-scene visual
approval. MSAA/RT format changes may require rebuilding FBOs; retain previous
working resources until allocation/completeness succeeds, then retire them after
in-flight consumers complete. Never mutate an in-use attachment asynchronously.

Render scale can erase thin geometry; lower shadow resolution changes edges;
bloom removal changes highlight energy; particle reduction affects transparency;
LOD changes silhouettes and may pop; anisotropy changes oblique texture detail.
Preserve a scene-specific floor, delay recovery, reset sustained evidence across
background/gaps, provide an off switch and a rollback path. Timing gains cannot
waive unacceptable banding/flicker or a missing GLES extension.

The common policy never invokes native GLES/ANGLE/Vulkan commands. Those backends
must each implement and validate the requested resource change. Review the full
preset against W6, not just a scale-only image. Current presets are engineering
examples and no physical performance/energy gain has been established.
