# GLES Rendering Expert Skill v1.1.0 完整覆盖与阶段性收官开发计划书

- 计划日期：2026-11-08
- 仓库：https://github.com/oahc09/gles-rendering-expert-skill
- 唯一目标版本：**v1.1.0**；本文件中全部任务均属于该版本，内部可拆 PR，但不得通过提前标记版本号绕过验收
- 研究窗口：**2026-08-11 至 2026-11-08（滚动 90 天）**；更早的规范和成熟技术作为 `historical-foundation`，不得伪称近期发布
- 性质：**可实施的开发任务书，非代码实施/发布授权**。不得擅自提交、push、merge、tag、部署、启用调度或修改凭据与权限
- 总目标：将 Skill 打造为 **OpenGL ES 全标准、全主要工作流、跨平台、可验证、可维护** 的生产级专家知识和工程验证体系，完成一次阶段性闭环

## 0. 结论与严格范围

**“GLES 全部覆盖完成”不是在所有设备上验证所有厂商专有特性，也不是把所有渲染算法都实现一遍。** 本版采用可审计的四层覆盖定义：

1. **规范索引全覆盖（必须达成 100%）**：按已冻结的 Khronos Registry 快照，对 GLES 2.0、3.0、3.1、3.2 核心命令与枚举、GLSL ES 1.00/3.00/3.10/3.20 的规范主题、EGL 1.4/1.5 核心对象与命令建立机器可读、可追溯索引。历史 GLES 1.0/1.1 只作为迁移索引，不作为现代生成目标。不可把 Desktop GL API 混入。
2. **扩展索引全覆盖（必须达成 100%）**：对 Registry 中标注 GLES/EGL 适用性的扩展建立名称、适用版本、依赖、平台、入口探测、原始来源、状态、是否有实现验证的索引；针对常见 KHR/EXT/OES/ARM/QCOM/IMG/ANGLE/ANDROID 等制定深入知识卡。不是所有扩展都必须生成一个独立可运行例程。
3. **专家工作流全覆盖（必须达成）**：对主要 GLES 系统工程场景做到“适用条件→正确代码/诊断策略→负例→Fallback→测试”，包括代码生成、Code Review、EGL 生命周期、渲染正确性、移动 GPU 性能、跨驱动问题及部署诊断。
4. **证据分级的工程闭环（严格）**：静态规则、编译/链接、软件 GLES、Android 真机、Windows/ANGLE、Embedded Linux、GPU 性能、真实 Agent 对照分别有独立门禁。缺硬件/Provider 的项只能标 `BLOCKED_*`，不能宣称全部验证完成。

最终发布用语只能是“**GLES/EGL/GLSL ES 标准覆盖索引完成，指定验证矩阵的工程闭环完成**”；不得写“已兼容所有驱动”“已实测所有 GPU”“全平台零缺陷”。

## 1. 实际仓库基线（计划起点，后续实施重新读取）

2026-11-08 读取 GitHub 默认分支可见：

- `SKILL.md` 元数据仍为 **1.0.2**；存在 v1.0.7 Shader/Material/RenderGraph candidate 路由。
- `docs/v1.0.7-release-gates.json`：`release_ready=false`、`release_authorized=false`，具有对前序 release-gates 的递归依赖。
- v1.0.7 已有变体、ABI、RenderGraph、Hazard、颜色管线、软件 GLES 工程示例与 30 个新增 Agent 案例，**但非正式 release**。
- v1.0.3–1.0.6 有不同程度 candidate 实现，真机性能、部分 Android APK、Windows/ANGLE 真机、校准 HDR、真实 Agent provider 的测试仍存在阻塞。
- 本次默认分支中未获取到 `docs/v1.0.8-development-plan.md`、`docs/v1.0.9-development-plan.md`；**这不等于用户的历史规划不存在或没有在分支实现**。实施前须检查所有相关分支/PR/tag，避免重复建设。

**前置义务**：实际开发时读取 HEAD SHA、tags、PR、工作区差异、release-gates、benchmarks、examples、CI。形成 feature inventory 与 `REUSE/EXTEND/MISSING/BLOCKED` 四态表。不得为了“收官”合并或删减已有安全与版本门禁。

## 2. 权威规范与研究证据

### 2.1 规范冻结源

| 范围 | 主要权威来源 | 用途 |
|---|---|---|
| OpenGL ES 2.0/3.0/3.1/3.2 与 ESSL | https://registry.khronos.org/OpenGL/index_es.php | 规范文本、版本边界、Shader Language |
| OpenGL API XML | https://github.com/KhronosGroup/OpenGL-Registry （`xml/gl.xml`） | 命令/枚举/版本/扩展机器索引 |
| Khronos GLES headers | 同上 `api/GLES2/`, `api/GLES3/`, `api/GLES/` | 编译交叉检查；禁止以 headers 替代规范解释 |
| EGL 1.4/1.5、EGL Extensions | https://registry.khronos.org/EGL/ | 平台、Context/Surface、同步和图像扩展 |
| EGL Registry XML | https://github.com/KhronosGroup/EGL-Registry （`api/egl.xml`） | EGL 命令、扩展索引 |
| CTS / dEQP | https://github.com/KhronosGroup/VK-GL-CTS | 合规正反测试与失败分析；不能宣称自身成为认证测试套件 |
| Android | https://developer.android.com/guide/topics/graphics/opengl | Android 生命周期/设备能力及现代平台约束 |
| ANGLE | https://github.com/google/angle | 翻译层、Backend 差异 |
| Mesa | https://docs.mesa3d.org/ | 驱动与测试生态 |

所有来源需记录 **URL、commit/tag/hash、采集时间、许可、对应规范版本**。对规范 PDF 有版权/分发限制时仅建立章节定位和摘要，不复制整份规范到仓库。CTS 只引用和运行许可允许的部分，保留其原许可证。

### 2.2 最近 90 天专项技术雷达

- 研究区间：2026-08-11 ~ 2026-11-08。搜索 GitHub releases/commits/PR、X 原帖、Khronos、Android、ARM Mali、Qualcomm Adreno、Imagination PowerVR、ANGLE、Mesa Panfrost/Freedreno/etnaviv、Filament、Perfetto、AGI、RenderDoc、glslang、KTX。
- 已核实的近期**设备兼容性线索**：Khronos OpenGL ES 认证登记显示 2026-11-03 Google/ANGLE Vulkan backend 的 GLES 3.2 项，以及 2026-11-04 Qualcomm Android 17 的 GLES 3.2 项。只能用作 **设备/驱动矩阵候选与 conformance 信息**，不能推定性能或普适兼容性：https://www.khronos.org/conformance/adopters/conformant-products/opengles
- 官方 GLES 核心规范仍为 3.2，EGL 核心仍为 1.5；这不是近 90 天新 API 的声明。
- 每个技术信号保存 original date / observed date / source ID / code diff / affected API / impacted rule / verification / reject rationale；X 无源码、无复现、无可信证据的仅列为候选，不进入强制规则。
- 持续监控仍复用项目已有 Radar，不新造并行抓取器；**本任务不授权开启定时调度**。

## 3. 开发工作包（W0–W12）

### W0 — 基线、债务和覆盖范围冻结 [P0]

**任务**：枚举仓库中 API cards、rules、pipeline、system examples、driver compat、benchmarks、CLI、Agent adapters、CI；核实 v1.0.3–v1.0.9 实施状态和递归门禁；固定 registry SHA 与目标设备矩阵。

**交付**：`docs/v1.1.0/baseline.md`、`docs/v1.1.0/debt-ledger.json`、`docs/v1.1.0/coverage-scope.yaml`。

**验收**：每项遗留要求有 `source_version`、status、evidence、owner、disposition；`NOT_RUN` 不会因为进入 v1.1.0 而自动改为 `PASS`。所有修改之前检查 diff。

### W1 — 全量 API 和枚举覆盖索引 [P0]

**任务**：基于固定 `gl.xml` 的 GLES core feature/require/remove 与扩展支持记录生成清单；归类 Buffer/VAO/Vertex Arrays、Texture/Sampler/Image、Framebuffer/Renderbuffer、Draw/Instancing/Indirect、Raster/Depth/Stencil/Blend、Query/Sync、Program/Pipeline、Compute/SSBO/Atomic、Geometry/Tessellation、Debug/Robustness、Transform Feedback、Readback/PixelStore、Limit/State Query。处理别名、promoted extension、同名 API 跨版本限制。

**交付**：`references/coverage/gles-api-catalog.json`、`tools/coverage/build_gles_catalog.py`、`references/coverage/gles-gap-report.md`；每个条目标注 `core_since`、`extension`、`rules[]`、`examples[]`、`tests[]`、`coverage_level`、`source_spec`。

**验收**：固定 Registry GLES 2.0/3.0/3.1/3.2 命令与枚举索引 100% 有记录；新漏项自动使 CI 失败。索引完整度≠所有函数均有专属示例；对核心 API 的不可生成项、精确权限和诊断入口均可查。

### W2 — GLSL ES 语言能力全面收口 [P0]

**任务**：GLSL ES 1.00（迁移）、3.00/3.10/3.20 的词法、预处理、精度、类型/数组/矩阵、控制流、uniform/block、layout、std140/std430、varying、接口匹配、插值、纹理和衍生函数、计算/原子/Barrier、Geometry/Tessellation、图像读写、编译/链接错误、扩展 gating；建立 AST 或可靠编译器驱动的验证方案，禁止单靠 regex 宣称语言合法性。

**交付**：`references/coverage/glsl-es-matrix.md`、正负 shader fixture、`tools/coverage/verify_glsl.py`。

**验收**：每个规范功能族至少一正一负场景；GLES 3.0/3.1/3.2 的版本边界及合法扩展路径通过真实编译和链接；未实现的特殊扩展明确标识。

### W3 — EGL 全生命周期/跨平台完备性 [P0]

**任务**：EGL 1.4/1.5 初始化/发现、Config、Context、Surface、Pbuffer/Surfaceless、MakeCurrent、Swap/Presentation、线程共享、Sync、Image、Platform Extensions、错误码/重建；Android NDK+Java（禁止 Kotlin）、Windows ANGLE/Windows-on-ARM、Embedded Linux GBM/Wayland/X11 能力矩阵。Surface 丢失和 Context Reset 分别处理；支持不共享对象边界。

**交付**：`references/coverage/egl-matrix.md`、多 Surface/共享 Context 真实 demo、EGL 故障注入、平台构建脚本。

**验收**：正常生命周期、暂停恢复、Resize、销毁顺序、双线程、跨上下文、出错回退有复现；未提供设备时保留 `BLOCKED_BY_HARDWARE`，不伪造结果。

### W4 — 扩展生态全索引与能力协商 [P0]

**任务**：从 Khronos Registry 生成 GLES/EGL 扩展清单，区分 KHR/EXT/OES 与 vendor（ARM/QCOM/IMG/ANDROID/ANGLE 等），建立 `core / extension / implementation / unsupported` 四类判定。扩展同名/提升 core/入口指针/依赖/运行时参数限制均被显式处理。优先深度卡片：External Texture、EGLImage/AHardwareBuffer、Sync、Debug、Robustness、Multiview、Framebuffer Fetch/PLS、MSRTT、ASTC、VRS、Protected Content、Timer Query。

**交付**：`references/coverage/extensions-catalog.json`、`references/coverage/extensions-priority.md`、`CapabilityNegotiator` 测试。

**验收**：Registry 内适用于 GLES/EGL 的扩展 100% **被索引和定级**；高频扩展具备真实版本/扩展决策及正负例；不宣称所有 GPU 可执行所有扩展。

### W5 — 渲染状态、格式与资源交互 [P0]

**任务**：全面检查格式/类型/可渲染性/Filterability/Blendability、色彩空间、纹理压缩、Framebuffer completeness、MSAA Resolve、State Cache、RAII/Context Generation、Resource Hazards、PBO/Sync、Program Binary、Query、Draw/Compute/Indirect、Pixel Store Alignment；增强“合法但实现相关”的条件陈述。

**交付**：状态机契约、格式能力矩阵、至少 40 条新的有区分度的正负组合测试（具体数量可由 gap audit 上调）。

**验收**：旧规则不回退；命令错误码、允许组合、资源生命周期和 fallback 有可运行验证；软件与真机性能证据分离。

### W6 — 移动 GPU 与系统平台深度知识收口 [P0]

**任务**：Mali、Adreno、PowerVR、Mesa Panfrost/Freedreno/etnaviv、ANGLE backend 的架构特征/计数器/工具限制；Android 性能与功耗、多 Surface、视频、WCG/HDR、压缩纹理、TBDR、GPU/CPU 同步。将“通用结论”拆成 `MUST` 规范、`SHOULD` 建议、`CONDITIONAL` 设备相关、`EXPERIMENTAL` 四档。

**交付**：vendor coverage cards、设备/驱动/扩展快照、真实问题诊断树、设备测试报告模板。

**验收**：禁止无计数器情况下断言性能改善；驱动 bug workarounds 限定精确版本、证据、有效期与自动回退。

### W7 — 主流 GLES 渲染场景的专家覆盖 [P1]

**任务**：2D UI/SDF/MSDF、3D PBR/Forward+、阴影、后处理、HDR、透明/OIT、粒子、流体、水体、玻璃/折射、Compute、动画/骨骼、3DGS 混合高重叠、纹理流、视频融合和多视图。每类保留代码路径、最小可复现、移动端带宽/精度注意事项、ES 3.0 fallback 或明确不支持理由。优先复用 v1.0.3–v1.0.9 已存在案例，避免重复新建引擎。

**交付**：场景能力矩阵、案例 README/源代码/视觉金图、质量阈值与失败解释。

**验收**：所有列入“主流场景”的类别至少一个经过 host compile/run 的代表案例或明确 `DEPENDENCY/BLOCKED`；不要把复杂算法的存在误认为 GLES 规范核心覆盖的一部分。

### W8 — Registry → Rules → Tests 一致性自动化 [P0]

**任务**：新增 coverage pipeline，从冻结 XML 自动更新覆盖清单，检查文档/规则 API 版本、扩展和例子索引，发现幽灵函数/错误版本/孤儿规则/未测试正负例；归档 upstream diff、审阅记录并支持按需更新。禁止动态拉取 head 直接导致基准漂移；运行以固定 SHA 为准。

**交付**：`tools/coverage/check_coverage.py`、机器报告 JSON/Markdown、CI workflow 的离线/联网双阶段；`coverage-report.json` 中单列 indexed/semantic/compiled/runtime/device/provider 指标。

**验收**：人造漏项/错误版本/错误扩展至少各一次被检测；源不完整时状态 INCOMPLETE 而非 100%；无网络离线基线可复现。

### W9 — 平台构建、CTS 对照与真机矩阵 [P0]

**任务**：CI 编译 C++17/GLSL/ES 3.0–3.2；Mesa software EGL 校验功能；Android arm64 APK（Java+JNI）至少可构建和安装；ANGLE Windows x64+ARM64 编译/运行（设备可用时）、Embedded Linux GBM/Surfaceless（设备可用时）。选择 CTS 子集/日志格式建立比较，不宣称对驱动进行 Khronos 官方认证；记录 driver, GPU, build, SHA、设备温度/性能。

**交付**：CI 矩阵、smoke APK、CTS runner 配置与原始 `.qpa`/可索引结果（适用时）、测试环境 manifest。

**验收**：Android APK 实际产物+安装运行证据；host 与 target 严格分开；没有真机就必须报告未完成和阻塞，不能用模拟器替代带宽结论。

### W10 — Agent 专家能力综合 Benchmark [P0]

**任务**：构造 100 个**去重后的终局评估任务**（建议构成：版本/扩展 20、代码生成 20、Review 20、EGL/驱动诊断 20、性能/质量优化 20），可从已有用例中独立抽样但不得混入训练/改进循环；对 no-skill / with-skill 使用同模型、同预算、同任务、固定 judge rubric，统计准确率、误报、首次编译成功率、正确性、诊断复现率、证据完整性、成本。

**交付**：`benchmarks/agent/final-eval/` 的冻结题库/脚本、盲评指南、原始模型输出、汇总报告及失败分析。

**验收**：真实 provider 执行才可声明模型分数；合成 fixture 只能证明评测器工作正常。建议门槛：`P0 API illegal generation = 0`（本基准集）、`valid solution first-run >= 90%`、`false-positive <= 5%`；若未达标，报告失败并修复后重新留痕，不能更改冻结题库作弊。强制报告分母和置信度。

### W11 — 90 天技术雷达与知识生命周期治理 [P1]

**任务**：沿用原 Radar 每周增量、每月回顾滚动 90 天；监控 Khronos XML/CTS、Android、ANGLE、Mesa、厂商 SDK、工程仓库、X 原帖。引入 `new / verified / adopted / deprecated / superseded / disputed / blocked` 生命周期、规则冲突检测、旧结论再确认、厂商 workarounds 过期检查。

**交付**：source ledger、rule provenance、version migration notes、自动生成 Change Impact 报告与人工审查清单。

**验收**：新技术必须能追踪到具体 rule/example/test；无高价值变化明确“未发现经验证实质更新”，不能为凑数纳入营销信息。定时运行必须另经授权。

### W12 — 整体验收、报告与唯一版本发布 [P0]

**任务**：核验 W0–W11、递归前序 gate、文档/目录/许可/安全/安装入口一致性、跨平台 smoke、Agent 基准与真实设备证据；只在授权后执行正式 merge/version bump/tag/release。

**交付**：`docs/v1.1.0/acceptance-report.md`、`docs/v1.1.0/release-gates.json`、`docs/v1.1.0/coverage-final.md`、`CHANGELOG.md`、维护与回滚指南。

**验收**：无不明状态；`release_ready` 不允许从文本注释手工推定；对旧版未关闭 gate 需要如实保留，不能通过递归链接失效或降低门槛跳过。**若硬件/Provider 环境无法提供，交付完整代码候选 + 阻塞报告，不宣称正式阶段性收官。**

## 4. 重点覆盖清单：避免遗漏的 GLES 功能族

| 功能族 | 代表范围 | 校验方式 |
|---|---|---|
| API 版本/扩展 | 2.0/3.0/3.1/3.2 核心边界、EXT/OES/KHR/vendor | XML + 规范 + 运行时探测 |
| Context / EGL | config、surface、sync、image、error、swap、sharing | EGL 生命周期执行 |
| Buffer / VAO | buffer storage/update/map、vertex attrib、instancing、TF | C++17 + GLES runtime |
| Texture | 2D/3D/array/cube、compressed、sRGB、sampler、mipmap、external | format/extension 正负用例 |
| Framebuffer | MRT、depth/stencil、invalidate、MSAA、resolve | FBO completeness + images |
| Raster/Blend/Depth | culling、scissor、depth/stencil、blend、state query | 数值 / Golden image |
| Draw/Compute | draw/indirect、image/SSBO、atomic、sync/barrier | ESSL + GPU/CPU parity |
| Shader | stage、precision、uniform/UBO/SSBO、layout、program interface | compile/link + reflection |
| Geometry/Tessellation | GLES 3.2 能力和限制 | 版本/能力/编译验证 |
| Query/Debug/Robustness | timestamp/occlusion、debug extension、reset | 错误/负例/能力差异 |
| Pixel Ops/Readback | PixelStore、PBO、format/type、fence | 数值回读和同步 |
| Platform/Interop | Android、ANGLE/Windows、Embedded Linux、AHB/video | platform builds/device |
| GPU Optimization | Mali/Adreno/PowerVR、TBDR、bandwidth、ALU、thermal | 真机 before/after counters |
| Mainstream Effects | UI、3D、PBR、particles、water、glass、postfx、3DGS | representative scenes |

注意：GLES 核心标准没有 Vulkan 显式 RenderPass、Mesh Shader、硬件 Ray Tracing 的同等 Core API；相关能力必须标记为外部 API 或模拟/近似方案，绝不虚构接口。

## 5. 建议新增目录（以真实仓库为准，增量创建）

```text
docs/v1.1.0/
  baseline.md
  debt-ledger.json
  coverage-scope.yaml
  coverage-final.md
  acceptance-report.md
  release-gates.json
references/coverage/
  gles-api-catalog.json
  glsl-es-matrix.md
  egl-matrix.md
  extensions-catalog.json
  extensions-priority.md
  format-capability-matrix.md
  scenario-matrix.md
  source-manifest.json
tools/coverage/
  build_gles_catalog.py
  build_egl_catalog.py
  check_coverage.py
  verify_glsl.py
benchmarks/coverage/
  positive/
  negative/
  state-machine/
  image-goldens/
benchmarks/agent/final-eval/
  cases.json
  rubric.md
  reports/
examples/closure/
  android-java-ndk/
  egl-lifecycle/
  gles-runtime/
reports/v1.1.0/
```

仓库已有同等工具时优先扩展，不重复实现第二套规则管理器、GPU 采集系统、RenderGraph 或 Agent runner。

## 6. 执行顺序、并行与 PR 约束

| PR | 内容 | 前置 |
|---|---|---|
| PR-01 | W0 + registry 快照与覆盖范围冻结 | 无 |
| PR-02 | W1 + W4 API/扩展全量索引 | PR-01 |
| PR-03 | W2 + W3 ESSL/EGL 语义与平台验证 | PR-01，可与 PR-02 并行 |
| PR-04 | W5 + W6 核心资源/厂商规则审查 | PR-02，可部分并行 |
| PR-05 | W7 代表场景与复现测试 | PR-03/04 的稳定接口 |
| PR-06 | W8 + W9 coverage CI/CTS/device matrix | PR-02/03 |
| PR-07 | W10 + W11 最终 Agent 基准/技术治理 | PR-05/06 |
| PR-08 | W12 集成审查、发布候选、release | 全部，且需明确授权 |

每个 PR 必须标明：变更范围、来源 SHA、受影响规则、正负测试、未验证事项、回滚办法。允许 2–3 个独立 Agent 并行（不修改同一文件），总状态只维护一个 `in_progress`。不得在未经授权情况下进行 git push/merge/tag。

## 7. 最终 DoD / Release Gate

- [ ] Registry SHA 已冻结且许可证合规，GLES 2.0–3.2 Core API/枚举 **索引完整度 100%**。
- [ ] EGL 1.4/1.5 Core + GLES/EGL 扩展 **索引完整度 100%**；针对重点扩展有 capability probe 与 fallback。
- [ ] GLSL ES 1.00（迁移）及 3.00/3.10/3.20 的全部规范功能族有正负案例，并通过实际编译/链接检查。
- [ ] 所有新增规范规则有 spec/extension 来源、适用条件和测试 ID，禁止孤儿 API/不存在接口。
- [ ] 全部主流工程场景在矩阵中有可用实现路径、验证状态和已知限制；不要求穷举所有渲染算法。
- [ ] C++17、Android Java/NDK、软件 EGL、Windows ANGLE、Embedded Linux 的平台矩阵有结果，未执行不可标 PASS。
- [ ] Android APK 可构建且有真机安装/功能 smoke 证据；至少一个实际 Mali 和一个实际 Adreno 设备验证移动 GPU 重点场景；PowerVR 若无硬件如实标记覆盖缺口。
- [ ] GPU 性能优化必须有命名设备、驱动、构建 SHA、原始 Trace、热状态与 before/after；无实测不宣称提升。
- [ ] 100 个终局 Agent benchmark 由真实模型执行，no-skill/with-skill 的原始输出和客观指标可核查；没有 Provider 则不能声称通过。
- [ ] CI 完成镜像/编译/运行/报告，规范源不可用或上游抓取失败应显示 `INCOMPLETE`。
- [ ] 前序版本候选门禁原样保留，未解决的阻塞明示，不允许版本更名伪造 release。
- [ ] 版本、README、SKILL、Changelog、license、安全检查、安装示例及回滚演练一致，且发布操作经授权。

**阶段性收官判定**：只有“规范索引完整 + 专家工作流覆盖 + 指定平台/模型验证门禁通过 + 历史阻塞闭环”全部满足，才宣布 v1.1.0 完成；否则报告 `IMPLEMENTATION_COMPLETE / ACCEPTANCE_BLOCKED` 等真实分层状态。

## 8. Agent 可直接执行的任务提示词

> 目标：实施 GLES Rendering Expert Skill v1.1.0 全域覆盖收官计划。先核实当前 `main`、PR/tag、工作区差异和递归 release gates，形成 W0 的真实差异清单。以固定 Khronos gl.xml/egl.xml SHA 建立 GLES 2.0–3.2、EGL 1.4/1.5、GLSL ES 全域机器索引；只做增量改动，不覆盖既有模型路由和触发条件。逐项完成 W1–W12，优先复用已有规则、例子、测试、工具。对每项交付生成可复现的 compile/link/runtime/target/provider 证据；禁用任何“无设备即通过”的伪结果。按 PR-01～PR-08 的依赖顺序推进，未经单独授权不得 push、merge、tag 或发布。最终交付 coverage report、原始测试证据、未验证项、release gates 和结论。

## 9. 后续维护策略（v1.1.0 之后）

v1.1.0 收官后不再按专题机械扩大文档体积。将未来变化分成：规范/扩展增量、厂商驱动事件、重要工程实践、测试回归修复。每月滚动 90 天 Review，每季度进行一次覆盖漂移审计；只在具备实际新增能力/纠错和证据时提升版本号。保持 Skill 入口简洁，内容按目标平台/具体问题按需路由。

---

**当前交付状态（2026-11-08）**：本文件是计划，不是源码实现。已读取现有仓库部分入口和 v1.0.7 gate，已查证 Khronos Registry/EGL/CTS 官方来源；未执行完整代码库的 XML 覆盖分析、编译、设备测试、真实 Agent 对照或 GitHub 发布。
