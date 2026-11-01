# GLES Rendering Expert Skill v1.0.5 完整开发任务计划书

- 计划日期：2026-11-01
- 仓库：https://github.com/oahc09/gles-rendering-expert-skill
- 唯一目标版本：`v1.0.5`（全部工作包一次性交付，内部可以多个 PR）
- 任务性质：规划，尚未实施、未提交或发布
- 首次技术研究窗口：2026-10-02 至 2026-11-01（UTC，包含首尾）

## 0. 结论、边界和前置状态

**核心目标：从单帧 GPU 诊断发展为长期运行中的性能、温度、功耗、画质协同诊断与自适应优化。** 特别强调 Android GLES 3.x、Mali/Adreno/PowerVR，以及 ANGLE 和嵌入式设备的差异。

本次直接核查的仓库 `SKILL.md` 元数据仍是 `1.0.2`，`README.md` 声明 v1.0.3 为 engineering candidate，`docs/release-gates.json` 中 `release_ready=false`。v1.0.3 候选版已有 112 规则测试、16 Shader 编译/链接测试与 64 Agent 用例，但真机验证和实际 Agent 对照存在阻塞。仓库未检索到 `docs/v1.0.4-development-plan.md`。因此 **不要把 v1.0.4 计划视为已实装或已发布**；实施开始先核对最新 main SHA、标签、PR、工作区差异，制作 v1.0.3/v1.0.4 已实现与未实现清单。属于前序版本的工作单独标为 `PREDECESSOR_BLOCKER`，不冒充 v1.0.5 新功能。未经明确授权不修改主干、合并、打 tag 或部署。

### 与 v1.0.4 的增量区别

- v1.0.4 规划：平台双后端、场景 Benchmark、GPU Trace 诊断、Agent 自动修复基础闭环。
- v1.0.5 新增：长时间稳定性、热/功耗反馈、可解释的动态质量策略、数值及视觉误差测试、内存压力恢复、面向 Trace SQL 的自动诊断与建议校验。
- 复用上一版 GPU capture/schema、Agent runner、CapabilitySnapshot、规则 ID，不复制开发另一套基础框架。

## 1. 开发任务一览

| ID | 主题 | 必须交付物 | 验收要点 |
|---|---|---|---|
| W0 | 前序版本基线/差异审计 | `docs/v1.0.5/baseline-and-delta.md` | 明确复用、阻塞、缺项、实际 SHA |
| W1 | 热、功耗、帧稳定性 | `references/playbooks/thermal-and-power.md`，长期采样场景 | 10/30 分钟曲线、帧分布、热状态与设备信息 |
| W2 | 自适应质量控制 | 质量策略状态机及跨场景示例 | 不抖动、画质下限、恢复策略、可关闭 |
| W3 | 精度与颜色正确性 | FP16/FP32、sRGB/linear、HDR、混合误差案例 | 数值/视觉对照和容差说明，回退明确 |
| W4 | GPU 资源与内存压力 | 上传、驻留、回收及 Context 恢复压力场景 | 无泄漏、资源增长受控、恢复可复现 |
| W5 | Trace SQL 智能分析 | Perfetto 适配器、SQL 模板、归因报告 | 可离线复现，缺字段时输出 UNKNOWN |
| W6 | Golden Image 视觉回归 | 参考图、比较器、mask、阈值配置 | 多平台差异分类，不把近似图像当完全正确 |
| W7 | 滚动技术雷达 | GitHub/X/规范/厂商来源证据台账 | 日期可追溯、去重、拒绝无证据的强制规则 |
| W8 | Agent Benchmark/CI/发布 | 端到端验收矩阵、报告、CHANGELOG | 静态/主机/真机/实模型证据分层，不伪造结果 |

## 2. W0：基线与依赖门禁

1. 读取 `main` HEAD、最新 tags、当前 PR、未提交修改以及所有既有测试入口。
2. 对照 v1.0.3 `docs/release-gates.json` 和 v1.0.4 计划，生成逐项状态：`IMPLEMENTED` / `TESTED_HOST` / `TESTED_DEVICE` / `UNVERIFIED` / `BLOCKED` / `NOT_PRESENT`。
3. 只在明确有来源的条件下判断完成；缺少证据不得擅自将 blocker 改为 PASS。
4. `SKILL.md` 的触发、平台范围及 GLES 3.0/3.1/3.2 边界保持不变。新增规则按需加载，避免将大段新知识全部塞入入口文件。

## 3. W1：长期帧稳定、热与功耗诊断

### 任务

- 设计 `LongRunCapture` 数据规范：device/SoC/GPU/driver、OS/API、渲染后端、屏幕刷新率、分辨率、画质档位、供电模式、温度/thermal status、GPU/CPU 频率、帧时分布、功耗数据来源、采样时钟、场景 SHA。
- 建立 10 分钟功能测试和 30 分钟持续运行基准；每台设备执行冷机和热稳态对照。覆盖交互突发、后台/前台、屏幕刷新率变化。
- 分析 `p50/p90/p95/p99 frame time`、jank ratio、缓慢劣化斜率、频率下降与帧耗时的时间相关关系。没有能源计量装置时，**不得推算精确毫瓦或电池节省百分比**。
- 对比系统侧 Android Performance Hint/ADPF 与 `AChoreographer`/Swappy 的适用边界；官方平台能力必须运行时探测，不强依赖任意供应商私有 counter。

### 验收

至少一个可离线复现的人工注入 trace 样本：热降频、CPU 提交瓶颈、GPU 长期带宽压力三种原因均能正确分类或输出 `INSUFFICIENT_EVIDENCE`。真实设备结论必须附原始 traces，不能用主机 Mesa 代替。

## 4. W2：自适应渲染质量决策器

- 设计 `QualityPolicy`：输入为目标帧预算、近 N 帧分位数、温度趋势、GPU 限制、用户偏好；输出为推荐档位而非无条件操作系统/驱动开关。
- 候选控制：render scale、MSAA 档位、阴影分辨率、后处理 pass 组合、粒子预算、LOD 与各向异性过滤。逐项声明视觉风险、能力检查和恢复条件。
- 状态机：`NORMAL -> PRESSURED -> DEGRADED -> RECOVERING`，增加迟滞、冷却窗口、最低驻留时长与变化频率限制；禁止每帧反复升降画质。
- 严格区分 GLES 原生、ANGLE、Vulkan 后端；公共策略不直接调用不存在的 GLES API。

**验收**：可回放输入记录触发确定性输出；无振荡测试、负载尖峰不误触发、热态持续压力会降档、压力解除能有序恢复；启用/禁用的画质差异进入 W6 检测。

## 5. W3：Shader 数值精度与画质保持

- 研究 GLES `highp/mediump/lowp` 实际保证、驱动差异、FP16 ALU/寄存器、插值器与离屏格式，不把 `mediump` 一概等同某固定 bit 数或性能收益。
- 场景：长时间累计动画、法线与高光、水面/流体、渐变、HDR tonemap、透明叠层、sRGB ↔ linear、RGBA8 vs RGBA16F。
- 建立 `NumericErrorSpec`：参考表达式/参考渲染、允许误差、设备信息、亮度或色度误差、边缘 mask、是否可容忍时间性闪烁。
- 设立性能-画质双门禁：性能提升但明显色带、闪烁或轮廓破坏不得自动接受。

## 6. W4：GPU 资源驻留、回收和后台恢复

- 纹理/渲染目标预算与分层 LRU；在 GLES 无可移植的精确 VRAM 空间统计时，记录**引擎已分配资源估算**，不可称 GPU 真实驻留字节数。
- PBO 异步上传和读取：具备 fence 生命周期、线程归属及取消处理；故意延迟 GPU completion 测试不得产生竞态。
- `AHardwareBuffer/EGLImage/GL_TEXTURE_EXTERNAL_OES` 生命周期：重点检查拥有权、fence 交接、context loss、安全销毁与恢复。
- 压测场景：反复切场景 100 次、Surface 销毁重建、上下文丢失模拟、纹理上传突发、低内存信号处理。

**验收**：无明显对象增长趋势；资源回收可追踪；在不可复现 Android 真实 loss 的环境中使用 `NOT_RUN_DEVICE` 而非 PASS。

## 7. W5：Perfetto Trace SQL Agent 诊断

- 研究基线：Perfetto v59.1（2026-10-27），官方 release 说明引入 Trace Processor agent mode、CLI 错误改进和 Android 重启后 trace 持久化。工具升级只作为采集/分析能力，不推断其自动掌握私有 GPU 计数器。
- 输入：Trace 文件路径/数据哈希、设备能力快照、元数据、可用表；SQL 模板必须先做表/列检测。
- 输出：`evidence.json`（SQL、时间范围、原始数据、缺失字段）、`diagnosis.md`（观测→假设→排除→结论/未知→建议实验）。
- 支持事件关联：render thread、CPU sched、GPU work slices（若存在）、频率、温度、SurfaceFlinger、swap/present/backpressure。
- 防止模型编造：没有 GPU counter 时不能写“GMEM 带宽降低 25%”；报告自动标注 `observed` / `inferred` / `not-measurable`。

**验收**：至少 12 个人工构造或获许可公开 Trace fixture；SQL 模板结果稳定、可回放，未知字段、空 Trace、截断 Trace 不能静默成功；对照人工结论列出误报和漏报。

## 8. W6：画质回归和性能-画质 Pareto 评价

- `Golden Image` 管理：GPU/driver/backend/分辨率/颜色空间/场景/时间戳/资源哈希；统一捕获格式，记录是否 HDR/WCG、是否发生压缩与色彩管理转换。
- 多尺度图像比较：像素绝对误差、结构相似度 SSIM、差异热图；需要亮度/颜色感知指标时明确色彩空间和参考算法。动态内容必须使用可重复的固定时间/种子，必要时采用时序误差评测。
- 边缘、透明层、阴影和发光应分别设置容差；绝不使用单一 SSIM 阈值替代所有美术质量判断。
- 形成 Pareto 报告：p95 帧时间、可测功耗、视觉误差、内存预算、热稳定性，而非只看 FPS。

**验收**：至少 8 个 golden 场景，其中半精度/色带、透明混合、水面高光、HDR tonemap、动态分辨率需被覆盖；对人为引入的视觉退化能稳定检出。

## 9. W7：滚动近 30 日技术雷达

### 来源与策略

1. **官方规范/认证**：Khronos OpenGL ES、EGL、GLSL、OpenGL ES CTS，按版本/扩展事实入库。
2. **主要实现**：ANGLE、Mesa Panfrost/Freedreno/etnaviv、Filament、RenderDoc、Perfetto、AGI、glslang、KTX-Software，抓取原始 release、commit、PR、issue。
3. **GPU 厂商**：Arm Mali/Immortalis、Qualcomm Adreno、Imagination PowerVR 的开发手册、Profiler/驱动说明。
4. **X 原创开发者发布**：必须保留原帖 URL、作者、原始发布时间、公开源码/演示、设备型号/采样证据；无法检索或核实则明确 `UNVERIFIED`，不能列成“本月正式发布”。
5. 研究范围 2026-10-02 至 2026-11-01；其他有价值的旧技术资料单独标为 `historical-context`，不能冒充本月发布。

### 首轮已验证线索与待确认范围

- **2026-10-27 Perfetto v59.1**：引入 Trace Processor 面向 AI 工具的 agent mode、SQL CLI 改进、Android 重启后 trace 持久化。行动：W5 建立离线 SQL fixture 和缺数据门禁。来源：https://github.com/google/perfetto/releases
- **OpenGL ES CTS 3.2.14.x**：Khronos 官方当前活跃分支，可作为规范回归参考；不是本轮确认的新发布。来源：https://github.com/KhronosGroup/VK-GL-CTS/wiki/Overview-of-releases
- **Filament v1.77.2**：页面标注 2026-09-28，超出本次 30 天窗口；后续按新版本变化审查 OpenGL backend、渲染技术与功耗优化，不标成本月新发布。来源：https://github.com/google/filament/releases
- Android 官方性能质量与 ADPF：长期技术基础，不误称为 2026 年 10 月新增。来源：https://developer.android.com/quality/technical
- X 最近 30 天原始可核验证据：本次未确认，记录为 `UNVERIFIED / FETCH_PENDING`，不可编造帖子或链接。

### 每条研究候选必须包含

`source_url`, `author_org`, `published_at`, `event_at`, `collected_at`, `source_hash`, `hardware`, `driver`, `api_version`, `extension`, `actual_change`, `engineering_impact`, `repro_steps`, `evidence_level`, `decision`, `target_rule`, `test_id`。

处理流：采集→去重→规范/源代码核验→适用条件→最小复现→规则或示例增量→正负测试→PR Review。不得让自动抓取直接修改规范性 `MUST` 规则。

## 10. W8：Agent Benchmark、CI 与单版本发布

### Agent 用例（新增至少 24 个，避免重复 v1.0.3 的 64 条）

- 热降频与瞬时 GPU 性能退化的区分（4）。
- 动态分辨率与画质迟滞调节（4）。
- GLSL 精度与颜色空间差异（4）。
- GPU 驻留/上传/Context 重建（4）。
- Trace SQL 缺失字段、证据边界、误归因（4）。
- 视觉正确性与性能收益冲突（4）。

对每条题目比较 `without_skill` / `with_skill`：规范违规率、编译运行成功率、根因准确率、错误建议率、证据引用充分性、画质安全性。Agent 的真实模型调用与 synthetic runner 测试必须分开计数。

### 测试分层

- L0：Markdown、JSON/schema、链接与 rule ID 一致性。
- L1：主机代码与 GLSL 编译、可重复的合成 traces 与图像回归。
- L2：Android NDK/APK、EGL lifecycle、设备兼容性。
- L3：真实 Mali / Adreno / PowerVR（设备允许时）的温度、帧时、带宽、功耗（可用时）测量。
- L4：真实模型 paired benchmark 与人工抽样评审。

不得将 L0/L1 PASS 归结为 L3/L4 PASS。缺设备时如实标注 `BLOCKED_BY_HARDWARE`，可交付 candidate，但不得宣布其真机优化完成。

### 建议 PR 划分（全属于 v1.0.5）

| PR | 范围 | 依赖 |
|---|---|---|
| PR-01 | W0 + W7 版本差异/研究台账 | 无 |
| PR-02 | W1 + W2 长期性能与动态质量 | PR-01 |
| PR-03 | W3 + W6 精度、颜色及画质回归 | PR-01，与 PR-02 并行 |
| PR-04 | W4 资源/内存压力与生命周期 | PR-01 |
| PR-05 | W5 Perfetto Trace SQL 自动诊断 | PR-01，与 PR-02/03/04 并行 |
| PR-06 | W8 集成、Agent Benchmark、CI、文档 | 上述 PR |

统一输出 README/CHANGELOG/版本门禁和 `docs/v1.0.5/acceptance.md`。仅在全部要求得到实际证据支持并获得发布授权后将版本改为 `1.0.5`，创建 `v1.0.5` tag；不自动安排后续版本。

## 11. 验收标准 DoD

- [ ] 查清真实版本基线、主干 SHA 与前序发布门禁；不假设 v1.0.4 已实现。
- [ ] 10/30 分钟长期测试流程、原始数据格式和至少 3 类可靠退化判断样例齐全。
- [ ] 自适应质量决策器可确定性回放、有迟滞、可关闭、可恢复。
- [ ] FP16/FP32、sRGB/linear、HDR、透明混合误差有可重复参考与回归。
- [ ] 资源压力、Context/Surface 生命周期没有未解释增长或对象泄漏；设备缺失明确标阻塞。
- [ ] Perfetto SQL 至少 12 个 fixture，缺数据不得编造结论；报告可复现。
- [ ] 视觉回归至少 8 个场景，明确 mask/阈值/色彩空间，能检测注入退化。
- [ ] 新增至少 24 个有标注 Agent 案例，真实模型与 synthetic 分离。
- [ ] 近 30 天研究来源可核验，新证据能追踪到规则/示例/用例；X 不可访问时不伪造。
- [ ] 全部新能力保留 GLES 版本/扩展边界、ANGLE 差异和平台回退。
- [ ] CI/NDK/真机/Agent 分层证据与阻塞项明确，未完成项不能被文档描述为 PASS。
- [ ] 只发布一个 `v1.0.5`，不擅自合并、提交主干或创建 tag。

## 12. 可直接交给 Coding Agent 的执行提示词

> 在 `oahc09/gles-rendering-expert-skill` 中实现《GLES Rendering Expert Skill v1.0.5 完整开发任务计划书》，目标是移动 GLES 长期性能、热/功耗协同、自适应画质、精度/颜色正确性、资源内存压力、Perfetto Trace SQL、Golden Image 与 Agent Benchmark。先审查 main SHA、标签、PR 和未提交变更，查清 v1.0.3/v1.0.4 的真实交付/阻塞状态；保留 `SKILL.md` 的既有路由和规则，不重复建设已有基础设施。按 W0–W8 增量实施，独立模块可并行，但不允许互相覆盖文件。所有新技术依据需来自官方规范、原始源码或可复现证据；最新 30 天 GitHub/X 研究按日期归档，核对真正发生日期。实现时每项补最小运行示例、正负测试、能力探测/fallback 和验收报告。主机、Android 设备、真实 GPU 性能和 Agent 实模型测试严格分层，无法测量就标 `BLOCKED`，绝不编造数据。最后提交分层 PR 供审查；未经明确授权不合并、发布或推送。

## 13. 参考链接

- 项目仓库：https://github.com/oahc09/gles-rendering-expert-skill
- Perfetto release：https://github.com/google/perfetto/releases
- Perfetto docs：https://perfetto.dev/docs/
- Android App technical quality：https://developer.android.com/quality/technical
- Khronos OpenGL ES registry：https://registry.khronos.org/OpenGL/index_es.php
- Khronos GLES CTS：https://github.com/KhronosGroup/VK-GL-CTS/wiki/Overview-of-releases
- Filament releases：https://github.com/google/filament/releases
- ANGLE：https://github.com/google/angle
- Mesa：https://mesa3d.org/
