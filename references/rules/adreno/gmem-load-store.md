# GMEM Loads & Stores — The Core Adreno Bandwidth Rule

> Distilled from the `avoid_gmem_loads` and `reduce_gmem_stores` samples and the
> Qualcomm doc *"Understanding and resolving Graphics Memory Loads"*.

Adreno is a **tiled** GPU. The framebuffer is divided into small tiles that are
rendered one at a time inside fast on-chip **GMEM** (Graphics Memory). Traffic
between GMEM and slow system memory (DRAM) is the dominant bandwidth and power
cost on mobile. There are exactly two directions of that traffic:

- **GMEM Load** — the driver copies a tile's *previous* contents from system
  memory **into** GMEM before rendering the tile. Needed only when you intend to
  *read back* what was already in the attachment.
- **GMEM Store** — the driver writes the finished tile from GMEM **back** to
  system memory. Needed only when you actually consume the attachment later.

Every unnecessary load or store wastes bandwidth, slows the frame, and drains
the battery. The goal is to perform **zero** loads and **only the stores you
truly need**.

---

## 1. Avoiding GMEM Loads

**Rule: at the start of every render pass, clear or invalidate *all* attachments
you are about to render into.** This tells the driver the old tile contents are
irrelevant, so it skips the load.

```cpp
// Preferred: a full clear signals "don't load the old tile".
glBindFramebuffer(GL_FRAMEBUFFER, fbo);
glClearColor(0.0f, 0.0f, 0.0f, 1.0f);
glClear(GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT | GL_STENCIL_BUFFER_BIT);

// Alternative when a clear color is not wanted: invalidate before drawing.
const GLenum all[] = { GL_COLOR_ATTACHMENT0, GL_DEPTH_ATTACHMENT, GL_STENCIL_ATTACHMENT };
glInvalidateFramebuffer(GL_FRAMEBUFFER, 3, all);
```

### What silently triggers a GMEM load (avoid these)
- **A partial clear** — clearing with a **scissor** rectangle enabled, or
  clearing only *some* attachments, forces the driver to load the tile so the
  un-cleared region is preserved. Clear the whole target, or invalidate.
- **Blending / alpha over existing content** without a preceding clear — the
  blend reads the destination, so the destination must be loaded.
- **Not clearing depth/stencil** while still using depth testing.
- **Re-binding an FBO you rendered to earlier** and continuing to draw without a
  clear (the driver reloads to preserve earlier results).
- Preserving the default framebuffer between frames (`EGL_BUFFER_PRESERVED`).
  Keep the default surface at `EGL_BUFFER_DESTROYED` and redraw each frame.

---

## 2. Reducing GMEM Stores

**Rule: at the end of a render pass, invalidate every attachment whose result is
not consumed afterward** — especially **depth and stencil**, which are almost
always transient.

```cpp
// After drawing into an offscreen FBO whose *color* we sample later,
// but whose depth/stencil we never read again:
const GLenum discard[] = { GL_DEPTH_ATTACHMENT, GL_STENCIL_ATTACHMENT };
glInvalidateFramebuffer(GL_FRAMEBUFFER, 2, discard);

// For the default framebuffer, depth/stencil are transient every frame:
const GLenum discardDefault[] = { GL_DEPTH, GL_STENCIL };
glInvalidateFramebuffer(GL_FRAMEBUFFER, 2, discardDefault);
```

### What silently triggers a GMEM store (avoid these)
- **Extra render targets you never read.** More attachments → more tiles stored.
  Remove unused MRT outputs; keep the attachment count minimal.
- **Keeping depth/stencil live** after the pass. Invalidate them.
- **A `glReadPixels` / `glCopyTexImage` / blit** mid-frame forces a store (and
  usually a stall). Batch readbacks to the very end, or use a PBO.
- **Switching FBOs back and forth** ("ping-pong" without need) stores/reloads
  each time. Do all work for one target before moving on.

---

## 3. Diagnosing with Snapdragon Profiler

- Use **Snapdragon Profiler → Metrics/Trace** and look at *"% Time Shading
  Fragments"*, GMEM load/store counters, and the *Surface* view.
- A non-zero **GMEM Load** count on a target you meant to fully overwrite is a
  bug — add a clear or invalidate at pass start.
- A **GMEM Store** on depth/stencil that is never sampled is wasted — invalidate
  at pass end.

## 4. Checklist for code review

- [ ] Every render pass begins with a full-target `glClear` **or**
      `glInvalidateFramebuffer` of all attachments.
- [ ] No scissor-limited clear is used where a full clear was intended.
- [ ] Depth/stencil are invalidated at the end of every pass that owns them.
- [ ] No unused MRT color attachments remain bound.
- [ ] Readbacks/blits are batched to end-of-frame or done through a PBO.
- [ ] The default surface uses `EGL_BUFFER_DESTROYED` swap behavior.
