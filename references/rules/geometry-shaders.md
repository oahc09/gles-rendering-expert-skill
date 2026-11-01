# Geometry Shaders (GLES 3.2)

> Adapted for OpenGL ES from the open.gl "Geometry shaders" tutorial
> (https://open.gl/geometry); mobile guidance cross-checked against the ARM
> OpenGL ES SDK for Android ("Procedural modelling with geometry shaders").

Geometry shaders sit between the vertex and fragment stages and can **create
or discard whole primitives** per invocation. In OpenGL ES they exist only in
**GLES 3.2 / GLSL ES 3.20** (desktop GL since 3.2; not in WebGL 2.0). Gate any
GS code behind a runtime version check, and always design a non-GS fallback.

---

## 1. Shader Structure

```glsl
#version 320 es

layout(points) in;                          // input primitive type
layout(line_strip, max_vertices = 2) out;   // output type + vertex budget

in vec3 vColor[];        // per-vertex inputs arrive as ARRAYS
out vec3 fColor;

void main() {
    fColor = vColor[0];
    gl_Position = gl_in[0].gl_Position + vec4(-0.1, 0.0, 0.0, 0.0);
    EmitVertex();
    gl_Position = gl_in[0].gl_Position + vec4( 0.1, 0.0, 0.0, 0.0);
    EmitVertex();
    EndPrimitive();
}
```

- **Input types** (`layout(...) in`): `points`, `lines`, `lines_adjacency`,
  `triangles`, `triangles_adjacency` — must match the draw call's primitive
  class. Vertex positions come via the built-in `gl_in[]` array
  (`gl_in[i].gl_Position`); user varyings from the vertex shader arrive as
  arrays (`in vec3 vColor[]`).
- **Output types** (`layout(...) out`): only `points`, `line_strip`,
  `triangle_strip` — these cover every primitive topology.
- `max_vertices` is the **per-invocation emission budget**; query the
  implementation limit `GL_MAX_GEOMETRY_OUTPUT_VERTICES` (GLES 3.2 minimum 256)
  and `GL_MAX_GEOMETRY_TOTAL_OUTPUT_COMPONENTS`. Keep it as low as possible —
  the limit directly affects shader register allocation.
- `EmitVertex()` snapshots the current output variables into a new vertex;
  `EndPrimitive()` closes the current strip. Forgetting `EndPrimitive` drops
  the final primitive.

## 2. Rules

1. **Version gate:** `#version 320 es` required; on 3.0/3.1 builds use the
   fallback technique (instancing, pre-generated meshes, compute + indirect
   draw). Never emit `#version 150` desktop shaders in ES code.
2. **Amplification is the cost model.** Each invocation runs serially per
   primitive on mobile TBDR GPUs; high fan-out (many vertices per input
   primitive) quickly becomes vertex-bound. Profile before relying on GS for
   bulk generation.
3. **Prefer instancing for repeated identical geometry** (voxels, foliage,
   sprites): `glDrawArraysInstanced` with per-instance attributes is cheaper
   and works from GLES 3.0. Reserve GS for *varying* or *adaptive* topology
   (the open.gl circle-LOD example; ARM SDK procedural modelling).
4. **Incompatible with multiview:** do not combine GS (or tessellation) with
   `GL_OVR_multiview` — see `mali-arm-best-practices.md` §2.
5. **VRS interaction:** when a GS is active, it is the last pre-rasterization
   stage — per-primitive shading rate must be written by the GS
   (`variable-rate-shading.md` §4).
6. **Transform feedback** with a GS captures the GS outputs; the feedback
   primitive mode must match the GS output type
   (`transform-feedback.md` §2).
7. GS cannot create data out of nothing — the invocation count equals input
   primitive count; core GLES 3.2 has no desktop-style `invocations` layout.
   Loop inside `main()` to emit multiple primitives per invocation.
   (`GL_OES_geometry_shader` backports GS to GLES 3.1 on some devices —
   check the extension if targeting 3.1.)

## 3. Mobile Use-Cases Worth Keeping

| Use | Notes |
|:---|:---|
| Procedural sprites/billboards from points | Low fan-out (4–6 verts) is fine |
| Adaptive LOD rings/circles | Vertex attribute drives side count (open.gl pattern) |
| Wireframe / edge overlay pass | Emit `line_strip` per triangle (moderate cost) |
| Layered rendering to arrays | Requires `GL_OES_geometry_shader` layered support — check |

## Related

- `references/rules/transform-feedback.md` — capturing GS output
- `references/rules/variable-rate-shading.md` §4 — GS writes primitive rate
- `mali-arm-best-practices.md` §2 — multiview incompatibility
- Card [12-draw-call-optimization](../cards/12-draw-call-optimization.md) — instancing alternative
