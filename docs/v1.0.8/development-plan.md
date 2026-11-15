# GLES Rendering Expert Skill v1.0.8 全量开发任务书

- **规划日期**：2026-11-07
- **目标仓库**：https://github.com/oahc09/gles-rendering-expert-skill
- **唯一目标版本**：`v1.0.8`；内部拆分工作包与 PR，不拆分版本号。
- **技术研究窗口**：2026-08-10 至 2026-11-07，含首尾共 90 天；窗口以外的重要基础资料必须显式标记 historical-context。
- **本轮性质**：规划与诊断，不包含修改、提交、推送、部署或发布授权。

## 0. 结论与差异定位

将 Skill 从“能够生成、审查和分析 GLES 渲染管线”提升为“能够对 GLES/EGL/Shader 进行生产级对抗验证、跨驱动差异测试、故障归因与最小化复现”的工程专家。与先前版本的分工：

| 版本 | 已规划方向 | v1.0.8 不能重复做的事情 |
|---|---|---|
| v1.0.3 | API 约束、基础编译/校验、Agent 基线 | 不重新搭一个正则规则测试器 |
| v1.0.4 | 场景 Benchmark、Trace、修复闭环 | 不重新搭 Trace CSV/JSON 分析器 |
| v1.0.5 | 30 分钟稳定性能、画质、精度 | 不重复开发热管理和自适应质量策略 |
| v1.0.6 | 跨 API、多 Surface、Compute、驱动适配、故障简化 | 复用现有 reducer 和设备能力矩阵 |
| v1.0.7 | Shader Variant/Material ABI/RenderGraph | 在既有系统上新增对抗测试，不重新实现管线 |
| **v1.0.8** | **Robustness / Differential / Fuzzing / Release Hardening** | **只增加新的验证深度、证据与实战案例** |

### 仓库核查（2026-11-07）

通过 GitHub 已读取：`SKILL.md` 的版本元数据仍为 `1.0.2`，并包含 v1.0.3–v1.0.6 candidate 入口；`README.md` 可见 v1.0.4、v1.0.3 候选说明；未在 `main` 查询到 `docs/v1.0.7-development-plan.md`。因此不能断言旧版本已发布，实施 v1.0.8 前必须以当前 HEAD、PR、tag、release gates 和测试报告重审。保留既有模型路由、触发条件、GLES 版本和平台范围。

## 1. 工作包与关键任务

### W0 — 基线、覆盖与依赖审计（P0）

**输入**：当前默认分支 HEAD；已有 `benchmarks/rules/`、`benchmarks/agent/`、`benchmarks/driver_compat/`、`benchmarks/reducer/`、`benchmarks/system_scenes/`、`tools/`；前序 release gate。

**任务**：
1. 读取工作区未提交改动、当前 branch/tag/PR、CI 和对应测试报告；不要覆盖用户文件。
2. 列出既有 Feature/Test ID，标识复用、扩展、新增，避免重写同类 harness。
3. 冻结 `base_sha`、测试工具与驱动版本、已有对照用例；建立 `docs/v1.0.8/coverage-diff.md`。
4. 前序 gate 如果阻塞，继承原状态；不能为了本版发布篡改为 PASS。

**DoD**：所有新增任务对应唯一能力缺口，100% 有前序映射和文件归属。

### W1 — GLSL ES Shader Fuzzing 与约束感知变异（P0）

**新增能力**：通过语法/AST/IR 感知的合法变换与无效输入生成检验 Shader 编译、链接和驱动一致性。

- 覆盖 `#version 300/310/320 es`；版本、扩展、precision、varying、UBO/SSBO、sampler、image、atomic、Compute 限制。
- **合法变异**：仅使用有证明的保持语义变换；shader 输入重排、常量折叠、layout 变换在规范允许条件下比较输出。
- **非法变异**：缺少扩展、非法类型组合、越级语法、超出静态资源限制；期望被编译器拒绝，不能误判成驱动 crash。
- 辅助工具可研究 `glslang`、`shaderc`、`SPIRV-Tools` 和既有 GraphicsFuzz 思路；注意 SPIR-V 是中间表示，不等于 GLES 原生支持 SPIR-V Shader。
- 设 seed、时间预算、最大 Shader 长度、编译超时、资源配额；对编译器崩溃与测试进程崩溃隔离。
- 出现差异后记录：输入源码、seed、GPU/driver、extension snapshot、编译日志、退出码、输出图像、期望规则。

**交付**：`benchmarks/fuzz/shaders/`、`tools/shader_fuzz.py`（具体命名以既有仓库风格为准）、最小种子库、报告 schema。

**DoD**：不少于 60 个稳定种子/变异组合；有效输入不能出现未经解释的编译错误；无效输入不能被归类为 GPU 性能退化；已知故障具备 replay 命令。

### W2 — GLES/EGL 状态机对抗测试（P0）

**新增能力**：基于显式状态模型的 API 调用序列生成和错误结果验证。

- 状态域：Context/Surface/Thread ownership、FBO/Renderbuffer/Texture、VAO/VBO/UBO、Program/Pipeline、Sync、Query、PBO。
- 对象生命周期变异：创建→绑定→删→重建、同名复用、跨 Context 非共享对象误用、状态缓存脏值、Framebuffer Attachment 拆卸。
- EGL 错误路径：`EGL_BAD_SURFACE`、`EGL_CONTEXT_LOST`、线程解绑、错误的 display/context/surface 组合；通过合法可控的模拟层做故障注入，不假装真机必须能强制触发 context loss。
- 测试必须区分：明确规定产生 GL/EGL 错误的非法调用、规范未定义行为、实现相关行为；禁止将不稳定未定义行为当作确定 oracle。
- 复用 v1.0.6 reducer 输出简化后的最短失败序列。

**交付**：`benchmarks/state_machine/`、状态转换规格、正负测试集合、故障序列 replay。

**DoD**：至少 40 条状态转换/边界案例，包含 10 条可重复的已知故障注入场景，主机 GLES/EGL 与可用真机分类验收。

### W3 — GPU Robustness、故障隔离与恢复（P0）

- 研究 `GL_KHR_robustness`、`GL_EXT_robustness`、`GL_KHR_debug` 等扩展的实际能力、函数入口与版本适用范围；逐设备探测，不推定必然可用。
- Resource exhaustion（可控内存预算）、编译资源耗尽、Shader watchdog 风险、超大纹理/SSBO/dispatch 工作量的安全上限。
- Render thread / worker thread 的 watchdog、取消、资源清理、受控重试；不以 `glFinish` 循环或高负载“烧机”作为默认测试。
- 通过离线模拟/替身测试验证 reset 回收路径；物理设备 reset 测试仅在可安全恢复的实验环境进行。
- 不将用户输入视为可信 Shader 或纹理：边界检查、尺寸溢出、内存预算、超时、文件大小和解码失败处理。

**DoD**：20 个鲁棒性案例；故障必须被报告为可区分的 `EXPECTED_ERROR`、`DRIVER_FAILURE`、`TEST_TIMEOUT`、`HARNESS_FAILURE`、`UNSUPPORTED` 等，所有资源清理路径有测试。

### W4 — RenderGraph / Material 的对抗验证（P0）

**前置依赖**：复用 v1.0.7 材质 ABI / RenderGraph 真实实现；未实现则记录 `BLOCKED_BY_PREDECESSOR`，不额外平行重建。

- 对 Pass DAG 做自动变异：删除/插入边、Attachment Alias 冲突、读写反馈、错误 `glMemoryBarrier`、样本数和色彩空间不一致。
- 对 Material ABI：layout offset、array stride、shader-version、Sampler 单元冲突、缺失 required uniform/extension 做静态 + 运行时负测。
- 资源别名安全性使用 reachability/liveness 判定；对跨 Context 同步提供明确 happens-before 证明。
- 对 IR 管线修改须生成最小的失败图结构、验证结果和替代修复建议。

**DoD**：至少 20 个对抗图案例 + 20 个 ABI 案例；合法图全通过，非法图明确报出冲突节点/资源和依据。

### W5 — 多驱动差异测试（P0）

- 同一案例跨 Mesa EGL/software、ANGLE 后端（可用时）及 Android 原生 GLES 比较；逐环境记录 driver、GPU、renderer、OS build、API、扩展、二进制 hash。
- **比较策略**：编译/链接期望、API error、FBO 像素结果、SSBO 数值、图像 Golden/容差、性能数据分别独立。
- 浮点输出根据精度规范、纹理采样容差、颜色空间和厂商允许误差设定 oracle；不得要求所有设备逐像素 bitwise 相等。
- 使用 capability-aware skipping，保留 `SKIP_UNSUPPORTED`、`UNKNOWN`、`FAIL` 的明确定义；缺少硬件不代表测试通过。
- 每条 mismatch 都经过 W1/W2 或现有 reducer 自动最小化并保存 replay artifacts。

**交付**：`benchmarks/differential/`、差异报告 schema、驱动矩阵、回放命令。

**DoD**：至少 30 个跨实现可复用用例；至少两个不同 GLES 实现完成 host-side 对照；真实 GPU 差异验证为单独门禁。

### W6 — 高级材质与 Shader 升级回归（P1）

- 以实际可查的 Filament v1.77.0 `iridescence` 变化作为案例研究：观察材质参数、版本/缓存无效化和视觉回归的方法；不要把 Filament 自身 API 移植为 GLES API。
- 建立薄膜干涉/虹彩材质可运行 GLES 参考示例（CPU 数值参考 + GLSL ES Shader）、色差与角度变化测试。
- 工程要求：材料描述向前兼容/拒绝策略、缓存键与 shader ABI 签名，跨版本回滚及 Golden Image。
- 对现实材质误差清楚区分近似模型与物理真实，移动端不同精度路径保持视觉阈值。

**DoD**：1 个完整虹彩/薄膜材质场景 + 5 个材质版本升级/回退错误案例，覆盖 GLES 3.0 fallback。

### W7 — Agent 对抗性修复 Benchmark 3.0（P0）

- 输入：未编译 Shader、错误 EGL 处理、无效 FBO 图、不同驱动输出差异、受控资源耗尽、材质 ABI 破坏。
- 评测模式：`Diagnose → Reproduce → Minimize → Patch → Compile/Run → Differential Verify → Report`。
- 评价指标：编译/链接成功率、定位准确率、误修率、误报率、最小复现保真率、回归损坏数、证据完整度、无 Skill/有 Skill 配对差异。
- 不允许 synthetic fixture 分数冒充真实模型输出；提供真实 provider 适配协议和证据拒绝准则。

**DoD**：新增至少 30 个高难度、可复现的 Agent 用例，每个有输入、oracle、失败模式、修复上限、严格评分器；真实模型对照缺少 provider 时标 `BLOCKED_BY_PROVIDER`。

### W8 — 90 天研究、CI 和发布（P0）

- 统一近 90 天窗口 2026-08-10—2026-11-07；GitHub release、commit、PR、官方规范、GPU 厂商工具、X 原帖均需核对**事件发生日期**和**信息发布日期**。
- 数据字段：`source_url`、`published_at`、`event_at`、`first_seen_at`、`api_scope`、`gpu_scope`、`evidence_type`、`repro_id`、`accepted`、`reason`。
- 每项真实新增技术要有规范/源码/场景/回归 ID；资料不足时标 `UNVERIFIED`，不能上升为 `MUST`。
- 新 CI：静态规则、Shader 生成器自测、状态机测试、受限 fuzz 短跑、host differential 与 Golden/ABI 回归；每项输出 JSON + Markdown 报告，上传失败样本。
- 对第三方工具和资产锁定版本/校验和，限制输入解析器资源，禁止外部源码自动执行；X 仅用于发现线索，保留原文链接并验证。
- 所有既有 gates 继续有效；禁止未经授权自动定时执行、提交、推送或发布 tag。

**DoD**：全套 regression 在干净环境可重现；受限 fuzz job 不可无限运行；依赖不满足时明确阻塞；版本 `1.0.8` 仅在所有强制发布 gate 通过之后变更。

## 2. 90 天研究依据及事实边界

| 日期 | 来源 | 可验证事件 | 工程启发 | 分类 |
|---|---|---|---|---|
| 2026-09-15 | https://github.com/google/filament/releases | Filament v1.77.0 引入材质虹彩参数并要求重新编译 Materials | 资产和 Shader ABI 版本化、升级兼容、视觉回归 | WINDOW_VERIFIED |
| 2026-09-09 | 同上 | Filament v1.76.1 修复某些 PowerVR Vulkan `readPixels` 慢路径 | 对照 GPU 后端/内存类型，不能错误归因为 GLES 缺陷 | WINDOW_VERIFIED_CROSS_API |
| 2026-09-28 | 同上 | Filament v1.77.2 包含构建工具和 Vulkan 深度/模板格式检测修复 | 能力探测与测试正确性，必须限定 backend | WINDOW_VERIFIED_CROSS_API |
| 2026-07-21 | https://github.com/KhronosGroup/VK-GL-CTS/releases | OpenGL ES CTS 3.2.14.1：精度、无效 Shader ID、atomics 等测试修复 | 负例及跨实现 oracle 设计 | HISTORICAL_CONTEXT_NOT_90D |
| 2026-03-06 | https://github.com/KhronosGroup/VK-GL-CTS/wiki/Overview-of-releases | OpenGL ES CTS 3.2.14.x 活跃系列起点 | CTS 基线选择，而非最新 GLES API 发布 | HISTORICAL_CONTEXT_NOT_90D |

额外研究源（候选、不可宣称本期具体更新）：Khronos GLES Registry/CTS、ANGLE、Mesa Panfrost/Freedreno/etnaviv、Google AGI/Perfetto、Arm Streamline、Qualcomm/PowerVR 官方文档、glslang、shaderc、SPIRV-Tools、GraphicsFuzz 相关研究。X 原帖只有存在可核实时间与源码/复现时方可入库，本次未核实具体原帖。

## 3. 交付目录建议（增量，不强行迁移）

```text
benchmarks/
  fuzz/shaders/
  state_machine/
  robustness/
  differential/
  material_upgrade/
  agent/v108/
docs/v1.0.8/
  coverage-diff.md
  source-evidence.csv
  implementation-traceability.md
  release-gates.json
  validation-report.md
references/evolution/
  2026-11-07-90d-review.md
```

若已有同名等价工具，则扩展原文件与测试，不另起重复仓库或复制测试系统。

## 4. PR 分拆及依赖

| PR | 主题 | 依赖 |
|---|---|---|
| PR-01 | W0 + W8 的研究证据、覆盖审计与数据契约 | 无 |
| PR-02 | W1 Shader Fuzzing + 有效/无效 oracle | PR-01 |
| PR-03 | W2 状态机 + W3 Robustness | PR-01 |
| PR-04 | W4 RenderGraph/Material 对抗验证 | v1.0.7 真实实现及 PR-01 |
| PR-05 | W5 跨驱动差异测试、失败最小化 | PR-02/03；复用既有 reducer |
| PR-06 | W6 材质升级案例 + W7 Agent Benchmark | PR-04/05（Agent 部分允许先建设 fixtures） |
| PR-07 | W8 整体验收、CI、文档、版本门禁 | 所有前序 |

所有 PR 面向同一 v1.0.8 集成目标；不自动发布中间版本。开发者可在独立分支并行，不应修改他人正在处理的工作区文件。保留旧版测试、旧规则、平台触发条件和证据；不允许无理由删改历史门禁。

## 5. 最终可执行验收清单

- [ ] 当前 `main` HEAD、文件差异、前序发布状态、标签和 release gates 已冻结与核实。
- [ ] Shader Fuzz：≥60 个稳定组合，日志可重放、超时可控、正确与错误输入分离。
- [ ] GLES/EGL 状态机：≥40 个边界测试，已知故障序列 ≥10，可控 oracle，不将未定义行为当规范。
- [ ] Robustness：≥20 个安全资源压力/故障恢复测试，清理与隔离可靠。
- [ ] RenderGraph 对抗：≥20；Material ABI 对抗：≥20；无前序实现不得伪造完成。
- [ ] 多驱动 Differential：≥30 条案例，至少两种 host GLES 实现对照；真机单列硬件门禁。
- [ ] 虹彩材质 1 个运行示例，材质升级/回退 ≥5 个负例，Golden 与误差阈值明确。
- [ ] Agent v3 新增 ≥30 个案例，真实模型/无 Skill 对照有独立评分，无授权 provider 标阻塞。
- [ ] 技术来源包含时间、原文 URL、可验证性、版本适用范围与不纳入理由；滚动 90 天有去重机制。
- [ ] CI 受限执行、恶意输入隔离、所有前代回归继续有效；无假 PASS / 假性能收益。
- [ ] 必须由授权者完成 GitHub PR 合入、最终 metadata bump 与 tag；规划本身不构成发布许可。

**分层证据等级**：`SPEC_VERIFIED` / `HOST_REPRODUCED` / `DEVICE_REPRODUCED` / `MODEL_EVALUATED` / `UNVERIFIED` / `BLOCKED_BY_HARDWARE` / `BLOCKED_BY_PROVIDER`。各层不得相互代替。

## 6. 可派发 Agent 的实施提示词

> 对仓库 `oahc09/gles-rendering-expert-skill` 执行 v1.0.8 全量任务书。先读取当前仓库差异、`SKILL.md`、前序版本路由和 release gates，形成覆盖差异矩阵。保持既有版本规则和触发条件，不删除约束；只做增量改动。按照 W0–W8 建设受限 GLSL Fuzz、GLES/EGL 状态机、GPU Robustness、RenderGraph/Material 对抗测试、跨驱动 Differential 和 Agent 对照 Benchmark，优先复用仓库现有 reducer、场景、设备矩阵与编译脚本。研究 2026-08-10—2026-11-07 的 GitHub/X/规范/厂商变化，逐条核实时间和证据，不把 Vulkan 特性当成 GLES Core。所有改动提供最小复现、自动测试、结果与未验证列表。真机、真实模型和前序门禁不具备时明确 BLOCKED，不能变为 PASS。最终提交待评审 PR；仅在收到单独发布授权且所有强制门禁通过后合入及发 tag。

## 7. 风险和范围控制

1. **Fuzz 不是以故意挂死设备为验收目标**。默认 CPU/软件驱动与隔离进程、小预算执行；物理设备压力测试必须设置限额与退出方案。
2. **GLES 规范不保证所有浮点结果 bitwise 相同**。Differential oracle 必须考虑合法的精度和实现差异。
3. **GPU hang、driver crash 的诊断结论必须标识证据层级**，不能把工具超时、用户输入非法或测试器崩溃当 GPU bug。
4. **v1.0.7 未核实完整落地**。W4/W6 必须有依赖门禁，不能通过平行重复造轮子规避依赖。
5. **计划只覆盖 v1.0.8 一个发布版本**；后续版本按 `1.0.8 → 1.0.9` 递增，不预设下一版需求。
