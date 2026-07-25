# GLES Rendering Expert — Knowledge Cards Index

> 按 OpenGL ES 功能点拆分的知识卡片系统。每张卡片聚焦一个独立功能域，
> 包含：核心规则、代码模式、常见陷阱、关联卡片。
>
> 数据来源：`references/rules/` 目录下的完整规则文档（本卡片为精炼摘要，详细上下文请查阅原始规则文件）。

## 卡片目录

| # | Card | 功能域 | GLES 版本 | 来源规则 |
|:--|:-----|:-------|:----------|:---------|
| 01 | [api-version-constraints](01-api-version-constraints.md) | API 版本约束 & 桌面 GL 禁用 | 3.0/3.1/3.2 | `gles-api-standards.md` |
| 02 | [texture-formats-compression](02-texture-formats-compression.md) | 纹理格式 & ASTC/ETC2 压缩 | 3.0+ | `gles-api-standards.md` §3, `mali-arm-best-practices.md` §4 |
| 03 | [buffer-objects](03-buffer-objects.md) | VAO/VBO/UBO/SSBO/PBO | 3.0/3.1 | `gles-api-standards.md` §4, `glsl-es-optimization.md` §3,§5.3 |
| 04 | [framebuffer-objects](04-framebuffer-objects.md) | FBO 生命周期 & MRT & Blit | 3.0+ | `gles-api-standards.md` §5, `tbdr-bandwidth-rules.md` §2 |
| 05 | [shader-precision-layout](05-shader-precision-layout.md) | GLSL ES 精度 & I/O 布局 | 3.00/3.20 | `glsl-es-optimization.md` §1,§2,§7,§8 |
| 06 | [compute-shader](06-compute-shader.md) | 计算着色器 & 同步 | 3.1+ | `glsl-es-optimization.md` §5, `mali-arm-best-practices.md` §3 |
| 07 | [egl-context-lifecycle](07-egl-context-lifecycle.md) | EGL 初始化/销毁/多线程/Context Lost | EGL 1.4+ | `egl-and-context.md` |
| 08 | [tbdr-bandwidth](08-tbdr-bandwidth.md) | TBDR 架构 & 带宽优化 | All | `tbdr-bandwidth-rules.md` §1,§3 |
| 09 | [overdraw-fillrate](09-overdraw-fillrate.md) | Overdraw & Fill-Rate 优化 | All | `tbdr-bandwidth-rules.md` §5, `mali-arm-best-practices.md` §8 |
| 10 | [msaa-antialiasing](10-msaa-antialiasing.md) | MSAA on TBDR (Mali/Adreno) | 3.0+ | `tbdr-bandwidth-rules.md` §5.3, `mali-arm-best-practices.md` §5, `adreno/efficient-msaa.md` |
| 11 | [synchronization](11-synchronization.md) | Fence/Memory Barrier/Buffer Orphaning | 3.0/3.1 | `gles-api-standards.md` §6, `glsl-es-optimization.md` §5.5-5.6 |
| 12 | [draw-call-optimization](12-draw-call-optimization.md) | Draw Call 批处理 & 实例化 & Indirect | 3.0/3.1 | `mali-arm-best-practices.md` §7, `gles-api-standards.md` §4 |
| 13 | [mali-pls-multiview](13-mali-pls-multiview.md) | Mali PLS & Multiview/Foveated | 3.0+ ext | `mali-arm-best-practices.md` §1,§2 |
| 14 | [adreno-gmem-vrs-lrz](14-adreno-gmem-vrs-lrz.md) | Adreno GMEM/VRS/LRZ/FlexRender | 3.0+ ext | `adreno/*.md` |
| 15 | [windows-egl-angle](15-windows-egl-angle.md) | Windows 平台 EGL/ANGLE/Windows-on-ARM | 3.0/3.1 via ANGLE | `windows-platform.md` |
| 16 | [powervr-hsr-img-extensions](16-powervr-hsr-img-extensions.md) | PowerVR HSR/PLS/IMG 扩展/Tile 带宽 | 3.0+ ext | `powervr/*.md` |

## 卡片格式说明

每张卡片遵循统一结构：

```
# [标题]
> Category | GLES Version | Source

## 核心规则        ← 必须遵守的硬性规则（生成代码时强制执行）
## 代码模式        ← 正确用法的典型代码片段
## 常见陷阱        ← 高频错误 & 其后果
## 关联卡片        ← 交叉引用
```

## 使用方式

- **代码生成时**：根据涉及的功能域加载对应卡片的核心规则作为约束。
- **代码审查时**：对照卡片的"常见陷阱"逐条检查。
- **性能诊断时**：从 `08-tbdr-bandwidth` 和 `09-overdraw-fillrate` 入手定位瓶颈。
