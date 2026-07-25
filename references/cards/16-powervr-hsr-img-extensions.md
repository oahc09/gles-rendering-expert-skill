# PowerVR HSR / PLS / IMG Extensions / Tile Bandwidth

> **Category**: PowerVR Vendor | **GLES Version**: 3.0+ extensions | **Source**: `references/rules/powervr/*.md`

## 核心规则

### HSR（Hidden Surface Removal）— PowerVR 独有
1. **ISP (Image Synthesis Processor)** 在着色前对 tile 内所有不透明图元做**完整可见性判定**——不透明像素**零 overdraw**，无需排序。
2. **禁止 depth pre-pass**：HSR 已消除所有隐藏 fragment；depth pre-pass 只会双倍几何开销 + Parameter Buffer 消耗，无任何着色收益。
3. **避免 `discard` / alpha test**：强制 ISP 将可见性决策推迟到 fragment shader 执行后，重新引入 overdraw。用 **alpha blend + depth write off** 替代。
4. **提交顺序**：opaque（任意顺序）→ alpha-tested（尽量少）→ skybox → alpha-blend（back-to-front）。

### Tile 带宽
5. **Pass 开始 clear/invalidate 所有 attachment**——防止 tile load from DRAM。
6. **Pass 结束 invalidate transient attachment**（depth/stencil/MSAA）——防止无意义 tile store。
7. 避免帧中频繁切换 FBO——每次切换触发当前 FBO 全 tile flush（store + 新 FBO load）。

### Pixel Local Storage
8. **PLS (`GL_EXT_shader_pixel_local_storage`)** 实现 on-chip deferred G-Buffer：geometry subpass 写 PLS，lighting subpass 读 PLS，零 DRAM 往返。HSR + PLS 协同：只有可见 fragment 写 PLS，无无效 G-Buffer 填充。

### IMG 扩展
9. **`GL_IMG_framebuffer_downsample`**：自动 on-tile 降采样，免费获得半分辨率输出——用于 bloom / DoF / AO。
10. **`GL_IMG_texture_filter_cubic`**：硬件双三次滤波，性能接近 bilinear。
11. **Program Binary 缓存**：`glGetProgramBinary` / `glProgramBinary` 缓存编译结果到磁盘；驱动更新时失效重编。compile→link 后立即 `glDeleteShader`。

### Parameter Buffer
12. 场景几何存入 **Parameter Buffer (PB)**。超量触发 **SPM (Smart Parameter Management)** 局部渲染——极其昂贵。用 LOD / frustum culling / occlusion query 限制复杂度。

## 代码模式

```cpp
// ✅ PowerVR 正确流程：无 depth pre-pass，clear + invalidate
glBindFramebuffer(GL_FRAMEBUFFER, fbo);
glClear(GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT);
drawOpaqueGeometry();   // HSR → 零 overdraw
drawAlphaBlended();     // depth write off, back-to-front
const GLenum disc[] = { GL_DEPTH_ATTACHMENT, GL_STENCIL_ATTACHMENT };
glInvalidateFramebuffer(GL_FRAMEBUFFER, 2, disc);

// ✅ Binary shader caching
GLint len; glGetProgramiv(prog, GL_PROGRAM_BINARY_LENGTH, &len);
std::vector<uint8_t> bin(len); GLenum fmt;
glGetProgramBinary(prog, len, nullptr, &fmt, bin.data());
// Save bin + fmt + driverVersion to disk
```

## 常见陷阱

| 陷阱 | 后果 | 修正 |
|:-----|:-----|:-----|
| Depth pre-pass | 双倍几何开销 + PB 消耗，零收益 | 去掉，依赖 HSR |
| 大量 `discard` / alpha test | HSR 失效，overdraw 回归 | alpha blend + depth write off |
| Pass 开始不 clear | Tile load from DRAM | `glClear` 或 invalidate |
| Depth/stencil 不 invalidate | 无用 tile store | pass 结束 invalidate |
| 帧中频繁切换 FBO | 全 tile flush | 合并 geometry 到同一 FBO，或用 MRT/PLS |
| 场景过复杂，不做 LOD | SPM 局部渲染 | LOD + frustum culling |
| 不缓存 program binary | 每次启动重编译着色器 | `glGetProgramBinary` 持久化 |
| MSAA 用 blit resolve | DRAM 往返 | `IMG/EXT_multisampled_render_to_texture` |

## 关联卡片

- [08-tbdr-bandwidth](08-tbdr-bandwidth.md) — 通用 TBDR 带宽模型
- [13-mali-pls-multiview](13-mali-pls-multiview.md) — Mali PLS（同一扩展，不同硬件协同）
- [14-adreno-gmem-vrs-lrz](14-adreno-gmem-vrs-lrz.md) — Adreno 对应方案
- [09-overdraw-fillrate](09-overdraw-fillrate.md) — Overdraw / early-Z 对比
- [04-framebuffer-objects](04-framebuffer-objects.md) — FBO clear/invalidate 通用
