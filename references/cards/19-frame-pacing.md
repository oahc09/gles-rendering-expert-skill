# 帧节奏 — Swap Interval / Choreographer / Swappy

> **Category**: Presentation | **GLES Version**: All | **Source**: `references/rules/frame-pacing.md`

## 核心规则

1. **平滑 = 呈现时机，不只是帧率**。渲染快但呈现节奏不稳，观感比稳定 30 FPS 更差。
2. **不要依赖 `eglSwapInterval` 做节奏控制**——Mali/Adreno/PowerVR 驱动行为不一致，多数会钳制或忽略；保持 1，禁止 0。
3. 用 **`AChoreographer_postFrameCallback64`** 对齐 vsync 驱动逐帧更新，动画时间取 vsync 时间戳而非系统时钟。
4. 生产环境优先 **Swappy（games-frame-pacing）**：自动检测 60/90/120/144Hz，`SwappyGL_init/setWindow/swap` 接管呈现；显式设置目标周期，别盲目用自动值。
5. **缓冲不是越多越好**：三缓冲是默认，多加缓冲增加延迟不增加平滑度。
6. 帧超时先**降负载**（动态分辨率/特效分级），别让节奏库与超预算帧硬扛。
7. Swappy 仅 Android；Windows/ANGLE 用 `eglSwapInterval(1)`。

## 代码模式

```cpp
// ✅ vsync 驱动帧循环
void OnVsync(long long frameTimeNanos, void* data) {
    auto* app = static_cast<App*>(data);
    app->Update(frameTimeNanos);   // 用 vsync 时间做动画
    app->Render();                 // 绘制 + SwappyGL_swap / eglSwapBuffers
    AChoreographer_postFrameCallback64(
        AChoreographer_getInstance(), OnVsync, app);
}
```

## 常见陷阱

| 陷阱 | 后果 | 修正 |
|:-----|:-----|:-----|
| 高 FPS 但明显卡顿 | 呈现节奏不稳 | Choreographer/Swappy 对齐，Perfetto 查帧时间线 |
| `eglSwapInterval(0)` | 撕裂 | 强制 1 |
| 120Hz 屏锁 60 | 浪费高刷 | Swappy 自动检测 / 查询刷新率 |
| 用 sleep 自由循环 | 与 vsync 错位抖动 | AChoreographer 回调 |
| 加缓冲治卡顿 | 延迟增大无收益 | 降低单帧成本 |

## 关联卡片

- [08-tbdr-bandwidth](08-tbdr-bandwidth.md) — 单帧成本优化
- [18-gpu-profiling-toolchain](18-gpu-profiling-toolchain.md) — 帧时间线测量
- [10-msaa-antialiasing](10-msaa-antialiasing.md) — 帧预算中的 MSAA 成本
