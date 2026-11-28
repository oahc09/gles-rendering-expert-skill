# v1.1.3 执行状态 · 2026-11-28

当前推进 **S2 六策略与业务覆盖**。六策略软件闭环和经验治理已运行，G01 真机预览已通过，其真机多实例和长时仍待验证，交付点 A、B、C 均待验收。

执行基线为 `d73240bd34b48a3641fd8ed4799b287681295e70`，tree 为 `0776c4c8aa6851f63f6d68ec13f98e7da4378e39`。该基线包含 PR #18 的四项修复。当前工作树补充了雷达原子替换、实际阴影片段正负控和 GLES 3.2 border 运行。本轮改动的原始结果绑定工作树输入。历史检查器继续保护 25 个来源文件和 146 项义务。当前台账另外映射 60 个 ID，其中增强计划 W0–W16 的原文条款仍需核对。

| 范围 | 状态 | 实际证据与剩余条件 |
| --- | --- | --- |
| W00 / W01 | PARTIAL | R2-01 至 R2-04 本地验证通过。阴影实际片段按 GLES 3.0、3.1、3.2 核心头编译，Mesa GLES 3.0 和 3.2 执行边缘 PCF 与负控。高风险片段清单目前覆盖阴影三段，其他规范性示例和增强计划原文待补。 |
| W02 / W03 | PARTIAL | 壁纸 Git 工程已生成源文件哈希和所有权声明。补采和硬约束通过主机回归。业务、运行时证据、场景和复现包仍需关联。 |
| W04 / W05 | PARTIAL | 六策略取得软件 GLES 回执，coherent fetch 使用锁定 ANGLE。禁用该扩展时候选保持 BLOCKED，ping-pong baseline 通过。discard + 单次 resolve 完成四路实际画面对比。导入 7 个逻辑案例，其中 1 个实际字形画质反例，验证同条件拦截、撤回、证据缺失传播、自审拒绝。尚待 50/10、独立复核、真机计时和额外业务边界。 |
| W06 | PARTIAL | 壁纸通过 API 37 模拟器和 Adreno 830 真机的系统预览。真机同一 context 下观察到 drawable generation 从 1 增至 2，PQ swapchain 请求被接受。API 37 模拟器通过桌面与预览多实例、resize、后台呈现采样停止及恢复，并通过 NVIDIA 转译后端 600 秒和 SwiftShader 1800 秒持续采样。两后端均走 SDR。实体 HDR 显示校准、第二类物理 GPU、真机多实例与长时、媒体双输出和异步资源仍待验收。 |
| W07 | PARTIAL | Godot 4.5.1 在 llvmpipe 原生 GLES 3.2 通过 G03 初始回放。Filament 1.66.0 Android 在 API 37 模拟器和 Adreno 830 真机通过 G06 模型切换、拾取、光照、缩略图和 required-extension 回退子集。真机回退前后模型区域最大单通道读回误差为 2，切回前台后保留蓝色模型的 UI 状态。完整业务与设备矩阵、Cocos 和 Unity 工程仍待完成。 |
| W08 | BLOCKED | 冻结 100 题数据校验通过，真实响应 0。真实 provider 预算、独立预审、40 个旗舰任务和其中 25 个项目闭环仍待满足。 |
| W09 | PARTIAL | 实际 90 天抓取显示 Unity releases 空、URP changelog 两条候选。续跑保留已知身份，部分来源命中限流。此前两次定时成功均早于状态接续实现，仍需新版本的线上状态产物。 |
| W10 | PARTIAL | 当前本地状态工具、可复现候选包和干净目录安装已验证。还需可验证关闭回执、独立复核、第二类物理 GPU、Windows ANGLE/WoA 与 Embedded Linux 实机验证、最终 main CI。 |

线上研究雷达历史运行可见 [2026-11-16 批次](https://github.com/oahc09/gles-rendering-expert-skill/actions/runs/43855916360) 与 [2026-11-23 批次](https://github.com/oahc09/gles-rendering-expert-skill/actions/runs/45175590205)。URP 来源使用官方 [包 changelog](https://github.com/Unity-Technologies/Graphics/blob/master/Packages/com.unity.render-pipelines.universal/CHANGELOG.md) 的提交历史。

引擎复现入口见 [Godot G03](../../examples/engine_cases/godot-g03/README.md) 和 [Filament G06](../../examples/engine_cases/filament-g06/README.md)。

## G01 模拟器专项证据

两台 API 37 x86_64 AVD 安装了 SHA-256 一致的壁纸 APK。SwiftShader 路径中，桌面和预览各有独立 EGL owner 线程。关闭预览后桌面线程及其图层保留并继续呈现。预览在 `1000×2200` 下仍出图，恢复原尺寸后桌面继续呈现。设置页遮住桌面时，图层最后一次呈现时间戳在两次采样间未变，返回后重新推进。该检查通过 SurfaceFlinger 观察呈现，应用内部 GPU 提交计数未采集。

| 模拟器后端 | 实测时长 | 采样数 | FD 起止 | PSS 范围 |
| --- | ---: | ---: | ---: | ---: |
| NVIDIA 转译，GLES 3.1 | 600.973 秒 | 41 | 139 → 135 | 31,013–31,321 KiB |
| SwiftShader 转译，GLES 3.0 | 1800.683 秒 | 121 | 166 → 166 | 29,340–30,819 KiB |

两轮均在桌面壁纸前台运行，每 15 秒采样，进程 PID 与目标图层保持稳定，每个采样窗口均取得新的呈现时间戳。GPU 时间与功耗缺失。两个 AVD 都未报告 HDR 类型，壁纸选择 SDR RGBA8，另有 Java HDR 策略、嵌入 shader 编译及 Mesa HDR→SDR 数值控制通过。结论覆盖两套模拟后端的软件路径。实体显示校准需要实际面板测量，第二类物理 GPU 仍待验收。 [Android Emulator 图形模式](https://developer.android.com/studio/run/emulator-acceleration) [Android 混合 SDR/HDR 验证](https://source.android.com/docs/core/display/mixed-sdr-hdr)
