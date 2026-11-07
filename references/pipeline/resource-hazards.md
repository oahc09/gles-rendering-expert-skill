# GLES resource hazards

Run `python benchmarks/pipeline/hazards.py trace.json` on a raw trace or run
`python -m unittest discover -s benchmarks/pipeline -p 'test_hazards.py' -v` for
19 positive/negative authored traces. This is a conservative whole-object static
model. GL errors and driver bugs are not inferred from a warning.

The trace declares `gles` and ordered `events`. An event may have `barrier` (GLES
bit names, issued before its accesses), `context`, and `accesses` with `resource`,
`kind`, `mode` and `stage`. Barriers apply only to earlier writes in that context.
After an image/SSBO shader write, choose the bit by the **following consumer**:

| Consumer | glMemoryBarrier bit |
|---|---|
| SSBO | GL_SHADER_STORAGE_BARRIER_BIT |
| Shader image | GL_SHADER_IMAGE_ACCESS_BARRIER_BIT |
| Texture sampling | GL_TEXTURE_FETCH_BARRIER_BIT |
| Vertex attribute fetch | GL_VERTEX_ATTRIB_ARRAY_BARRIER_BIT |
| Element/index fetch | GL_ELEMENT_ARRAY_BARRIER_BIT |
| Indirect command | GL_COMMAND_BARRIER_BIT |
| Framebuffer access | GL_FRAMEBUFFER_BARRIER_BIT |
| Uniform buffer | GL_UNIFORM_BARRIER_BIT |
| Texture update API | GL_TEXTURE_UPDATE_BARRIER_BIT |
| Buffer update API | GL_BUFFER_UPDATE_BARRIER_BIT |

Bits may be combined. GL_ALL_BARRIER_BITS is accepted, not recommended as a routine
optimization. Producer-stage and consumer-stage are reported. Image-write followed
by texture-fetch requires TEXTURE_FETCH, not merely SHADER_IMAGE_ACCESS. Barriers
before the producer or on another context do not satisfy this command's visibility.
The model also conservatively requires barriers before subsequent writes to a
shader-written resource. It cannot prove disjoint-address race freedom.

GLES 3.0 uses ordered graphics operations and GL sync objects; it does not expose
core compute, SSBO, shader image load/store or glMemoryBarrier. GLES 3.1 adds these.
GLES 3.2 retains the same relevant visibility rules. Extension-specific paths
(e.g. external image producers, EGL native fences or extension image access) must
probe the extension and apply its own visibility contract; this checker does not
silently enable them. Version number alone does not prove extension availability.

**Not a hazard:** sequential framebuffer rendering followed by sampling that texture
in a later draw in the same context, with no simultaneous feedback. No memory
barrier is demanded. **Undefined feedback:** sampling an attached render target in
the same draw. Ping-pong allocations or restructure passes; a memory barrier is
not a repair. Same-object mip/layer accesses are conservative overlaps here;
`subrange` emits `HZ_SUBRANGE_CONSERVATIVE` and is not treated as proof of safety.

Cross-context shared objects need a producer fence after writes, a producer flush
so the fence is submitted, a consumer wait, and visibility/rebinding of changed
shared objects. A `sync` record explicitly asserts all four plus the producer
context. This is a contract check, not proof that actual fence handles, share
relationships and rebinding are correct. Shader-write barriers remain independently
necessary. `glFlush` submits work but does not wait for completion; `glFinish` is
not recommended as a routine replacement for correct sharing/synchronization.

The automated barrier proof covers prior shader-write visibility (RAW/WAW), not
arbitrary read-to-later-shader-write (WAR) ordering. Review those anti-dependencies
against the specification even when this limited checker returns valid.

Dynamic GL bindings, aliases, shader invocation overlap, coherent/restrict semantics,
atomics, workgroup barriers, external producers and actual fence lifetimes require
runtime/shader inspection. `intra_dispatch_dependency` produces HZ_DYNAMIC: command
barriers cannot order workgroups inside a dispatch. CPU test success is not measured
device evidence. Device evidence and performance remain NOT_RUN unless reported by
a separate runtime execution artifact.

Normative historical context:
- [GLES 3.1 glMemoryBarrier](https://registry.khronos.org/OpenGL-Refpages/es3.1/html/glMemoryBarrier.xhtml).
- [GLES 3.0 specification](https://registry.khronos.org/OpenGL/specs/es/3.0/es_spec_3.0.pdf), shared objects, sync and framebuffer feedback.
- [GLES 3.2 specification](https://registry.khronos.org/OpenGL/specs/es/3.2/es_spec_3.2.pdf).
