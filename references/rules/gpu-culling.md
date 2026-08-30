# GPU-Driven Culling on OpenGL ES

> Culling that used to need the CPU (frustum, occlusion, small-primitive) can
> run on the GPU with instancing + transform feedback (GLES 3.0) or compute +
> indirect draw (GLES 3.1). GLES has **no** mesh shaders, no shader-driven
> rasterization, and no bindless — the pipeline below is the ceiling for
> GPU-driven rendering in ES. Vendor depth-buffer tricks (Adreno LRZ) are in
> `references/rules/adreno/lrz-and-flexrender.md`.

---

## 1. Capability matrix

| GLES level | Culling tools |
|:---|:---|
| 3.0 | Instancing, transform feedback, occlusion queries (`GL_ANY_SAMPLES_PASSED[_CONSERVATIVE]`) — compact via TF + stream output |
| 3.1 | + compute shaders, SSBO atomics, indirect draw (`glDrawArraysIndirect` / `glMultiDrawElementsIndirect`) — full GPU pipeline |
| 3.2 | + geometry shaders (GS as a compaction/rasterize-less stage; usually inferior to compute) |

## 2. Rules

1. **Standard 3.1 pipeline**: bounding-volume array → compute cull (frustum +
   LOD + small-primitive) → each element writes/zeroes its own
   `DrawArraysIndirectCommand` slot (count = 0 means "skip", nearly free) →
   `glMultiDrawArraysIndirect(mode, indirect, drawCount = elementCount,
   stride)` with `GL_DRAW_INDIRECT_BUFFER`. The CPU never reads back
   visibility. Add atomic compaction (survivors packed into a prefix buffer
   with a per-group shared counter + one global `atomicAdd`) only when the
   element count vastly exceeds survivors.
2. **Barrier discipline when chaining passes**: after the culling compute
   dispatch and before the indirect draw, `glMemoryBarrier()` must name every
   dependent use — at minimum
   `GL_VERTEX_ATTRIB_ARRAY_BARRIER_BIT | GL_COMMAND_BARRIER_BIT |
   GL_DRAW_INDIRECT_BARRIER_BIT`. On a TBDR a missing barrier is a
   nondeterministic one-frame race, not a validation error.
3. **Occlusion culling on mobile is last-resort**: an occlusion query forces
   the driver to resolve samples early — on TBDR that means a tile flush.
   Only worthwhile when the occluded geometry is genuinely expensive
   (hi-poly, heavy overdraw). Use `GL_ANY_SAMPLES_PASSED_CONSERVATIVE`, test
   coarse clusters (not per object), and accept the 1-frame latency:
   query object visibility this frame, cull by **last** frame's result, and
   never stall on the query result (`glGetQueryObjectuiv(..., GL_QUERY_RESULT)`
   before it completes = CPU stall; use `glGetQueryObjectuiv(..., 
   GL_QUERY_RESULT_AVAILABLE)` and defer).
4. **Hierarchical depth beats occlusion queries**: render scene depth once at
   1/16 resolution (early Z pass), then frustum-plus-depth-test clusters in
   compute by sampling the hi-Z buffer. This is the Vulkan-world ReSTricted
   approach adapted to ES 3.1; on tile GPUs the hi-Z pass is cheap if you
   never store color (`glDrawBuffer(GL_NONE)` + depth invalidate after).
5. **Frustum planes into a UBO** (6 x vec4, plane-normalized, in world or
   view space consistently). A compute thread per instance tests
   `dot(plane, sphereCenter) >= -radius` per plane — sphere tests, not AABB.
6. **Stability over optimality**: keep hysteresis on LOD/cull decisions or
   objects pop every frame; a frame-coherent output buffer (sort stable IDs)
   matters more on mobile than culling 5% more geometry.
7. **Small-primitive culling**: discard instances whose projected size is
   under ~2 px (they cost a full vertex fetch + draw slot for sub-pixel work)
   — on tile GPUs triangle setup is not free.
8. **Draw the culled result indirectly against a persistent mapped buffer** if
   `GL_BUFFER_UPDATE_BARRIER_BIT`-style PBO-style sync annoys you: allocate
   the instance buffer once at worst-case size, `glClearBufferfi`-free —
   re-zero only the atomic counter each frame (a 4-byte clear via
   `glClearBufferuiv(GL_ATOMIC_COUNTER_BUFFER, ...)`, not a memset round-trip).
9. **CPU fallback honesty**: on GLES 3.0-only devices prefer CPU culling —
   an SSBO-less TF compaction loop works but each pass costs a full vertex
   round-trip; measure before shipping (see `profiling-tools.md`).

## 3. Code pattern (compute cull + indirect draw, GLES 3.1)

```glsl
// cull.comp — GLSL ES 3.10 — one thread per batch, per-slot predication.
// No compaction, no cross-thread ordering: every slot is written every frame.
#version 310 es
layout(local_size_x = 64) in;

struct Batch { vec4 sphere;        // xyz = center, w = radius
               uvec2 range; };     // first, count in the shared static VB

layout(std140, binding = 0) uniform Frustum { vec4 planes[6]; };
layout(std430, binding = 1) readonly buffer Batches { Batch items[]; } u_Batch;
// DrawArraysIndirectCommand == uvec4 — the args block MUST be `buffer` (SSBO):
// compute cannot write a UBO, and the same GL buffer is rebound as
// GL_DRAW_INDIRECT_BUFFER on the host.
layout(std430, binding = 3) buffer DrawArgs { uvec4 cmd[]; } u_Draw;

uniform uint u_BatchCount;

void main() {
    uint b = gl_GlobalInvocationID.x;
    if (b >= u_BatchCount) return;  // no barrier in this kernel, guard is safe
    bool visible = true;
    for (int p = 0; p < 6; ++p)
        visible = visible && dot(planes[p].xyz, u_Batch.items[b].sphere.xyz)
                        + planes[p].w >= 0.0;
    Batch bt = u_Batch.items[b];
    u_Draw.cmd[b] = visible
        ? uvec4(bt.range.y, 1u, bt.range.x, 0u)   // count, instanceCount, first, baseInstance
        : uvec4(0u);                              // zero-count draw: skipped
}
```

```cpp
// Host: cull dispatch -> barrier -> indirect draw, no CPU readback
glUseProgram(cullProgram);
glBindBufferBase(GL_SHADER_STORAGE_BUFFER, 1, batchesBuf);
glBindBufferBase(GL_SHADER_STORAGE_BUFFER, 3, drawArgsBuf);  // same buffer as
glBindBuffer(GL_DRAW_INDIRECT_BUFFER, drawArgsBuf);          //   indirect source
glDispatchCompute((batchCount + 63) / 64, 1, 1);
glMemoryBarrier(GL_COMMAND_BARRIER_BIT | GL_DRAW_INDIRECT_BARRIER_BIT |
                GL_VERTEX_ATTRIB_ARRAY_BARRIER_BIT);
glMultiDrawArraysIndirect(GL_TRIANGLES, nullptr, batchCount,
                          sizeof(GLuint) * 4);  // stride = DrawArraysIndirectCommand
```

## 4. Common pitfalls

| Pitfall | Symptom | Fix |
|:---|:---|:---|
| Missing `glMemoryBarrier` between cull and draw | Stale/one-frame-late or corrupt instance data | Barrier with all dependent-use bits (rule 2) |
| `GL_QUERY_RESULT` read before availability | Multi-ms CPU stall every frame | `GL_QUERY_RESULT_AVAILABLE` + 1-frame-delayed decisions |
| Per-object occlusion queries | Tile flush per query — slower than not culling | Cluster-level or hi-Z compute approach |
| Atomic compaction without group reduction | One atomic per instance, contention cliff at 10k+ | Per-group shared counter, single global atomic (pattern above) |
| Cull decision flips frame-to-frame | Pop-in at LOD/cull boundary | Hysteresis bands; frame-coherent ordering |
| Reallocating buffers per frame | Orphaning traffic + driver overhead | Persistent worst-case-size buffers |

## 5. Cross-references

- Card 12 (indirect draw), card 06 (compute + barriers), card 25 (transform feedback)
- `references/rules/adreno/lrz-and-flexrender.md` — do-not-break-LRZ constraints
- `references/rules/tbdr-bandwidth-rules.md` — why queries flush tiles
