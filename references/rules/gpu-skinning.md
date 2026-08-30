# GPU Skinning — Matrix Palette Animation

> GPU skinning moves per-vertex bone blending from CPU to the vertex shader.
> Distilled from standard mobile practice (the Adreno SDK historically shipped a
> Skinning sample; the technique is universal across Mali / Adreno / PowerVR).

---

## 1. Two storage strategies for the bone matrix palette

| Strategy | How | When |
|:---|:---|:---|
| **UBO matrix palette** (GLES 3.0) | Bones as `mat4` array in a UBO (`std140`); index via per-vertex bone indices | Default choice; simple, fast, ~64–120 bones |
| **SSBO matrix palette** (GLES 3.1) | Bones in an SSBO (`std430`); more bones, tighter packing | >~120 bones or bone count varies per frame |
| **Vertex-texture palette** (GLES 3.0, legacy) | Bones encoded into a float texture, fetched in VS | Legacy path for GLES 2.0-era hardware; avoid on 3.0+ |

## 2. Rules

1. **UBO size caps the bone count**: `GL_MAX_UNIFORM_BLOCK_SIZE` (typically
   16 KB) ÷ 64 bytes per `mat4` ≈ ~256 theoretical, but per-stage UBO limits
   and other UBOs sharing the budget reduce this. Plan for **~64–120 bones**
   in a UBO; switch to SSBO above that.
2. **Limit per-vertex influences to 4** (`vec4` weights + `ivec4` bone indices).
   4 influences is the mobile standard; 8 doubles VS cost for marginal quality.
   Normalize/re-normalize weights if they can sum away from 1.0.
3. **Normalize the blended normal** after skinning — blending rotations
   de-normalizes the normal; renormalize in the VS before passing out.
4. **Dual-quaternion skinning** (instead of LBS) avoids candy-wrapper twist for
   large rotations but costs more ALU; use only where joint quality matters.
5. **Update the palette once per frame** via a single UBO/SSBO upload
   (`glBufferSubData`, or `glBufferData` re-specification to orphan), not per
   draw call. Skinned instances sharing a pose share the palette.
6. **Frustum-cull skinned meshes with an inflated bounding volume** — skinned
   vertices move beyond the bind-pose AABB; pad the bounds or compute
   CPU-side skinned bounds, or false-culling pops meshes.
7. On GPU-bound devices, skinning is vertex-stage work — it competes with
   vertex-heavy scenes; if VS-bound, reduce bone count/influences before
   cutting fragment quality.
8. **`layout(binding=N)` on the UBO requires GLES 3.1 (`#version 310 es`)**;
   on 3.00 declare the block without a binding and set it via
   `glUniformBlockBinding` + `glBindBufferBase` (see `glsl-es-optimization.md` §8).

## Code pattern (UBO palette, 4 influences)

```glsl
// Vertex shader (GLSL ES 3.10 — the binding= qualifier requires 3.1;
// on 3.00 drop "binding = 2" and use glUniformBlockBinding on the host)
#version 310 es
precision highp float;

#define MAX_BONES 96
layout(std140, binding = 2) uniform SkinningBlock {
    mat4 u_Bones[MAX_BONES];
};

layout(location = 0) in vec3 a_Position;
layout(location = 1) in vec3 a_Normal;
layout(location = 4) in ivec4 a_BoneIndex;
layout(location = 5) in vec4 a_BoneWeight;

uniform mat4 u_ViewProj;
out mediump vec3 v_Normal;

void main() {
    // Renormalize weights defensively
    mediump vec4 w = a_BoneWeight / max(dot(a_BoneWeight, vec4(1.0)), 1e-5);

    mat4 skin = u_Bones[a_BoneIndex.x] * w.x
              + u_Bones[a_BoneIndex.y] * w.y
              + u_Bones[a_BoneIndex.z] * w.z
              + u_Bones[a_BoneIndex.w] * w.w;

    vec4 pos = skin * vec4(a_Position, 1.0);
    v_Normal = normalize(mat3(skin) * a_Normal);  // re-normalize after blend
    gl_Position = u_ViewProj * pos;
}
```

## Common pitfalls

| Pitfall | Symptom | Fix |
|:---|:---|:---|
| Too many bones for UBO budget | Link error / UBO overflow | Move to SSBO (`std430`, GLES 3.1) |
| Weights not normalized | Shrinking/collapsing mesh | Normalize weights before blend |
| Not renormalizing skinned normal | Dim/banded lighting | `normalize(mat3(skin) * n)` |
| Bind-pose AABB for culling | Meshes pop at screen edges | Inflate bounds or skinned bounds |
| Palette re-uploaded per draw | Bandwidth waste | One palette update per frame |
| 8 bone influences by default | 2× vertex cost | 4 influences unless quality demands |
