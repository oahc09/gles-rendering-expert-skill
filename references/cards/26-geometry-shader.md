# Geometry Shader — 图元生成（GLES 3.2）

> **Category**: Shader Stage | **GLES Version**: 3.2 only (GLSL ES 3.20) | **Source**: `references/rules/geometry-shaders.md`

## 核心规则

1. **仅 GLES 3.2**：`#version 320 es`；3.0/3.1 必须提供回退（instancing / 预生成网格 / compute+indirect）。可用 `GL_OES_geometry_shader` 在部分 3.1 设备上回退，运行时检查。
2. 输入类型 `layout(points|lines|lines_adjacency|triangles|triangles_adjacency) in` 必须匹配 draw 的图元类别；输出只有 `points|line_strip|triangle_strip` 三种。
3. `gl_in[]` 读入顶点（`gl_in[i].gl_Position`）；VS varyings 以**数组**形式到达（`in vec3 vColor[]`）；`EmitVertex()` 发射、`EndPrimitive()` 收尾——漏掉 `EndPrimitive` 会丢最后一条图元。
4. `max_vertices` 按 `GL_MAX_GEOMETRY_OUTPUT_VERTICES`（3.2 最小 256）夹紧，**尽量写小**——直接影响寄存器分配。
5. **放大率 = 成本模型**：移动端每图元串行调用，高 fan-out 会迅速 vertex-bound；重复同构几何**优先 `glDrawArraysInstanced`**（3.0 起）。GS 留给变化/自适应拓扑（程序化建模、自适应圆环）。
6. **与 `GL_OVR_multiview` 互斥**（tessellation 同理）；有 GS 时它是末级 pre-rasterization 阶段——VRS 图元着色率必须由 GS 写。
7. 配合 Transform Feedback 时捕获的是 GS 输出，`glBeginTransformFeedback` mode 匹配 GS 输出类型。

## 代码模式

```glsl
#version 320 es
// ✅ 点 → 线段放大（最小可用形态）
layout(points) in;
layout(line_strip, max_vertices = 2) out;
in vec3 vColor[];
out vec3 fColor;
void main() {
    fColor = vColor[0];
    gl_Position = gl_in[0].gl_Position + vec4(-0.1, 0.0, 0.0, 0.0);
    EmitVertex();
    gl_Position = gl_in[0].gl_Position + vec4( 0.1, 0.0, 0.0, 0.0);
    EmitVertex();
    EndPrimitive();
}
```

## 常见陷阱

| 陷阱 | 后果 | 修正 |
|:-----|:-----|:-----|
| 在 3.0/3.1 目标上发 `#version 320 es` | 编译失败/设备不兼容 | 版本门控 + instancing 回退 |
| 用 GS 批量生成同构网格 | vertex-bound，慢于 instancing | `glDrawArraysInstanced` |
| `max_vertices` 写满 256 | 寄存器压力，占用率下降 | 按实际扇出写紧 |
| 忘 `EndPrimitive()` | 最后一条图元丢失 | 每个图元显式收尾 |
| GS + multiview 同 pass | 扩展互斥 | 拆 pass 或去掉 GS |
| VS 写 `gl_PrimitiveShadingRateEXT` | 有 GS 时被忽略 | 由末级阶段（GS）写入 |

## 关联卡片

- [25-transform-feedback](25-transform-feedback.md) — 捕获 GS 输出
- [12-draw-call-optimization](12-draw-call-optimization.md) — instancing 对比
- [01-api-version-constraints](01-api-version-constraints.md) — 3.2 门控
- [13-mali-pls-multiview](13-mali-pls-multiview.md) — multiview 互斥
