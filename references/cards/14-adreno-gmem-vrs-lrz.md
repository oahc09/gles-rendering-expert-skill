# Adreno GMEM / VRS / LRZ / FlexRender

> **Category**: Adreno Vendor | **GLES Version**: 3.0+ extensions | **Source**: `references/rules/adreno/*.md`

## 核心规则

### GMEM Load / Store（tile memory 流量）
1. **GMEM = Adreno 片上 tile memory**。GMEM Load = pass 开始从 DRAM 载入 tile；GMEM Store = pass 结束写回 DRAM。
2. **避免 GMEM Load**：pass 开始 `glClear` 或 `glInvalidateFramebuffer` 所有 attachment（除非需保留旧内容，如增量渲染/blend 读回）。警惕 scissor 限制 clear、blend over uncleared target。
3. **减少 GMEM Store**：pass 结束 invalidate depth/stencil/MSAA 等 transient attachment；去掉未使用的 MRT output；`glReadPixels`/blit 批到帧末或用 PBO。

### Efficient MSAA
4. **优先**使用 **`EXT_multisampled_render_to_texture`**（`glFramebufferTexture2DMultisampleEXT`）on-tile resolve，避免 GMEM → DRAM round-trip。若扩展不可用，ES 3.x Renderbuffer + `glBlitFramebuffer` 是合法回退方案（代价是额外 store+load）。

### Variable Rate Shading (`QCOM_shading_rate`)
5. `glShadingRateQCOM(GL_SHADING_RATE_2X2_PIXELS_QCOM)` per-drawcall 降低 fragment 调用频率（无需 glEnable，扩展确认后直接调用）。
6. 低细节 draw（天空盒、远景、模糊、VR 外围）用粗 rate；hero/UI 恢复 `1X1`。**运行时检查扩展**。

### LRZ (Low Resolution Z)
7. Adreno 的 early coarse depth rejection——**不要破坏它**：
   - 不透明 front-to-back；depth test+write on
   - **禁止 `discard`、`gl_FragDepth`**（禁用 LRZ）
   - 透明最后画，depth write off
8. 用 `GL_DEPTH24_STENCIL8` 合并 depth+stencil；pass 结束 invalidate。

### FlexRender
9. 驱动自动选 binning(tiled) 或 direct 模式。保持 render pass 自包含（clear start / invalidate end）让驱动最优选择。

### Frame Extrapolation & Upscaling
10. `QCOM_frame_extrapolation`（AFME）：隔帧渲染 + GPU 外推，省 ~50% CPU/GPU。UI/HUD 排除在外。
11. `QCOM_motion_estimation`：硬件生成 motion vector texture。
12. **SGSR2**：低分辨率渲染 + temporal upscale 到原生——GPU bound 时首选。

## 代码模式

```cpp
// ✅ 避免 GMEM Load + Store
glBindFramebuffer(GL_FRAMEBUFFER, fbo);
glClear(GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT);  // no Load
DrawScene();
GLenum discards[] = { GL_DEPTH_ATTACHMENT, GL_STENCIL_ATTACHMENT };
glInvalidateFramebuffer(GL_FRAMEBUFFER, 2, discards);  // no Store

// ✅ VRS per-drawcall (no glEnable needed — call directly after confirming extension)
glShadingRateQCOM(GL_SHADING_RATE_4X4_PIXELS_QCOM);
drawSkybox();
glShadingRateQCOM(GL_SHADING_RATE_1X1_PIXELS_QCOM);
drawHero();
```

## 常见陷阱

| 陷阱 | 后果 | 修正 |
|:-----|:-----|:-----|
| Scissor clear 代替 full clear | 触发 GMEM Load | 全 clear 或 invalidate |
| Depth/stencil 不 invalidate | 每帧无谓 GMEM Store | pass 结束 invalidate |
| Blit resolve MSAA | DRAM 往返 | `EXT_multisampled_render_to_texture` |
| Opaque 用 `discard` | LRZ 失效，overdraw 全执行 | alpha blend 或隔离 pass |
| VRS 全局 4x4 | 画面模糊 | per-drawcall，hero 恢复 1x1 |
| 不检查 QCOM 扩展 | 崩溃 | 运行时查询 + fallback |

## 关联卡片

- [08-tbdr-bandwidth](08-tbdr-bandwidth.md) — 通用 TBDR 带宽模型
- [04-framebuffer-objects](04-framebuffer-objects.md) — FBO clear/invalidate
- [10-msaa-antialiasing](10-msaa-antialiasing.md) — MSAA 通用规则
- [09-overdraw-fillrate](09-overdraw-fillrate.md) — early-Z / overdraw
