# Clustered Forward Lighting (Forward+) on GLES 3.1+

> Many-lights on mobile within GLES's limits: divide the view frustum into a
> 3D grid of **clusters** (screen tiles x depth slices), precompute which
> lights affect each cluster in a **compute** pass, then in the single forward
> pass each fragment evaluates only its cluster's light list. Avoids deferred
> G-Buffer DRAM traffic — the historically dominant mobile cost.

---

## 1. Applicability

| GLES | Path |
|:---|:---|
| 3.0 | No compute/SSBO → clustered is impractical; use UBO-batched forward (60-100 lights max) or stencil-tiled |
| **3.1+** | Full Forward+: compute cull + SSBO light lists — the reference mobile many-light design |
| + `ARM/IMG` PLS or `EXT_shader_framebuffer_fetch` | Combine: albedo/normal/depth kept on-tile during the lighting pass |

## 2. Rules

1. **Grid sizing**: 16x9 screen tiles x 24-32 depth slices is the mobile
   sweet spot (each tile 2x the TBDR-friendly 16 px); directional lights stay
   in a small global list evaluated everywhere — only point/spot lights are
   clustered.
2. **Logarithmic Z slices**: uniform slices waste precision near the camera.
   Map view depth with
   `slice = clamp(int(log2(zFar / z) / log2(zFar / zNear) * slices), 0, slices-1)`
   and precompute slice near/far planes in a UBO.
3. **Culling compute (one workgroup per cluster)**: test light sphere vs the
   cluster AABB (6-plane sphere test) or cluster frustum; surviving indices
   go into a per-cluster list via `atomicAdd` on a count word. **Cap
   lights-per-cluster (e.g. 64)**; overflow goes to a per-cluster remainder
   list (or gets dropped with a debug counter) — a hard cap keeps the SSBO
   size and shader loop bounds fixed. Barrier discipline inside the group:
   `memoryBarrierShared()` before `barrier()` (card 06 rule).
4. **Between dispatch and shading**: `glMemoryBarrier(GL_SHADER_STORAGE_BARRIER_BIT)`
   — the fragment stage reads what compute wrote. Missing it = stale-light
   flicker that no validation layer shows on release drivers.
5. **Fragment-side lookup**: `clusterIdx = (int(gl_FragCoord.y)/tileH)*gridX*gridZ + (int(gl_FragCoord.x)/tileW)*gridZ + slice` — derive the row-major order once and keep host/shader identical. Loop `for (i=0; i<count; ++i)` over the list with a **constant-bounded** inner loop (`min(count, CAP)`) so drivers unroll predictably.
6. **Bandwidth math decides the wins**: light list = clusters x cap x
   2 bytes (uint16 indices) + counts. 16x9x32 clusters x 64 x 2B = ~590 KB
   worst case — versus a G-Buffer MRT chain at ≥ 12 bytes/px written + read
   every frame. Keep list entries uint16.
7. **Sort/shading model**: one forward pass, lighting accumulated in
   registers; if the material also needs a pre-pass (e.g. decals, complex
   BSDF LUT), use PLS/framebuffer-fetch (card 13/16) to avoid a second
   DRAM round-trip — never "deferred-style" MRT G-Buffer + fullscreen
   resolve unless tile budgets are known to overflow.
8. **Shadow interaction**: clustered *and* per-light shadow maps explode
   bandwidth — cluster only unshadowed lights, keep 1-2 shadowed "hero"
   lights in the global list (see `shadow-mapping-mobile.md`).
9. **Vendor notes**: on PowerVR, HSR already removes hidden fragments —
   clustered + HSR gives per-visible-fragment lighting almost for free;
   do not add a depth prepass. On Mali, watch per-cluster count divergence
   across a warp — dense clusters near the camera dominate cost. On Adreno,
   `QCOM_shading_rate` can co-drive cluster density (coarse shading where
   lists are long).

## 3. Code pattern

```glsl
// lightcull.comp — GLSL ES 3.10, one workgroup per cluster (skeleton)
#version 310 es
layout(local_size_x = 64) in;
layout(std140, binding = 0) uniform ClusterGlob {
    vec4 planes[6];      // cluster frustum planes (world space)
    uint u_LightCount;
};
layout(std430, binding = 0) readonly buffer Lights {
    vec4 posRadius[];    // xyz, w = radius (<= u_LightCount entries)
} u_Lights;
layout(std430, binding = 1) writeonly buffer Lists {
    uint counts[];       // [clusterIdx]
    uint indices[];      // [clusterIdx * CAP + slot]
} u_Lists;
const uint CAP = 64u;

shared uint s_Count;
void main() {
    uint cluster = gl_WorkGroupID.x;
    if (gl_LocalInvocationIndex == 0u) s_Count = 0u;
    memoryBarrierShared();
    barrier();
    for (uint l = gl_LocalInvocationIndex; l < u_LightCount; l += 64u) {
        vec4 L = u_Lights.posRadius[l];
        bool hit = true;
        for (int p = 0; p < 6; ++p)
            hit = hit && dot(planes[p].xyz, L.xyz) + planes[p].w >= -L.w;
        if (hit) {
            uint slot = atomicAdd(s_Count, 1u);
            if (slot < CAP) u_Lists.indices[cluster * CAP + slot] = l;
            // slot >= CAP: overflow -> remainder policy (rule 3)
        }
    }
    memoryBarrierShared();
    barrier();
    if (gl_LocalInvocationIndex == 0u)
        u_Lists.counts[cluster] = min(s_Count, CAP);
}
```

```glsl
// main.frag fragment-stage lookup (GLSL ES 3.10, SSBO reads)
uint slice = uint(clamp(log2(u_ZFar / viewZ) * u_SliceScale, 0.0, 31.0));
uvec3 g = ivec3(ivec2(gl_FragCoord.xy) / ivec2(u_TileSize), int(slice));
uint cluster = (g.y * u_Grid.x + g.x) * u_Grid.z + g.z;
uint n = u_Lists.counts[cluster];
for (uint i = 0u; i < min(n, 64u); ++i) {
    uint l = u_Lists.indices[cluster * 64u + i];
    accum += evaluateLight(u_Lights.posRadius[l], P, N);
}
```

## 4. Common pitfalls

| Pitfall | Symptom | Fix |
|:---|:---|:---|
| No `glMemoryBarrier(GL_SHADER_STORAGE_BARRIER_BIT)` | Lights lag/flicker a frame, device-dependent | Barrier between dispatch and draw |
| Uniform Z slices | Huge far clusters, tiny near clusters, light-count spikes | Log slices (rule 2) |
| Uncapped per-cluster loop | Register pressure kills occupancy | Fixed CAP + overflow list |
| Cluster index formula mismatch host vs shader | Scrambled lighting bands | Derive both from one shared header constant |
| All lights clustered incl. shadowed | Shadow map count x list length blowup | Global shadowed hero lights (rule 8) |
| G-Buffer MRT "just in case" | +GB/s DRAM on every pixel | PLS/fetch or single-pass accumulate (rule 7) |
| uint32 light indices | 2x list bandwidth for nothing | uint16 lists (rule 6) |

## 5. Cross-references

- Card 06 (compute/barriers), card 09 (overdraw), card 13 (Mali PLS), card 16 (PowerVR HSR/PLS)
- `references/rules/shadow-mapping-mobile.md`, `tbdr-bandwidth-rules.md`
