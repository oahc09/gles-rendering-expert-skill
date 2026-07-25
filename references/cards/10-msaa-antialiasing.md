# MSAA on TBDR — 高效抗锯齿

> **Category**: Anti-Aliasing | **GLES Version**: 3.0+ | **Source**: `references/rules/tbdr-bandwidth-rules.md` §5.3, `references/rules/mali-arm-best-practices.md` §5, `references/rules/adreno/efficient-msaa.md`

## 核心规则

1. TBDR GPU 在 **Tile Memory 内完成 MSAA resolve**——远比桌面 GPU 便宜。
2. **默认使用 4x MSAA**：Mali 上 on-tile resolve 开销很低（G7x+ 通常为低个位数百分比，因代际/分辨率/着色器复杂度而异）；Adreno 类似。
3. **避免 8x/16x**：16x 可耗费 >50% 性能，收益递减。
4. **使用 `EXT_multisampled_render_to_texture`** 做 on-tile resolve（`glFramebufferTexture2DMultisampleEXT`）——**禁止**手动 blit resolve。
5. Resolve 后立即 `glInvalidateFramebuffer` 多采样 attachment——transient MSAA buffer 不写回 DRAM。
6. 查询最大采样数：`glGetIntegerv(GL_MAX_SAMPLES, &maxSamples)`。

## 代码模式

```cpp
// ✅ On-tile MSAA（无 blit）
glBindTexture(GL_TEXTURE_2D, colorTex);
glTexStorage2D(GL_TEXTURE_2D, 1, GL_RGBA8, w, h);

glBindFramebuffer(GL_FRAMEBUFFER, fbo);
glFramebufferTexture2DMultisampleEXT(
    GL_FRAMEBUFFER, GL_COLOR_ATTACHMENT0, GL_TEXTURE_2D, colorTex, 0, /*samples*/4);

// Depth: multisample renderbuffer (transient)
glBindRenderbuffer(GL_RENDERBUFFER, depthRb);
glRenderbufferStorageMultisampleEXT(GL_RENDERBUFFER, 4, GL_DEPTH24_STENCIL8, w, h);
glFramebufferRenderbuffer(GL_FRAMEBUFFER, GL_DEPTH_STENCIL_ATTACHMENT, GL_RENDERBUFFER, depthRb);

// Render pass
glClear(GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT);
DrawScene();
// colorTex 已含 resolved 结果，直接采样
GLenum discards[] = { GL_DEPTH_STENCIL_ATTACHMENT };
glInvalidateFramebuffer(GL_FRAMEBUFFER, 1, discards);
```

## 常见陷阱

| 陷阱 | 后果 | 修正 |
|:-----|:-----|:-----|
| 渲染到 multisample FBO 再 `glBlitFramebuffer` resolve | 额外 DRAM 往返（Store+Load） | `EXT_multisampled_render_to_texture` |
| 使用 16x MSAA | >50% 性能损失 | 4x 即可 |
| Resolve 后不 invalidate multisample depth | 无谓 DRAM 写 | `glInvalidateFramebuffer` |
| 加载 multisample 纹理从 DRAM | 巨量带宽 | 渲染+resolve in-place，不 load |

## 关联卡片

- [04-framebuffer-objects](04-framebuffer-objects.md) — FBO 生命周期
- [08-tbdr-bandwidth](08-tbdr-bandwidth.md) — 带宽模型
- [14-adreno-gmem-vrs-lrz](14-adreno-gmem-vrs-lrz.md) — Adreno GMEM Store
