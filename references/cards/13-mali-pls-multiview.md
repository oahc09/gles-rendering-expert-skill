# Mali PLS & Multiview / Foveated Rendering

> **Category**: Mali Vendor | **GLES Version**: 3.0+ extensions | **Source**: `references/rules/mali-arm-best-practices.md` §1, §2

## 核心规则

### Pixel Local Storage (PLS)
1. **`GL_EXT_shader_pixel_local_storage`**：将 G-Buffer 完全保留在 tile memory，**零 DRAM 往返**——Mali 上延迟着色/透明/多 pass 的首选。
2. 用 `__pixel_localEXT` 声明存储，每个成员指定 **紧凑 packed format**（`rgb10_a2`, `rg16f`）；总预算 ~128 bits/pixel。
3. 法线存 `xy` 重建 `z`；sign bit 打包到 alpha；**禁止 `rgba32f`**（耗尽 tile 预算）。
4. PLS 在 pass 开始 **未定义**，pass 结束 **丢失**——视同 tile memory，不可 CPU 回读。
5. 配合 **stencil buffer** 跳过无几何像素的光照计算。
6. Fallback 顺序：PLS → Framebuffer Fetch → MRT + `glInvalidateFramebuffer`。

### Multiview / Foveated
7. **`GL_OVR_multiview2`**：单次 draw call 渲染到 array texture 多层（双眼）；`layout(num_views=N) in;` + `gl_ViewID_OVR` 索引 per-view 矩阵。
8. `num_views` 必须等于 FBO layer count；所有 attachment 层数一致。
9. **不兼容 geometry / tessellation shader**。
10. `GL_OVR_multiview`（base）仅允许 `gl_Position` 依赖 view；需要 view-dependent lighting 时用 `multiview2`。
11. **Foveated**：中心高分辨率 inset + 外围低分辨率，`smoothstep` 按距屏幕中心距离混合。

## 代码模式

```glsl
// PLS 声明
#version 300 es
#extension GL_EXT_shader_pixel_local_storage : require
precision highp float;
__pixel_localEXT FragDataLocal {
    layout(rgb10_a2) vec4 lighting;
    layout(rgb10_a2) vec4 albedo;
    layout(rg16f)    vec2 normalXY;
} gbuf;

// Multiview vertex
#version 300 es
#extension GL_OVR_multiview2 : require
layout(num_views = 2) in;
uniform mat4 u_VP[2];
void main() {
    gl_Position = u_VP[gl_ViewID_OVR] * vec4(a_Pos, 1.0);
}
```

## 常见陷阱

| 陷阱 | 后果 | 修正 |
|:-----|:-----|:-----|
| PLS 用 `rgba32f` | 超出 tile 预算，性能暴跌 | `rgb10_a2` / `rg16f` packed |
| 期望 PLS 跨 pass 持久 | 读到未定义值 | PLS 仅限同一 render pass 内 |
| Multiview + geometry shader | INVALID_OPERATION | 不兼容，去掉 geometry shader |
| `num_views` ≠ FBO layers | INVALID_OPERATION | 保持一致 |
| 不检查 PLS 扩展 | 编译/链接失败 | 运行时查询 + fallback |

## 关联卡片

- [08-tbdr-bandwidth](08-tbdr-bandwidth.md) — Tile memory 架构
- [04-framebuffer-objects](04-framebuffer-objects.md) — FBO 与 MRT fallback
- [14-adreno-gmem-vrs-lrz](14-adreno-gmem-vrs-lrz.md) — Adreno 对应方案 (GMEM)
