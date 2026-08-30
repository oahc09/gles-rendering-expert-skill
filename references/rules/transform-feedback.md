# Transform Feedback (GLES 3.0 core)

> Adapted for OpenGL ES from the open.gl "Transform feedback" tutorial
> (https://open.gl/feedback), cross-checked against the GLES 3.0 spec and the
> ARM OpenGL ES SDK for Android (Boids sample).

Transform feedback captures **vertex-stage (or geometry-stage) outputs into
buffer objects** on the GPU, so data can be transformed and reused without a
CPU round-trip. Classic uses: GPU particle integration, boids/flocking,
gravity/physics updates, geometry preprocessing. It is the GLES 3.0-era answer
to "update buffers on GPU"; on GLES 3.1+ **prefer compute shaders** for the
same tasks unless the output must feed the rasterizer directly.

---

## 1. Setup Contract

1. Declare the captured varyings **before `glLinkProgram`** — linking depends on them:
   ```cpp
   const GLchar* varyings[] = { "outValue" };
   glTransformFeedbackVaryings(program, 1, varyings, GL_INTERLEAVED_ATTRIBS);
   glLinkProgram(program);
   ```
   - `GL_INTERLEAVED_ATTRIBS` — all varyings packed into **one** buffer (single binding index).
   - `GL_SEPARATE_ATTRIBS` — each varying into its own buffer (one binding index per varying, up to `GL_MAX_TRANSFORM_FEEDBACK_SEPARATE_ATTRIBS`, minimum 4).
2. The captured shader **does not need to write `gl_Position`** when rasterization is discarded.
3. Bind output buffers with `glBindBufferBase(GL_TRANSFORM_FEEDBACK_BUFFER, index, buffer)` — index matches the separate-attrib slot; with interleaved mode only index 0 is used.
4. Size the output buffer for the **worst case** (with a geometry shader, up to `max_vertices` per input vertex).

## 2. Execution

```cpp
glEnable(GL_RASTERIZER_DISCARD);            // pure GPU compute, no pixels
glBeginTransformFeedback(GL_POINTS);        // must match output primitive class
glDrawArrays(GL_POINTS, 0, count);
glEndTransformFeedback();
glDisable(GL_RASTERIZER_DISCARD);
```

- `glBeginTransformFeedback` mode is one of `GL_POINTS`, `GL_LINES`,
  `GL_TRIANGLES` and must match what the last pre-rasterization stage emits:
  with only a vertex shader it must match the draw mode's class; **with a
  geometry shader it must match the GS output type** (e.g. `GL_TRIANGLES` for
  `triangle_strip` out).
- Transform feedback and rasterization can run **together** (update vertices
  while drawing them) — omit `GL_RASTERIZER_DISCARD` in that case.
- **Pause/resume**: `glPauseTransformFeedback()` / `glResumeTransformFeedback()`
  let one active feedback session span multiple draw calls (only while active).

## 3. Reading Results & Variable Output

- GPU→GPU reuse: just bind the feedback buffer as `GL_ARRAY_BUFFER` (or via
  VAO) for the next draw — no CPU involvement, no sync needed between GPU steps.
- GPU→CPU readback: `glGetBufferSubData` is **not available in OpenGL ES**.
  Use `glMapBufferRange(GL_TRANSFORM_FEEDBACK_BUFFER, 0, size, GL_MAP_READ_BIT)`
  after a fence (`glFenceSync` + `glClientWaitSync`), or `glReadPixels` into a
  PBO is not applicable here — mapping is the ES-correct path.
- Variable-length output (geometry shader amplification): wrap the run in a
  query to learn how many primitives were written:
  ```cpp
  glBeginQuery(GL_TRANSFORM_FEEDBACK_PRIMITIVES_WRITTEN, query);
  // ... begin/draw/end transform feedback ...
  glEndQuery(GL_TRANSFORM_FEEDBACK_PRIMITIVES_WRITTEN);
  GLuint prims = 0;
  glGetQueryObjectuiv(query, GL_QUERY_RESULT, &prims);  // primitives, not vertices
  ```
  (Desktop GL has `GL_PRIMITIVES_GENERATED`; GLES 3.x only offers
  `GL_TRANSFORM_FEEDBACK_PRIMITIVES_WRITTEN`.)

## 4. Rules

1. **Runtime object discipline:** feedback objects (`glGenTransformFeedbacks`,
   `glBindTransformFeedback`, `glBeginTransformFeedback`) are required only when
   you need pause/resume or multiple concurrent sessions; simple single-pass
   capture works with buffer binding alone.
2. **Ping-pong buffers** for iterative simulation: buffer A feeds the draw that
   writes buffer B, swap next frame. Never read and write the same buffer range
   in one feedback session.
3. **Buffer size = worst case.** With amplification (GS out), an undersized
   feedback buffer raises `INVALID_OPERATION` and aborts the capture.
4. Choose usage hints honestly (`GL_DYNAMIC_COPY` for buffers written by
   feedback and consumed as vertex data).
5. On TBDR GPUs transform feedback executes in the vertex/geometry stage —
   it adds **no tile traffic**; the cost is vertex processing + buffer write
   bandwidth.
6. **GLES 3.1+: evaluate compute shaders first.** Compute gives random access,
   atomics, shared memory, and unsized arrays (`std430` SSBOs); transform
   feedback is sequential per-primitive output only. Keep TF when you must stay
   on 3.0, or when the output goes straight into a draw with zero extra copies
   (ARM SDK Boids pattern).
7. ANGLE (Windows) supports transform feedback — host testing of TF code works,
   but performance characteristics differ from mobile drivers.

## Related

- `references/rules/geometry-shaders.md` — GS amplification feeding feedback
- `mali-arm-best-practices.md` §3, §7 — compute alternative & Boids
- Card [03-buffer-objects](../cards/03-buffer-objects.md), [06-compute-shader](../cards/06-compute-shader.md)
