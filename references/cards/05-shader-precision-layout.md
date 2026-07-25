# GLSL ES 精度控制 & Shader I/O 布局

> **Category**: Shader | **GLES Version**: GLSL ES 3.00 / 3.20 | **Source**: `references/rules/glsl-es-optimization.md` §1, §2, §7, §8

## 核心规则

1. **每个 shader 第一行必须是 `#version 300 es`（或 `310 es` / `320 es`）**，之前不得有空行或注释。
2. **Fragment shader 必须显式声明精度**：`precision mediump float;`（无默认值，缺失则编译失败）。
3. 精度选择：
   - `highp`：顶点位置、深度、MVP 矩阵、时间累加器
   - `mediump`：纹理坐标、颜色、法线、光照方向
   - `lowp`：仅 8-bit 颜色输出（极少使用）
4. **始终使用 `layout(location = N)`** 绑定 attribute 和 fragment output；禁止依赖 `glGetAttribLocation`。
5. 使用 `in`/`out`（GLES 3.0+）；**禁止** `attribute`/`varying`/`gl_FragColor`/`texture2D()`。
6. Fragment 优化：避免 divergent branch（用 `mix`/`step`/`smoothstep`）；循环用常量上界；尽量用内置函数。
7. 可移到 vertex shader 或 CPU 的计算不要留在 fragment shader（per-pixel 成本最高）。

## 代码模式

```glsl
// ✅ Vertex Shader
#version 300 es
precision highp float;
layout(location = 0) in vec3 a_Position;
layout(location = 1) in vec3 a_Normal;
layout(location = 2) in vec2 a_TexCoord;
layout(std140) uniform Matrices {  // binding via glUniformBlockBinding (ES 3.00)
    highp mat4 u_MVP;
    highp mat3 u_NormalMat;
};
out mediump vec3 v_Normal;
out mediump vec2 v_UV;
void main() {
    v_Normal = normalize(u_NormalMat * a_Normal);
    v_UV = a_TexCoord;
    gl_Position = u_MVP * vec4(a_Position, 1.0);
}

// ✅ Fragment Shader
#version 300 es
precision mediump float;
layout(location = 0) out vec4 o_Color;
in mediump vec3 v_Normal;
in mediump vec2 v_UV;
uniform sampler2D u_Albedo;
void main() {
    o_Color = texture(u_Albedo, v_UV) * vec4(v_Normal * 0.5 + 0.5, 1.0);
}
```

## 常见陷阱

| 陷阱 | 后果 | 修正 |
|:-----|:-----|:-----|
| Fragment 不声明 `precision` | 编译错误 | 加 `precision mediump float;` |
| 顶点位置用 `mediump` | 大坐标抖动 | 位置/矩阵一律 `highp` |
| 大纹理 UV 用 `mediump` | 接缝/闪烁 | 4096+ 纹理 UV 升 `highp` |
| 使用 `gl_FragColor` | GLES 3.0 编译失败 | `layout(location=0) out vec4` |
| `texture2D()` | GLES 3.0 编译失败 | `texture()` |
| Divergent `if` 选纹理 | SIMD 两路都执行 | `mix(texA, texB, selector)` |
| 时间 uniform 用 `mediump` | 溢出/动画卡顿 | `highp` + `mod()` 回绕 |

## 关联卡片

- [01-api-version-constraints](01-api-version-constraints.md) — 版本-特性对应
- [06-compute-shader](06-compute-shader.md) — Compute shader 精度 (默认 highp)
- [09-overdraw-fillrate](09-overdraw-fillrate.md) — Fragment 成本优化
