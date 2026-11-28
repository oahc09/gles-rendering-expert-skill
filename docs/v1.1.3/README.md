# v1.1.3 项目接入与验收

见[本地结果和剩余验收条件](execution-status.md)。

## 首跑

稳定版元数据为 `1.0.2`，本说明对应 `v1.1.3 candidate`。安装目录可运行包自检和固定实验，目标项目的 Git 根目录用于项目快照，开发仓库用于验收台账和重新打包。

从解压安装后的技能目录执行自检，Python 3.11+ 即可。

```sh
python tools/package_skill.py check .
```

首个实际实验需要 Linux 或 WSL 及可用于无窗口运行的 Mesa EGL/GLES 和 llvmpipe。所需请求和驱动配置已随包提供。从安装目录执行。

```sh
work="$(mktemp -d)"
python benchmarks/workflow/run.py docs/v1.1.3/discard-workload.json \
  --config docs/v1.1.3/mesa-linux.json --backend mesa-software \
  --output-dir "$work/discard" --expect HOST_PASS
python tools/experience_cases.py --store "$work/experience.sqlite3" \
  --evidence-root "$work/discard" import strategy-receipt.json --actor local-executor
```

六策略工作流统一写入 `strategy-receipt.json`。旧的 `discard-result.json` 仍可作为历史实验报告阅读，导入经验库需要重新运行统一入口，以绑定当前的工作树和前置检查。

## 项目快照与补采

从技能目录执行，`--root` 指向外部目标项目的 Git 根目录，清单中的路径也相对该根目录。下面的随包示例选择仓库自带的 Android 壁纸工程，请把根目录改成实际的开发仓库检出位置。

```sh
python tools/project_context.py --root /path/to/gles-rendering-expert-skill-checkout docs/v1.1.3/wallpaper-project.json
```

保存输出中的 `source_manifest_sha256`、文件清单及工作树状态。清单限定本次读取和拟修改的文件范围。工作树状态保留 Git porcelain v1 的 NUL 分隔格式，可据此识别暂存、未暂存、未跟踪和重命名条目。引擎、构建入口、所有权等字段来自清单。设备端实际 backend 要在运行中采集。

既有 [GPU Decision](../v1.1.1/architecture.md) CLI 可独立使用。需要硬约束和单步补采时，把旧请求和以下结构的会话事实分别存成 JSON。

```json
{
  "schema_version": 1,
  "facts": {
    "backend": null,
    "driver": null,
    "timer_available": null,
    "quality_oracle": null,
    "evidence_conflict": false,
    "environment_changed": false
  },
  "budget_remaining": {"seconds": 30, "frames": 120, "resource_bytes": 1048576},
  "constraints": {},
  "attempted_probes": []
}
```

```sh
python tools/gpu_session.py decision-request.json session-facts.json
```

将探测 ID 记入 `attempted_probes`，更新已采集事实，并扣减预算后再次运行。同一个探测仍缺证据时保留基线。发生环境变代时从新运行记录重新建立会话。硬约束支持 `resource_bytes`（`bytes`）、`latency_ms`（`ms`）、`quality_error`（`normalized`）、`thermal_severity`（`ordinal`）。各项填写 `unit`、`maximum`、`observed` 和 `source`，未知的 `observed` 使用 `null`。当会话返回 `EXPERIMENT_REQUIRED`，使用[已有实验工作流](../../benchmarks/workflow/run.py)和 [Advisor](../../tools/optimization_advisor.py)审查对应实验是否已实现、质量是否合格，以及是否有可用测量。会话事实目前属于声明输入，DeviceLab、实验回执和经验导入的自动贯通仍待实现。

## 深度附件实验

首跑命令复放固定的 4×4 GLES 场景，记录 baseline、baseline 重复、candidate、恢复 baseline 和画质负控。仅比较仍有消费者的 RGBA8 输出，并在运行候选前检查存在后续深度消费者时 Decision 拒绝该候选。当前结论覆盖软件 GLES 正确性，Advisor 保留生产 baseline，性能字段为 `NOT_MEASURED`。

## 六策略与经验库

```sh
work="$(mktemp -d)"
python benchmarks/workflow/strategies.py --config docs/v1.1.3/mesa-linux.json \
  --strategy texture-mip-selection --case glyph --expect QUALITY_FAIL --output "$work/glyph.json"
python tools/experience_cases.py --store "$work/cases.sqlite3" --evidence-root "$work" \
  import glyph.json --actor local-executor
python tools/experience_cases.py --store "$work/cases.sqlite3" --evidence-root "$work" evaluate glyph.json
```

`strategies.py --help` 列出六条正式入口和 `--composition`。两轮 A/B 使用 AB、BA 顺序，前置 A/A 和一次预热，最后恢复 baseline 并保留负控。CPU 墙钟包括初始化和读回，GPU timing 为 `null`。ANGLE coherent 路径要求 `GL_EXT_shader_framebuffer_fetch`。缺扩展时保留独立的 ping-pong 输出及原路径的 `BLOCKED`。 [Khronos EXT 规范](https://registry.khronos.org/OpenGL/extensions/EXT/EXT_shader_framebuffer_fetch.txt)

默认退出码为 `0`（实验通过）、`1`（实验或候选质量失败）、`2`（参数或工作流执行错误）和 `3`（候选被阻塞）。验收负控时传入 `--expect QUALITY_FAIL` 或 `--expect BLOCKED`，预期状态匹配时退出 `0`。

经验库保存原始回执路径和哈希，每次查询复核代码和证据。用 `validate` 校验历史与有效条目，用 `query` 查看 workload、backend、API、driver 和环境哈希匹配情况。独立复核者可用 `review --scope <环境哈希> --actor <复核者> --reason <依据> --verdict reproduce-software <案例ID>` 记录复核，候选导入者不能自审。用 `retract` 附相同的环境、操作者和原因可撤回。当前工具可记录软件复现、拒绝、失效和撤回。真机证据和正式独立审查仍由相应验收处理。

实际画质反例仅在相同 workload、环境哈希及 profile 下拦截重复候选。可通过 `evaluate` 回放 Decision 与 Advisor，也可在 `gpu_session.py` 同时给出 `--experience-store`、`--evidence-root`、`--environment-sha256`、`--workload-id` 应用相同政策。证据哈希变化、来源缺失或撤回会恢复补采，其他 workload 保持独立。

## 本地验收

以下命令在技能包开发仓库的 Git 检出中运行。解压安装目录使用上面的 `package_skill.py check`。

```sh
python tools/check_v113_acceptance.py
python tools/check_v113_acceptance.py --output /tmp/gles-local-check --software-gles
```

第一条校验当前义务映射和历史台账。第二条要求新的仓库外目录，并执行雷达、决策和两个实际 Mesa GLES 阴影回归。仅运行 Python 回归时省略 `--software-gles`。决策 Schema 回归需要 `jsonschema`，CI 固定为 `4.23.0`。Mesa 路径需要 C++17 编译器、GLES 3 头文件和 llvmpipe。

报告保留源码和日志哈希以及实际执行结果。工作树有变化时，`source_tree_scope: HEAD_ONLY` 表示 Git tree 只标识基线，具体受测输入见 `critical_inputs_manifest`。当前入口执行本地检查并报告缺口，仍待实现独立复核接入和有效关闭回执的验证。

## 候选包

```sh
python tools/package_skill.py build /tmp/gles-v113-candidate.zip
python tools/package_skill.py install /tmp/gles-v113-candidate.zip /tmp/gles-rendering-expert-skill
```

打包读取 Git 已跟踪路径和明确列出的 v1.1.3 候选文件在当前工作树中的内容。ZIP 使用固定排序、时间戳、权限和无压缩模式，输出归档 SHA-256。安装前校验逐文件哈希，安装目标必须是新目录。Python 3.11+ 可直接运行项目快照和会话工具，项目快照另需要目标项目的 Git 可用。设备、图形和 provider 各自的环境要求见对应工具文档。已安装技能的替换和卸载接口待补充。
