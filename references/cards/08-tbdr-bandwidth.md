# TBDR 架构 & 带宽优化

> **Category**: Architecture / Bandwidth | **GLES Version**: All | **Source**: `references/rules/tbdr-bandwidth-rules.md` §1, §3, §6

## 核心规则

1. 移动 GPU（Mali/Adreno/PowerVR）均为 **Tile-Based**：Vertex → Binning → Per-Tile Fragment → Writeback。Tile Memory 是片上 SRAM（16×16~128×128 px），**零 DRAM 成本**。
2. **核心目标：最小化 DRAM 读写**。数据尽量留在 Tile Memory。
3. **禁止在渲染循环中调用 `glReadPixels`（同步）**——强制全 tile resolve + CPU stall。用 PBO 双缓冲异步回读。
4. **禁止在渲染循环中调用 `glFinish()`**——摧毁 CPU/GPU 流水线。用 `glFenceSync` 做 targeted 同步。
5. **最小化 FBO 切换**：每次切换 = Store 当前 tile + Load 新 target tile。按 target 分组 draw call。
6. **Framebuffer Fetch**（`GL_EXT_shader_framebuffer_fetch`）：fragment shader 直接读当前 tile 颜色，零带宽——用于自定义 blend、deferred、post-process chain。
7. **EGL Swap Behavior**：保持 `EGL_BUFFER_DESTROYED`（默认）；`EGL_BUFFER_PRESERVED` 每帧强制 DRAM→Tile reload。

## 代码模式

```cpp
// ✅ PBO 异步回读（替代 glReadPixels 同步）
glBindBuffer(GL_PIXEL_PACK_BUFFER, pbos[current]);
glReadPixels(0, 0, w, h, GL_RGBA, GL_UNSIGNED_BYTE, nullptr);  // 异步
current ^= 1;
// 下一帧 map 上一个 PBO 取数据

// ✅ Fence sync（替代 glFinish）
GLsync f = glFenceSync(GL_SYNC_GPU_COMMANDS_COMPLETE, 0);
glClientWaitSync(f, GL_SYNC_FLUSH_COMMANDS_BIT, timeoutNs);
glDeleteSync(f);
```

**带宽估算公式：**
```
每 attachment 每帧带宽 = width × height × bytesPerPixel × (loads + stores)
例：1080×1920, RGBA8, 1 load + 1 store = ~16.6 MB/attachment/frame
60 FPS → ~995 MB/s per attachment
Invalidate depth+stencil → 省 ~1.2 GB/s
```

## 常见陷阱

| 陷阱 | 后果 | 修正 |
|:-----|:-----|:-----|
| 渲染循环中 `glReadPixels` 到 CPU buffer | 全管线 stall + tile flush | PBO 双缓冲异步 |
| `glFinish()` 做同步 | CPU/GPU 串行化，帧率暴跌 | `glFenceSync` |
| FBO A→B→A→B 频繁切换 | 每次 Store+Load | 按 target 排序 draw call |
| `EGL_BUFFER_PRESERVED` 无需却开启 | 每帧全屏 DRAM→Tile reload | 保持 `EGL_BUFFER_DESTROYED` + 全量重绘 |
| 后处理多个全屏 pass 不合并 | N× 全屏带宽 | 合并 bloom+tonemap+FXAA 到一个 shader |

## GPU 差异速查

| GPU | Tile 大小 | 特殊点 |
|:----|:----------|:-------|
| ARM Mali | 16×16 | `glInvalidateFramebuffer` 极关键；forward + FB fetch 优于 deferred |
| Qualcomm Adreno | 32×32~128×128 | FlexRender 动态选 TBDR/Immediate；GMEM Load/Store 术语 |
| PowerVR | 32×32 | 真 deferred (HSR)；overdraw 几乎零 fragment cost，但带宽仍关键 |

## 关联卡片

- [04-framebuffer-objects](04-framebuffer-objects.md) — FBO clear/invalidate 生命周期
- [09-overdraw-fillrate](09-overdraw-fillrate.md) — Overdraw 优化
- [14-adreno-gmem-vrs-lrz](14-adreno-gmem-vrs-lrz.md) — Adreno GMEM 细节
- [13-mali-pls-multiview](13-mali-pls-multiview.md) — Mali PLS 零带宽 G-Buffer
