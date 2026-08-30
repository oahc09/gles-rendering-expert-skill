# GLES 翻译层 — ANGLE / MobileGL / SwiftShader

> **Category**: Platform | **GLES Version**: via layer | **Source**: `references/rules/translation-layer-gles.md`

## 核心规则

1. **翻译层 ≠ GPU 架构模拟**：ANGLE（GLES→D3D11/Vulkan，Chrome/Edge 使用，成熟）、MobileGL（桌面 GL 4.2→Vulkan/GLES，实验性未完成）、SwiftShader（CPU 软栅，极慢）。
2. **功能测试可信，性能测试不可信**——翻译层开销与 Mali/Adreno/PowerVR 差异巨大；带宽/填充率必须真机测。
3. **显式固定 ANGLE 后端**（`EGL_ANGLE_platform_angle`）；默认后端随机导致机器间行为不一致。
4. **ANGLE 特性行为**：varying 精度不匹配被**静默置零**（不报错）；"能跑" ≠ 规范正确。
5. **翻译层无厂商扩展**：`GL_QCOM_*`、`GL_EXT_shader_pixel_local_storage` 等在 ANGLE 缺失——所有厂商路径运行时 gate + fallback。
6. SwiftShader 仅用于 CI 正确性冒烟测试，绝不做性能。
7. MobileGL 是研究性项目（未完成），生产用 ANGLE。
8. 测试 harness 里准备 `glGetString(GL_EXTENSIONS)` 后端能力 diff 工具。

## 主机-真机测试矩阵

| 测试项 | ANGLE 主机 | 模拟器 | 真机 |
|:---|:---|:---|:---|
| API 正确性 | ✅ 好 | ✅ 可用 | ✅ 权威 |
| Shader 编译 | ✅ 抓语法错 | 可用 | ✅ 权威 |
| 视觉输出 | 可用 | 可用 | ✅ 权威 |
| 带宽/填充率 | ❌ 不代表 | ❌ 宿主后端 | ✅ 权威 |
| 厂商扩展 | ❌ 缺失 | 部分 | ✅ |

## 常见陷阱

| 陷阱 | 后果 | 修正 |
|:-----|:-----|:-----|
| 信任 ANGLE 性能数据 | 性能结论错误 | 真机测量 |
| 依赖默认 ANGLE 后端 | 机器相关 bug | 显式固定后端 |
| 把 "能跑" 当规范正确 | 真机独有失败 | 保持规范一致代码 |
| 主机用厂商扩展无 fallback | 主机崩溃 | 扩展 gate + fallback |
| SwiftShader 测性能 | 数字无效 | 只做正确性 |

## 关联卡片

- [15-windows-egl-angle](15-windows-egl-angle.md) — Windows ANGLE 集成细节
- [18-gpu-profiling-toolchain](18-gpu-profiling-toolchain.md) — 真机性能测量工具
- [01-api-version-constraints](01-api-version-constraints.md) — 扩展检查纪律
