# Framebuffer Objects — 生命周期 & MRT & Blit

> **Category**: FBO | **GLES Version**: 3.0+ | **Source**: `references/rules/gles-api-standards.md` §5, `references/rules/tbdr-bandwidth-rules.md` §2

## 核心规则

1. **Render Pass 开始应 `glClear` 或 `glInvalidateFramebuffer` 所有 attachment**——否则 TBDR GPU 被迫从 DRAM 加载旧 tile 内容（GMEM Load）。例外：需要保留旧内容的场景（增量渲染、Load-then-blend、多帧累积）可省略。
2. **Render Pass 结束必须 `glInvalidateFramebuffer` 不再使用的 attachment**（尤其 depth/stencil）——跳过 DRAM 写回（GMEM Store）。
3. 创建后验证 `glCheckFramebufferStatus() == GL_FRAMEBUFFER_COMPLETE`（debug 构建）。
4. MRT：`glDrawBuffers(n, bufs)` 启用多目标；fragment 输出用 `layout(location = N) out vec4`。所有 attachment 必须同宽/高/采样数；每个额外 attachment = 额外一次 tile store（带宽 N×）——不写的 slot 不挂。G-Buffer 典型布局：RT0 albedo+roughness(A)、RT1 normal（`n*0.5+0.5` 编码）+metalness(A)、RT2 深度/自发光；标量先塞空闲 alpha 再加 attachment。深度入颜色附件必须 RGBA 打包（8-bit 单通道无法重建世界坐标）。Mali 上同 pass 消费的中间数据优先 PLS，MRT G-Buffer 是通用回退（结束必须 invalidate）。透明物体不进 deferred——光照后单独 forward pass。详见 `gles-api-standards.md` §5.2。
5. `glBlitFramebuffer` 在 TBDR 上触发 tile resolve——**能直接渲染到目标就不要 blit**。
6. 最小化 FBO 切换次数：每次切换 = 一次 Store + 一次 Load。按 target 分组批处理 draw call。

## 代码模式

```cpp
// ✅ 完整 FBO 生命周期
glBindFramebuffer(GL_FRAMEBUFFER, fbo);
glViewport(0, 0, w, h);
glClear(GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT);  // 避免 GMEM Load

DrawScene();

// depth/stencil 后续不再读取 → invalidate
GLenum discards[] = { GL_DEPTH_ATTACHMENT, GL_STENCIL_ATTACHMENT };
glInvalidateFramebuffer(GL_FRAMEBUFFER, 2, discards);  // 避免 GMEM Store

glBindFramebuffer(GL_FRAMEBUFFER, 0);  // 切到下一个 target
```

## 常见陷阱

| 陷阱 | 后果 | 修正 |
|:-----|:-----|:-----|
| 绑定 FBO 后不 clear 直接 draw | 驱动执行 DRAM→Tile Load（全屏读） | 加 `glClear` 或 `glInvalidateFramebuffer` |
| Scissor 限制下 clear | 只清部分区域 → 仍需 Load 保留其余 | 全 clear 或 invalidate |
| Depth/stencil 不 invalidate | 每帧多一次全屏 DRAM 写 | pass 结束 invalidate |
| 频繁 FBO ping-pong | N 次 Store + N 次 Load | 按 target 分组，减少切换 |
| MRT attachment 尺寸/采样数不一致 | FBO incomplete | 所有附件同宽高、同 sample count |
| G-Buffer 挂 6+ 全尺寸 attachment | tile store 带宽爆炸 | 打包进 alpha / RG16F；Mali 用 PLS |
| 深度存单 8-bit 通道 | 位置重建精度不足 | RGBA 打包或真 depth attachment |
| 用 blit 做 MSAA resolve | 额外 DRAM 往返 | `EXT_multisampled_render_to_texture` on-tile resolve |

## 关联卡片

- [08-tbdr-bandwidth](08-tbdr-bandwidth.md) — TBDR 带宽模型
- [10-msaa-antialiasing](10-msaa-antialiasing.md) — MSAA resolve 策略
- [14-adreno-gmem-vrs-lrz](14-adreno-gmem-vrs-lrz.md) — Adreno GMEM Load/Store 细节
