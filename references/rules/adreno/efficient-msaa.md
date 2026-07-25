# Efficient MSAA — On-Tile Resolve Without a Blit

> Distilled from the `msaa` sample: *"Efficient MSAA"* using
> `EXT_multisampled_render_to_texture`.

MSAA is cheap on tiled GPUs **only if the multisample resolve happens inside
GMEM (tile memory)**. The naive desktop-style path — render to a multisample
FBO, then `glBlitFramebuffer` into a single-sample FBO — forces the large
multisample buffer to be **stored to system memory and read back** to resolve.
That blit is exactly the bandwidth cost we want to avoid on mobile.

`EXT_multisampled_render_to_texture` lets the driver keep the multisample
samples in GMEM, resolve them **on-tile** as the tile is written out, and store
**only the single-sample result**. No extra buffer, no blit, no round-trip.

---

## Rules

- **Use `EXT_multisampled_render_to_texture` for all offscreen MSAA.** Never
  create a separate resolve target and `glBlitFramebuffer` between them on
  mobile.
- Check for the extension at runtime before using it; fall back to non-MSAA (or
  a standard multisample renderbuffer + blit) if absent.
- **Prefer 4x MSAA.** On Adreno (as on Mali) 4x is the sweet spot; higher sample
  counts cost disproportionately more for little visual gain. Query the max with
  `glGetIntegerv(GL_MAX_SAMPLES, …)`.
- **Still invalidate the multisample depth/stencil at pass end** — the resolved
  color is stored, but the transient multisample depth must not be.

## Usage

```cpp
// 1) A normal single-sample texture receives the RESOLVED result.
glGenTextures(1, &colorTex);
glBindTexture(GL_TEXTURE_2D, colorTex);
glTexStorage2D(GL_TEXTURE_2D, 1, GL_RGBA8, w, h);

// 2) Attach it to the FBO *as multisampled* — the driver keeps N samples
//    on-tile and resolves into this texture automatically.
glBindFramebuffer(GL_FRAMEBUFFER, fbo);
glFramebufferTexture2DMultisampleEXT(
    GL_FRAMEBUFFER, GL_COLOR_ATTACHMENT0, GL_TEXTURE_2D, colorTex,
    /*level*/0, /*samples*/4);

// 3) A multisample depth renderbuffer (transient — never stored).
glGenRenderbuffers(1, &depthRb);
glBindRenderbuffer(GL_RENDERBUFFER, depthRb);
glRenderbufferStorageMultisampleEXT(GL_RENDERBUFFER, 4, GL_DEPTH24_STENCIL8, w, h);
glFramebufferRenderbuffer(GL_FRAMEBUFFER, GL_DEPTH_STENCIL_ATTACHMENT,
                          GL_RENDERBUFFER, depthRb);

// --- render pass ---
glClear(GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT);  // avoid GMEM load
// ... draw ...
const GLenum transient[] = { GL_DEPTH_STENCIL_ATTACHMENT };
glInvalidateFramebuffer(GL_FRAMEBUFFER, 1, transient); // avoid GMEM store of depth
// colorTex now holds the resolved image — sample it directly, no blit.
```

## Anti-pattern (do NOT do this on mobile)

```cpp
// BAD: explicit multisample FBO + blit resolve = store + reload through DRAM.
glBindFramebuffer(GL_READ_FRAMEBUFFER, msaaFbo);
glBindFramebuffer(GL_DRAW_FRAMEBUFFER, resolveFbo);
glBlitFramebuffer(0,0,w,h, 0,0,w,h, GL_COLOR_BUFFER_BIT, GL_NEAREST); // costly
```
