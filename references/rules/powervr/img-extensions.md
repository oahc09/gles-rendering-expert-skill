# IMG Extensions — Framebuffer Downsample, Texture Filter Cubic, Binary Shaders

> Distilled from PowerVR Native SDK examples: `IMGFramebufferDownsample`,
> `IMGTextureFilterCubic`, `BinaryShaders`.

PowerVR hardware exposes several `IMG_`-prefixed extensions that are exclusive
to Imagination GPUs and provide significant optimizations.

---

## 1. `GL_IMG_framebuffer_downsample`

Allows attaching a **half-resolution** texture to an FBO that is automatically
downsampled from the full-resolution render output by the hardware — no
separate downsample pass, no extra DRAM bandwidth.

### Rules

- Use for any post-processing that needs a lower-resolution version of the
  scene: bloom threshold extraction, depth-of-field CoC, ambient occlusion.
- Attach the downsample texture via `glFramebufferTexture2DDownsampleIMG`.
- The GPU performs the downsample **on-chip as tiles are written out** — the
  half-res texture appears alongside the full-res output with zero extra cost.
- **Check extension availability at runtime**; fall back to a manual blit
  downsample if absent.

### Usage

```cpp
// Attach full-size color + half-size downsampled color
glFramebufferTexture2D(GL_FRAMEBUFFER, GL_COLOR_ATTACHMENT0,
                       GL_TEXTURE_2D, fullResTex, 0);
glFramebufferTexture2DDownsampleIMG(GL_FRAMEBUFFER, GL_COLOR_ATTACHMENT1,
                                    GL_TEXTURE_2D, halfResTex, 0,
                                    /*xscale*/2, /*yscale*/2);

// Both textures receive data from the same render pass.
// The fragment shader writes to gl_FragData[0] (full) and [1] (auto-downsampled).
```

---

## 2. `GL_IMG_texture_filter_cubic`

Provides **hardware-accelerated bicubic texture filtering** — a single texture
fetch returns a bicubic-filtered result instead of bilinear.

### Rules

- Use for high-quality image upscaling, UI rendering, or LUT sampling where
  bilinear produces visible blocking.
- Enable per-sampler: `glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MIN_FILTER, GL_CUBIC_IMG)`.
- Performance is close to bilinear on PowerVR (hardware-native path); on other
  GPUs you'd need a 4-tap manual Catmull-Rom shader.
- **Falls back gracefully**: if the extension is absent, use standard
  `GL_LINEAR` or a manual cubic shader.

---

## 3. Binary Shaders (Program Binaries)

The PowerVR SDK heavily uses **`glGetProgramBinary` / `glProgramBinary`** for
offline-compiled shaders. Because PowerVR's compiler runs on-device and
compilation is relatively expensive, caching binaries provides significant
startup time savings.

### Rules

- **Always cache compiled program binaries to persistent storage** after
  first successful link. Reload with `glProgramBinary` on subsequent launches.
- Query `GL_NUM_PROGRAM_BINARY_FORMATS` to verify support (always available on
  PowerVR GLES 3.0+).
- **Invalidate the cache when the GPU driver updates** — binary format can
  change. Store the driver version string alongside the cache.
- PowerVR SDK pattern (`ShaderUtilsGles`): compile shader → attach → link →
  **immediately delete shader objects** (`glDeleteShader`) after link. The
  linked program retains the code; keeping shader handles alive wastes memory.

### Pattern (from SDK ShaderUtilsGles)

```cpp
// Compile + link + delete shader objects
GLuint vs = loadAndCompileShader(vertSrc, GL_VERTEX_SHADER);
GLuint fs = loadAndCompileShader(fragSrc, GL_FRAGMENT_SHADER);
GLuint program = glCreateProgram();
glAttachShader(program, vs);
glAttachShader(program, fs);
glLinkProgram(program);
// ✅ Delete shader objects immediately — program retains the code
glDeleteShader(vs);
glDeleteShader(fs);

// Cache the binary for fast reload
GLint binaryLength = 0;
glGetProgramiv(program, GL_PROGRAM_BINARY_LENGTH, &binaryLength);
std::vector<uint8_t> binary(binaryLength);
GLenum binaryFormat = 0;
glGetProgramBinary(program, binaryLength, nullptr, &binaryFormat, binary.data());
// ... write binary + binaryFormat + driver version to disk ...

// On next launch: reload without compile
GLuint cachedProgram = glCreateProgram();
glProgramBinary(cachedProgram, binaryFormat, binary.data(), binaryLength);
// Check link status — if it fails (driver updated), recompile from source
```

---

## 4. `GL_IMG_multisampled_render_to_texture`

Similar to `EXT_multisampled_render_to_texture` (shared with other vendors),
this extension enables **on-tile MSAA resolve**. The PowerVR SDK uses it
identically to the Adreno pattern:

- Attach a single-sample texture to the FBO via
  `glFramebufferTexture2DMultisampleIMG(...)`.
- MSAA samples live in tile memory and resolve on-chip when the tile is stored.
- **Never use `glBlitFramebuffer` for MSAA resolve on PowerVR** — it forces a
  full store + load cycle through DRAM.

---

## Summary of IMG extensions to check at runtime

| Extension | Purpose | Fallback |
|:---|:---|:---|
| `GL_IMG_framebuffer_downsample` | Free half-res output | Manual blit downsample |
| `GL_IMG_texture_filter_cubic` | HW bicubic filtering | 4-tap Catmull-Rom shader |
| `GL_IMG_multisampled_render_to_texture` | On-tile MSAA resolve | `EXT_multisampled_render_to_texture` or blit |
| `GL_PROGRAM_BINARY_LENGTH` (core) | Shader binary caching | Recompile from source |
