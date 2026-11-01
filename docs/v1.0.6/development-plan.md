# GLES Rendering Expert Skill v1.0.6 全量开发任务计划书

- 日期：2026-11-01
- 仓库：https://github.com/oahc09/gles-rendering-expert-skill
- 唯一目标版本：`v1.0.6`，工作包不拆成其他发布版本。
- 任务属性：规划，不代表已实现或验收。
- 版本前置：核查 `main` SHA、最近标签、PR、发布门禁及未提交文件。当前可读 `SKILL.md` 仍标记 `1.0.2`，`docs/release-gates.json` 仍记录 `v1.0.3` `release_ready=false`；不能把 v1.0.4/1.0.5 视为已发布。既有成果先复用，缺口单列，不覆盖旧规则。

## 1. v1.0.6 定位

从 v1.0.3 的规则/验证、v1.0.4 的单帧 GPU 诊断、v1.0.5 的持续性能与画质，升级到跨 API/跨 Surface 的系统级工程、高级效果的正确性、真实驱动兼容与最小故障复现。范围以 GLES 3.0/3.1/3.2 + EGL 为主体；Vulkan 作为互操作或比较对象，不将 Vulkan API 伪装为 GLES 能力。

## 2. 交付工作包

| 包 | 工作内容 | 主要交付 | 最低验收 |
|---|---|---|---|
| W0 | 基线与已有版本去重 | gap-matrix、基线 SHA、前置风险台账 | 明确实际已实现/未验收/未实现 |
| W1 | GLES ↔ Vulkan / Android 硬件缓冲跨 API 互操作 | AHardwareBuffer/EGLImage/原生 fence/格式约束/ownership playbook + 双端实例 | 同设备写→读、同步、释放、异常回退正确；不支持时安全退出 |
| W2 | Android 多 Surface/多 EGLContext | Java SurfaceView/WallpaperService 入口、C++17 EGL 状态机、共享资源 registry | 2～4 Surface 生命周期交错、resize、pause/resume、context loss 测试，资源无误用 |
| W3 | GLES 3.1 Compute 高级仿真 | SSBO、image load/store、memoryBarrier、ping-pong 的粒子/水波/Boids 样例 | 与 CPU reference 误差可控；ES 3.0 fallback；跨驱动可重复 |
| W4 | GPU/Driver 兼容知识库 | 设备 probe JSON、known issues、workaround 条件、最小复现集 | 所有 workaround 有环境条件、来源、复现、撤销条件；无凭据收集 |
| W5 | 透明/折射/液态效果 | weighted blended OIT（说明限制）、排序透明、屏幕空间折射、厚度近似 | 至少 3 场景（玻璃、流沙、粒子），有画质基线/性能预算及正确 fallback |
| W6 | 高级光照与水体 | Forward+ 复用增强、PCF/CSM、近似焦散和屏幕空间深度效果 | 2 场景，明确移动端 pass、附件/带宽估计及视觉差异 |
| W7 | 纹理资源/外部视频管线 | KTX2/Basis transcoding、ASTC/ETC2 fallback、YUV external image、可选 protected content | 一套资源多 GPU 选择路径、质量/加载峰值/内存报告；受保护内容不做非法读回 |
| W8 | 数值/颜色正确性 | FP16/FP32、mediump/highp、sRGB/线性、预乘 alpha、HDR→SDR 基准 | 至少 12 组图像/数值正负例，独立区分输入精度、ALU、blend/附件量化 |
| W9 | 自动化最小化故障复现 | Shader reducer（可复用外部工具）、GL state snapshot、FBO fixture、capture replay 引导 | 10 个已知失败样本可稳定最小化、复现/无法复现均可审计 |
| W10 | Agent Benchmark 2.0、CI、研究雷达 | Generate/Review/Diagnose/Optimize 复杂用例、跨设备报告、发布门禁 | 30 条新增高难用例；真实模型对照与硬件结果分层，不伪造 |

## 3. 重点设计

### W1 跨 API 互操作
- 能力探测：Android API level、AHardwareBuffer usage/format、EGL/GL extensions、Vulkan external-memory & external-semaphore feature bits、受保护内容限制。
- 同步：生产者完成 → export/import fence → 消费者 wait → 归还；区分 CPU fence 与 GPU fence；不得在未同步时读写。
- Ownership：buffer、EGLImage、texture、fd、semaphore、context 的生命周期表，使用后关闭 fd，不重复 close、不在无效 context 释放 GL 名称。
- Fallback：CPU staging / GLES-only / Vulkan-only，标注额外拷贝开销。
- 禁止假设 GL_EXT_memory_object_fd / semaphore_fd 在 Android 普遍可用；以能力探测为准。

### W2 多 Surface
- 最小 Android Java（不使用 Kotlin）项目展示 2 个 SurfaceView；WallpaperService 为可选独立入口。
- 单线程/多线程两个调度模型、共享组与不共享对象名单、ContextLost/SurfaceLost 分离处理。
- 交错事件注入：连续创建/销毁、尺寸变化、锁屏/解锁、后台返回、快速切换。
- Frame scheduling/BufferQueue/SurfaceFlinger 可用 Perfetto 证据；不能将 Vulkan 的 pre-rotation 机制直接移植到 GLES。

### W3 Compute
- ES 3.1 compute 使用 dispatch、SSBO、image barriers、read/write hazards、GPU→draw 的 barrier；ES 3.0 使用 transform feedback/CPU fallback。
- Boids 规模、流体水波格点、粒子碰撞分别提供 deterministic seed 和 CPU reference。
- 记录每个 pass 的资源读写依赖，不宣称 compute 一定比 fragment 管线快。

### W4 硬件差异
- 至少涵盖 Mali、Adreno、PowerVR，以及可获取的 Vivante/ANGLE/软件驱动样本。
- 每个 workaround：vendor、renderer、driver、OS、extension predicates、symptom、minimal reproducer、source、confidence、regression tests、expiry。
- 设备模型不作为唯一身份，禁止仅凭设备品牌推断 GPU。

### W5/W6 渲染特效
- 以真实移动端的 pass 数、tile load/store、混合精度、深度与 MSAA 兼容性限制设计。
- 透明叠加不假定 weighted-blended OIT 物理正确；提供排序透明对照。
- 画质证据包括参考图、误差掩码、相同曝光与输出色彩空间；性能证据必须来自真实设备。

### W7/W8 资源与精度
- KTX2/Basis Universal 需 runtime transcoder，压缩容器本身不会自动让 GLES 支持全部格式。
- 视频/相机输入检查 `GL_TEXTURE_EXTERNAL_OES`、扩展和 `samplerExternalOES` 变体、YUV 色域/范围/旋转。
- protected content 需同时检查 surface/context/texture 支持；禁止 CPU readback 和明文导出。
- 精度测试分开量化纹理采样、shader ALU、FBO 格式、融合、颜色管理，不把 CPU 浮点结果直接当 GPU 精确规格。

### W9/W10 Agent 闭环
- 每条 Bug：环境快照 → 复现输入 → 失败判据 → 最小化 → 规则定位 → patch → 可执行回归 → 若涉及性能则同机 A/B。
- Agent 最低 30 条高难案例，含正例/反例、跨版本边界、扩展缺失、GPU 厂商条件、反事实优化。
- 指标：compile/link/pass 通过率、正确修复率、误报率、修复引入回归率、分析证据完整性；性能改进单列。

## 4. 近 30 天技术研究 (2026-10-03 ～ 2026-11-01，UTC)

数据源：Khronos GLES 注册表及 VK-GL-CTS 的 `opengl-es-cts-*`；Android 官方图形/NDK；ANGLE Chromium upstream；Filament；KTX-Software；Mesa Panfrost/Freedreno/etnaviv；Arm/Qualcomm/Imagination 官方文章和 SDK；GitHub 有发布日期的 PR/release/commit；X 原始帖（原文日期、源码/演示、二次核验）。

已知可采用的工程参考（不冒充最近 30 天新增）：
- Khronos KTX-Software：KTX2 / Basis Universal 载入及转码：https://github.com/KhronosGroup/KTX-Software
- Google Filament Android GLES 平台实现：AHardwareBuffer→EGLImage 及受保护内容能力条件：https://github.com/google/filament/blob/main/filament/backend/src/opengl/platforms/PlatformEGLAndroid.cpp
- Khronos CTS releases，GLES CTS 与 Vulkan CTS 分开识别：https://github.com/KhronosGroup/VK-GL-CTS/releases
- Android 性能工具和帧同步：https://developer.android.com/games/optimize/vitals/slow-session

每条技术变化必须包含 `event_at`、`published_at`、`source`、`evidence_level`、`gpu/API/version`、`test`、`decision`、`affected_rules`。若近 30 天无可验证实质新技术，明确写无，绝不从老版资料编造本月更新。X 帖只作为候选线索，未经证据支持不可直接变成 MUST 规则。

## 5. 实施顺序和 PR

1. PR-A W0 + W1/W2：基线、系统级多 Surface、资源互操作。
2. PR-B W3/W4：Compute + 硬件驱动矩阵。
3. PR-C W5/W6：高级效果场景与可视化基线。
4. PR-D W7/W8：资源格式、视频与精度基准。
5. PR-E W9/W10：故障最小化、Agent 对照与 CI 门禁。
6. Final Integration：回归、文档与单版本发布候选。

各 PR 可以在无冲突文件下并行，统一基线和 schema；任何依赖设备/模型的 gate 未完成，显式保持 BLOCKED，不自动将其标 PASS。未经授权不 merge、push、tag、deploy。

## 6. 最终 DoD

- [ ] 基线、HEAD/tag、前序交付状态真实核实；差异清单与旧规则保留。
- [ ] W1/W2 提供 Android Java + C++17 完整构建、EGL 生命周期、多 surface/共享资源真实验收。
- [ ] W3 GPU/CPU 同数据输出；不同 ES 能力路径明确；缺扩展 fallback。
- [ ] W4 兼容库中每个已确认问题都可复现，workaround 有版本范围与回退。
- [ ] W5/W6 有 ≥5 个高级渲染场景与 Golden Image，且至少 1 个覆盖真实交互。
- [ ] W7/W8 有压缩纹理/视频/颜色路径的实测记录与精度边界。
- [ ] W9 至少 10 个稳定复现案例，W10 至少 30 条新增 Agent Benchmark。
- [ ] 真实 Android GLES 真机至少 1 台，覆盖 Mali/Adreno/PowerVR 的不可用设备标 BLOCKED，不宣称全覆盖。
- [ ] 所有提交伴随 CI、许可证检查、测试报告、证据归档与 CHANGELOG；发布单一 `v1.0.6`。

## 7. 执行 Agent 提示词

> 请在 `oahc09/gles-rendering-expert-skill` 真实仓库按本 `v1.0.6` 任务书实施。先检查当前 HEAD、tags、PR、未提交修改、版本和已有 W 包能力，做 gap matrix，严禁重复造轮子。遵循现有 `SKILL.md` 与 repo 风格，保留旧规则和触发条件。对每个 W 包提供代码、最小复现、测试、规范证据与不支持 fallback。按 PR-A～E 逐步交付，发布前执行完整 Gate；无设备/Provider 时标为 BLOCKED，不能以软件模拟代替真机，也不能伪造收益。任何提交/推送/合并/标签仅在当前授权范围内进行。
