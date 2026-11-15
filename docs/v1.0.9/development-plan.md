# GLES Rendering Expert Skill v1.0.9 完整开发任务书

- **计划日期**：2026-11-08
- **目标仓库**：https://github.com/oahc09/gles-rendering-expert-skill
- **唯一目标版本**：`v1.0.9`；工作包可拆分 PR，但不拆分版本发布
- **研究窗口**：2026-08-11—2026-11-08（含首尾，共 90 天）；历史高价值技术独立标记 `HISTORICAL_CONTEXT`
- **任务性质**：开发规划，不代表代码已修改、性能已验证或版本已发布
- **定位**：Mobile GPU Workload Intelligence & Evidence-Based Optimization

## 0. 结论与范围边界

v1.0.9 要把已有 GLES 规范、GPU Trace、RenderGraph、材质、驱动兼容、鲁棒性测试等模块连接成 **场景输入 → GPU 工作负载特征 → 假设与候选优化 → 受控 A/B 实验 → 画质/性能/功耗判定 → 证据归档与安全回退** 的工程闭环。

与 v1.0.5 的运行时自适应画质不同，本版主要针对 **离线分析、开发期优化、CI 回归与跨设备迁移**，不重新实现动态分辨率控制；与 v1.0.8 的 Fuzzing/鲁棒性不同，本版不重新建设故障生成器，而是复用它保障优化变更安全。

### 实际仓库基线（2026-11-08 检查）

- 已读取 `SKILL.md`，其 metadata 仍为 `1.0.2`，并包含 v1.0.7 的候选路由；`README.md` 记录 v1.0.7 的候选实现和 172 条累计 Agent 任务。
- `docs/v1.0.7-development-plan.md` 已存在；当前默认分支上未找到 `docs/v1.0.8-development-plan.md`，不能假定 v1.0.8 已实现或发布。
- 先核查实际 HEAD、tag、分支、PR、CI、发布门禁、工作区差异；继承全部未关闭门禁，不因开发 v1.0.9 将旧版本未验收项标记 PASS。
- 不修改原有 Skill 触发条件、模型路由、平台支持、GLES 版本边界；不引入新的硬性第三方运行时依赖，优先复用现有 Python/C++17/GLSL 工具。

## 1. 90 天技术研究与证据

### 1.1 已核实且可作为本版工程参考的上游变化

| 来源 | 原始日期 | 证据性质 | 对 v1.0.9 的作用 |
|---|---|---|---|
| Perfetto v59.1 | 2026-10-27 | 官方 Release；含 Trace Processor agent mode、GPU draw-call stage slices、重启后 trace 恢复等 | 复用现有 Trace 适配层，增量接入更细粒度 draw-call 与长时追踪；可用性需按设备和数据源探测 |
| Filament v1.78.0 | 2026-10-13 | 官方 GitHub Release，确认版本与 Android 构建产物 | 作为移动渲染工程基线与差分研究对象；**不能仅凭版本发布宣称某项 GLES 性能提升** |
| Khronos OpenGL ES CTS 3.2.14.x | 2026-03 起，最新 3.2.14.1 为 2026-07-21 | 历史规范参考，不属于本轮 90 天新增 | 复用 GLES 合法性、错误行为和一致性测试设计，不将 Vulkan CTS 当作 GLES 功能 |

来源：
- https://github.com/google/perfetto/releases/tag/v59.1
- https://github.com/google/filament/releases/tag/v1.78.0
- https://github.com/KhronosGroup/VK-GL-CTS/releases
- https://github.com/KhronosGroup/VK-GL-CTS/wiki/Overview-of-releases

### 1.2 持续检索范围

- GitHub：ANGLE、Mesa Freedreno/Panfrost/etnaviv、Filament、Perfetto、Android GPU Inspector、RenderDoc、Khronos VK-GL-CTS、glslang、KTX-Software、Arm Mobile Studio 公开资料。
- 官方资料：Khronos GLES/EGL/GLSL Registry、Android Graphics/ADPF、Arm Mali、Qualcomm Adreno、Imagination PowerVR。
- X：只接收有原始帖子、日期、作者、源代码/复现或设备计数器的案例；未核实帖子只进入候选，不形成强制规则。
- 每个候选记录 `source_url`、`event_date`、`discovered_at`、`platform`、`gpu`、`driver`、`gles_version`、`evidence_class`、`affected_rules`、`repro`、`decision`、`test_id`。
- 区分 `SPEC_CONFIRMED`、`SOURCE_CONFIRMED`、`REPRODUCED`、`MEASURED_ON_DEVICE`、`UNVERIFIED`、`REJECTED`；**没有计数器不能声称已经测得带宽下降**。

## 2. W0–W10 开发工作包

### W0 — 基线审计与复用映射（P0）

**任务**：核查 HEAD/tag/PR/CI/文件差异，盘点已有 DeviceLab、SceneLab、Trace SQL、RenderGraph、Shader A/B、Agent Benchmark、Fuzz/Reducer；按 `EXISTS_VERIFIED / EXISTS_UNVERIFIED / MISSING` 标记。建立前序版本未验收依赖清单。

**交付**：`docs/v1.0.9/baseline-gap.md`、`docs/v1.0.9/inherited-gates.json`。

**验收**：每条继承能力都有真实路径和复现命令；未覆盖现有文件；无未经授权提交、推送或发布。

### W1 — GPU Workload Fingerprint（P0）

**任务**：定义场景指纹 `WorkloadFingerprint`：分辨率、帧耗时分布、CPU submit、GPU stage、纹理读写量（若有）、像素覆盖估算、混合层数、Draw/Dispatch、FBO 切换、采样格式、资源大小、热状态、Trace 可用性。

分类候选：`CPU_SUBMIT`、`BANDWIDTH`、`FRAGMENT_ALU`、`OVERDRAW_BLEND`、`VERTEX_GEOMETRY`、`COMPUTE`、`SYNC`、`UPLOAD`、`THERMAL`、`UNKNOWN`。允许多标签、置信度与证据缺失，禁止只凭单一 GPU utilization 断定根因。

**交付**：`benchmarks/workloads/schema.json`、`tools/workload_fingerprint.py`、至少 12 个有标签的真实或合成输入样本（分别标识）。

**验收**：缺失 counter 时输出 `UNKNOWN` 与所需下一步采集；相同输入输出确定；能正确识别 CPU 与 GPU 时间重叠及不同时间基准。

### W2 — TBDR 成本模型与校准（P0）

**任务**：建立附件级带宽上下界模型、Tile Load/Store、clear/invalidate、MSAA resolve、FBO 切换、纹理采样、Overdraw 的**估算模型**。模型输入包含格式、宽高、sample count、生命周期和已知驱动条件；不假设所有 GPU 都按同一 tile 大小或行为运行。

**交付**：`references/optimization/tbdr-cost-model.md`、`tools/estimate_gpu_cost.py`、至少 12 组边界/反例；可选设备校准配置。

**验收**：估算结果明确区分理论上界/下界/未知；与真实计数器对比时输出误差及适用设备；不以字节计算直接等同于实际 DRAM 传输。

### W3 — Shader A/B 优化实验（P0）

**任务**：复用 v1.0.7 Shader Variant 和 v1.0.4 Trace，构造条件分支 vs branchless、`highp` vs `mediump`、纹理采样合并、UBO/SSBO 访问、纹理格式、discard/depth、计算与绘制融合等实验。每个实验保留基线、优化版、反例和 Shader 源码哈希。

**交付**：`benchmarks/shader_ab/`，至少 16 组受控实验（包含预期无收益或退化）；Shader 编译/链接和图像数值验证。

**验收**：功能/画质不合格直接拒绝性能候选；设备数据缺失只能输出 `NOT_MEASURED`，不能伪造加速比。

### W4 — 高重叠透明与屏幕空间负载（P0）

**任务**：覆盖 Gaussian Splatting/3DGS、透明粒子、玻璃、雨滴、体积近似、层叠 UI。构建屏幕分块统计：投影面积、混合层数、颜色/Alpha 分布、深度范围、背景贡献、可感知误差。研究背景 Gaussian 合并/LOD、透明分组、远景分辨率、前景边界保留；明确透明排序及视觉正确性限制。

**交付**：`benchmarks/overlap_scenes/`，至少 4 个可运行 GLES 场景；含 1 个高重叠 Gaussian/精灵代理场景和 1 个多层透明玻璃场景；空间热力图与 A/B 数据。

**验收**：每种简化必须验证轮廓、视差、Alpha、颜色误差和动态相机；减少 draw calls 不等于减少实际像素覆盖，需分别报告。

### W5 — RenderGraph 优化建议器（P1）

**任务**：复用现有 Graph Checker，增加候选 Pass fusion、附件 transient 化、FBO 复用、MSAA resolve 路径、PostFX 缩放建议；保留语义和同步依赖，不自动修改业务渲染器。

**交付**：`tools/rendergraph_optimizer.py`、至少 10 组合法/非法/不值得优化案例。

**验收**：建议包含前置条件、收益假设、风险、fallback、可运行验证；对危险 feedback、丢失 attachment、错误 barrier 必须拒绝。

### W6 — 纹理与内存访问局部性（P1）

**任务**：基于已有 KTX2/ASTC/ETC2 管线，研究纹理分辨率、Mip、各向异性、纹理阵列/Atlas、PBO 上传与纹理采样局部性对帧时间、带宽和画质的影响；记录格式扩展支持与 transcoder 成本。

**交付**：至少 8 个纹理访问实验与资源质量报告。

**验收**：不把纹理压缩比直接当作显存或带宽收益；计入 CPU 转码时间、上传卡顿、驻留内存与画质损失。

### W7 — 证据约束的优化决策引擎（P0）

**任务**：输入指纹、设备能力、Trace、画质预算、性能目标，输出排序后的候选优化；排序考虑预计收益范围、实施成本、回归风险、置信度、证据完整性。规则优先，避免引入不可解释的黑盒模型。

状态：`RECOMMENDED_FOR_EXPERIMENT`、`VERIFIED_IMPROVEMENT`、`NO_GAIN`、`REGRESSION`、`INSUFFICIENT_EVIDENCE`、`REJECTED_BY_QUALITY`。

**交付**：`tools/optimization_advisor.py`、可审计的 JSON 报告、至少 20 个决策正负案例。

**验收**：不能以模型预测替代真机测量；所有推荐必须指向对应实验；收益为负、画质失败或证据不足时不能自动接受。

### W8 — 跨 GPU 可移植性与设备策略（P1）

**任务**：建立 Mali、Adreno、PowerVR、ANGLE（及可用的 Mesa）之间的 A/B 数据比较协议；按 GPU 型号、驱动、后端、API 版本、热状态分组；设备不可用时仅保留 `NOT_RUN` 配置。

**交付**：`benchmarks/device_portability/`、设备矩阵、策略适用条件和回退路径。

**验收**：禁止从单设备数据推广“所有 Mali/Adreno”；至少完成一条真实设备 A/B 才能宣称实测收益，跨厂商对比不足时明确阻塞。

### W9 — Agent 优化 Benchmark（P0）

**任务**：新增至少 30 个不重复的 Agent 任务：诊断瓶颈、生成优化补丁、验证合法性、执行实验、解释负收益、回退。复用已有无 Skill/有 Skill 配对 Runner 与独立判分体系。

**交付**：`benchmarks/agent/V109_CASES.md`、任务数据集、判分规则、失败分析报告。

**验收**：分别统计诊断准确率、误报率、编译/运行成功率、画质通过率、实测收益比例、无证据收益宣称率；Fixture 测试不能替代真实模型调用。

### W10 — 90 天技术雷达、CI 与统一发布（P0）

**任务**：扩展现有 Radar（不另造独立框架）；每周增量、每月滚动 90 天；维护 source → claim → experiment → rule → test；CI 加入 schema、静态规则、Shader 编译、软件 EGL、A/B 控制、Advisor 反例、Agent Runner 单测。真机测试独立门禁，不得由软件渲染替代。

**交付**：`docs/v1.0.9/research/`、`docs/v1.0.9/traceability.md`、`docs/v1.0.9/release-gates.json`、CHANGELOG/README 增量更新。

**验收**：所有前序门禁保留；明确 `PASS / PARTIAL / BLOCKED_BY_HARDWARE / BLOCKED_BY_PROVIDER / NOT_RUN`；版本元数据和 tag 仅在全部验收且明确授权后变更。

## 3. 推荐验收场景

| ID | 场景 | 必须比较的证据 |
|---|---|---|
| S01 | 100 万级高重叠透明代理（按能力分档） | 覆盖热力图、混合层数、画质误差、GPU time |
| S02 | 玻璃/水滴多层透明 | Alpha、排序、轮廓误差、带宽/帧耗时 |
| S03 | 2D UI + 3D + PostFX | FBO 切换、附件 load/store、画质 |
| S04 | 粒子 Compute + Render | barrier 正确性、同步时间、帧时间 |
| S05 | HDR/SDR 双路径 | 色彩空间、量化误差、ToneMap 正确性 |
| S06 | 纹理 Streaming + ASTC/ETC2 | 纹理驻留、上传卡顿、画质 |
| S07 | Mali/Adreno 差异策略 | 驱动条件、相同场景 A/B、反例 |
| S08 | 负收益优化自动回退 | 功能正确、质量门禁、状态回退 |

## 4. 统一数据契约

```json
{
  "schema_version": "1.0",
  "workload_id": "S01",
  "build_sha": "<actual commit>",
  "device": {"model": null, "gpu": null, "driver": null, "os": null},
  "backend": "GLES_3_1",
  "resolution": [1080, 2400],
  "source_evidence": [],
  "metrics": {"cpu_ms": null, "gpu_ms": null, "frame_p95_ms": null, "dram_bytes": null},
  "quality": {"golden_id": null, "thresholds": {}, "pass": null},
  "hypothesis": "reduce background overdraw",
  "status": "INSUFFICIENT_EVIDENCE",
  "artifacts": []
}
```

注意：空值代表未测量，绝不能默认填零；所有指标标注采集工具、单位、样本数、温度/频率状态和原始 trace 引用。性能比较应采用多轮交错 A/B、预热与稳定热状态，记录中位数和分布（例如 p50/p95），避免只比较一次 FPS。

## 5. PR 拆分与依赖

| PR | 范围 | 依赖 |
|---|---|---|
| PR-01 | W0 + W1 指纹和数据契约 | 无 |
| PR-02 | W2 成本模型 + W3 Shader A/B | PR-01 |
| PR-03 | W4 高重叠场景 + W6 纹理实验 | PR-01 |
| PR-04 | W5 RenderGraph 优化建议器 | 复用 v1.0.7 |
| PR-05 | W7 决策引擎 + W8 跨 GPU 数据协议 | PR-02/03/04 |
| PR-06 | W9 Agent Benchmark + W10 CI/研究/文档 | PR-05 |

全部 PR 属于一个 `v1.0.9` 开发周期。PR 只表示实施拆分，当前规划不授权创建、合并、提交、推送或发布。

## 6. 发布 DoD

- [ ] W0 基线与前序发布门禁已核查，旧规则和触发条件保持兼容。
- [ ] 至少 12 个工作负载指纹样本；无计数器场景能够输出不确定性。
- [ ] TBDR 成本模型至少 12 组边界/反例，并明确估算与实测区别。
- [ ] Shader A/B 至少 16 组；至少 4 个高重叠场景和 8 个纹理实验。
- [ ] RenderGraph 建议器至少 10 组测试，优化决策引擎至少 20 组正负案例。
- [ ] 8 个端到端场景包含质量/正确性/性能证据或明确 `NOT_RUN`。
- [ ] 新增至少 30 个 Agent Benchmark 任务，真实模型结果与 fixture 结果分离。
- [ ] 研究资料覆盖滚动 90 天并完成去重；无充分证据的 X 内容不写成事实。
- [ ] CI、构建、Shader、软件 EGL、跨平台兼容性和回退机制完成约定检查。
- [ ] 真机性能结论必须有原始 Trace、设备/驱动/热状态；未取得则保留硬件阻塞。
- [ ] 不得绕过 v1.0.3–v1.0.8 继承的发布门禁；明确授权后才更新版本、tag、Release。

## 7. Agent 执行提示词

> 在 `oahc09/gles-rendering-expert-skill` 仓库中实施 `GLES Rendering Expert Skill v1.0.9 完整开发任务书`。先审计工作区差异、HEAD/tag/PR、现有 v1.0.3–v1.0.8 代码和 release gates，禁止覆盖已有修改。只做增量实现，保留 SKILL.md 的原有模型路由、GLES 3.0/3.1/3.2 边界、Android/ANGLE/Embedded Linux 支持。按 W0–W10 执行并复用现有 DeviceLab、SceneLab、Trace SQL、RenderGraph、Reducer、Agent Runner。每个优化必须区分假设、估算、软件正确性、真实 GPU 实测；对缺失数据报告 UNKNOWN/NOT_RUN。交付完整测试、对照实验、研究证据和发布门禁。未经明确授权不得提交、推送、合并、打 tag 或发布。

## 8. 状态说明

本文件只完成规划。未在当前会话中执行 C++17/Shader 编译、真机性能测量、真实 Agent 配对测试或 GitHub 写入。GitHub 默认分支中 v1.0.7 是候选实现；v1.0.8 尚未在默认分支确认，必须实施前再次核对。
