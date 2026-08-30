# Texture Streaming & LOD Control on GLES

> Large-world GLES projects cannot keep every mip resident. This document covers
> mip-level streaming, LOD control, and bandwidth budgeting on TBDR mobile GPUs.
> Format/compression choices (ASTC/ETC2, KTX2) are in card 02 and
> `gles-api-standards.md` §3.3; cross-thread upload is in `egl-and-context.md`.

---

## 1. Rules

1. **Create immutable storage for the FULL mip chain upfront**:
   `glTexStorage2D(target, levels, ifmt, w, h)` with
   `levels = 1 + floor(log2(max(w, h)))`, then stream individual levels later
   with `glTexSubImage2D(target, level, ...)`. A texture object without its top
   mips is still usable while `GL_TEXTURE_BASE_LEVEL`/`GL_TEXTURE_MAX_LEVEL`
   keep the effective range valid — never allocate/reallocate per level.
2. **Gate the resident range, not the object**: after uploading mip N..0,
   `glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MAX_LEVEL, n)` to admit the new
   levels; on eviction lower `GL_TEXTURE_BASE_LEVEL` and sample a fallback.
   Changing base/max level is cheap state, not a re-upload.
3. **Stream through PBOs, not client pointers**: `glTexImage2D/glTexSubImage2D`
   with `GL_PIXEL_UNPACK_BUFFER` bound and a byte-offset pointer decouples the
   copy from the CPU (see `references/examples/pbo_streaming_upload.cpp`).
   Unmapped client-pointer uploads stall the driver's packer thread.
4. **Upload on a worker thread with a shared context**, signal visibility with
   `glFenceSync` + `glFlush` (consumer: `glWaitSync`, then `glDeleteSync`) —
   the render thread must never wait. Full pattern: `egl-and-context.md`.
5. **Budget by bandwidth, not count**: a mobile streaming budget of ~200–400 MB/s
   of texture traffic leaves headroom for geometry. Prefer ASTC 6×6/8×8 over
   4×4 for streaming-heavy content (see card 02 for the block-size table) —
   fixed-rate decode makes bandwidth predictable.
6. **LOD selection controls what you must have resident**: bias the sampler
   (`glSamplerParameterf(sampler, GL_TEXTURE_LOD_BIAS, b)` — sampler-object
   state in GLES 3.0+) or compute LOD in the shader (`textureLod`,
   `textureQueryLod`) and evict below the visible LOD floor. Hysteresis on LOD
   change (+/- 1 level) prevents thrash when the camera sits near a boundary.
7. **Never `glGenerateMipmap` on a mid-frame-hot texture**: it reads the whole
   chain and writes every level (bandwidth spike ≈ 1.33× the texture) and acts
   as an implicit sync point on most mobile drivers. Bake mips offline into
   KTX2; generate only during loading on a freshly uploaded, unsampled texture.
8. **Anisotropic filtering is an extension, not core**: wrap
   `GL_EXT_texture_filter_anisotropic`; query
   `GL_MAX_TEXTURE_MAX_ANISOTROPY_EXT` and clamp (4× is a sane mobile cap —
   16× multiplies filter taps on ground planes).
9. **No sparse textures in modern GLES** — emulate virtual texturing with a
   fixed grid of 128² tiles packed into a `GL_TEXTURE_2D_ARRAY` and
   `texture(sampler2DArray, vec3(uv, tileLayer))`; keep a tile → layer LUT in
   a SSBO/texture. This streams at 16 KB tile granularity instead of per-mip.
10. **TBDR note**: texture *upload* traffic is CPU→GMEM-external DRAM and does
    not touch tile memory; the tile cost comes later from fetches. Streaming
    therefore fights frame bandwidth, not fill rate — schedule large uploads
    during loading screens or between frames, never inside a render pass.

## 2. Code pattern (stream one mip, then admit it)

```cpp
// Worker thread (shared context): upload mip 'level' of an immutable texture
glBindBuffer(GL_PIXEL_UNPACK_BUFFER, pbo[slot]);
void* mapped = glMapBufferRange(GL_PIXEL_UNPACK_BUFFER, 0, size,
    GL_MAP_WRITE_BIT | GL_MAP_INVALIDATE_BUFFER_BIT);
memcpy(mapped, cpuPixels, size);                      // decode/copy off render thread
glUnmapBuffer(GL_PIXEL_UNPACK_BUFFER);

glBindTexture(GL_TEXTURE_2D, tex);
glPixelStorei(GL_UNPACK_ALIGNMENT, 1);
glTexSubImage2D(GL_TEXTURE_2D, level, 0, 0, w >> level, h >> level,
                GL_RGBA, GL_UNSIGNED_BYTE, nullptr);  // nullptr = PBO offset 0
GLsync fence = glFenceSync(GL_SYNC_GPU_COMMANDS_COMPLETE, 0);
glFlush();  // render thread: glWaitSync(fence,...) before sampling the new mip
```

```cpp
// Render thread, next frame: admit the streamed level into the usable range
glWaitSync(fence, 0, GL_TIMEOUT_IGNORED);
glDeleteSync(fence);
glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MAX_LEVEL, level);
glBindSampler(unit, sampler);  // sampler carries MIN_LOD/MAX_LOD + LOD bias
```

## 3. Common pitfalls

| Pitfall | Symptom | Fix |
|:---|:---|:---|
| `glTexImage2D` per streamed mip (mutable storage) | Storage reallocated, old mips lost, driver stalls | One `glTexStorage2D` + `glTexSubImage2D` per level |
| Sampling before top mips exist | Black/incomplete texture (`GL_TEXTURE_COMPLETE == FALSE`) | Keep `GL_TEXTURE_MAX_LEVEL` at the resident floor until upload completes |
| `glGenerateMipmap` inside the frame | Periodic frame spikes | Offline mip bake (KTX2); generate only at load |
| No LOD hysteresis | Texture pops/thrashing uploads on camera wiggle | +/- 1-level hysteresis on residency decisions |
| Client-pointer upload on render thread | Stutter proportional to texture size | PBO staging + shared-context worker upload |
| Assuming anisotropy exists | `INVALID_ENUM` on some drivers | Extension-guard `GL_EXT_texture_filter_anisotropic` |
| Forgetting fence between worker upload and render use | Corrupt/torn mip levels, nondeterministic | `glFenceSync`/`glWaitSync` (or `glMemoryBarrier` inside one context) |

## 4. Cross-references

- Card 02 (formats/compression), card 11 (synchronization), card 03 (buffers/PBO)
- `references/rules/tbdr-bandwidth-rules.md` — bandwidth accounting model
- `references/examples/pbo_streaming_upload.cpp` — triple-buffered PBO pattern
