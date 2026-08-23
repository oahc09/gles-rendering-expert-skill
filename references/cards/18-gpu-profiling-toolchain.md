# GPU 性能分析工具链 & 诊断流程

> **Category**: Tooling | **GLES Version**: All | **Source**: `references/rules/profiling-tools.md`

## 核心规则

1. **先确认 GPU 型号**（`glGetString(GL_RENDERER)`）再选工具：Mali→Streamline，Adreno→Snapdragon Profiler，PowerVR→PVRTrace/PVRPerf，通用→AGI/Perfetto。
2. Windows/ANGLE 环境无移动端工具——用 RenderDoc 抓帧 + ANGLE debug layer。
3. **禁止在 Android 模拟器上做带宽/填充率分析**——它是宿主 immediate-mode 后端。
4. 每个优化必须附带前后计数器对比（设备型号 + 驱动版本），不做无设备限定的绝对断言。
5. 诊断遵循固定流程：Symptom → Triage(CPU/GPU) → Counter → Classify → Map to Rule → Fix → Verify。

## 工具速查

| 工具 | 适用 | 核心指标 |
|:-----|:-----|:---------|
| ARM Streamline | Mali | 外部带宽、fragment 周期、tile 占用 |
| AGI / Perfetto | 全平台 Android | GPU 时间线、频率、热状态 |
| Snapdragon Profiler | Adreno | GMEM 利用率、LRZ 效率、UCHE 命中 |
| PVRTrace/PVRPerf | PowerVR | HSR 效率、SPM 事件、ISP/USC 负载 |
| RenderDoc | Windows/ANGLE | 逐 draw call 状态/资源检查 |
| GL_KHR_debug | 全平台 | 驱动告警（debug 构建常开） |

## 瓶颈分类表

| 观察 | 分类 | 首选动作 |
|:-----|:-----|:---------|
| GPU 忙 + 带宽高 | 带宽瓶颈 | 审计 clear/invalidate 覆盖 |
| GPU 忙 + 带宽低 + fragment 周期高 | 填充/ALU | 降 overdraw、简化 shader、VRS |
| GPU 不忙但帧时长高 | CPU/同步 | 查 `glFinish`、fence 阻塞、draw call 数 |
| 周期性尖峰 | 热/加载 | Perfetto 热轨道、资源流式加载审计 |

## 常见陷阱

| 陷阱 | 后果 | 修正 |
|:-----|:-----|:-----|
| 模拟器上测带宽 | 数据完全无效 | 真机测量 |
| 不锁热状态对比 | 前后数据不可比 | 冷却间隔 + 记录频率 |
| 只凭肉眼判断优化效果 | 结论不可靠 | 同组计数器前后对比 |
| 忽略 `GL_KHR_debug` 告警 | 错过驱动提示的带宽问题 | debug 构建开回调 |

## 关联卡片

- [08-tbdr-bandwidth](08-tbdr-bandwidth.md) — 带宽优化规则
- [09-overdraw-fillrate](09-overdraw-fillrate.md) — Overdraw 分析
- [11-synchronization](11-synchronization.md) — 同步阻塞诊断
