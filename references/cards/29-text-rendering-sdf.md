# SDF/MSDF 文本渲染

> **Category**: UI / Textures | **GLES Version**: 3.0+ | **Source**: `references/rules/text-rendering-sdf.md`

## 核心规则

1. **默认 MSDF（3 边缘通道）**，spread 4–8；单通道 SDF 仅在图集内存逼限时用；位图 mip 只适合固定字号。
2. **图集是距离场不是颜色**：用 `GL_R8`，**禁用 sRGB internal format**（硬件 sRGB 解码会毁掉距离数学），gamma 在 coverage 之后自己校。
3. **AA 来自屏幕空间导数而非 mipmap**：`smoothstep(0.5-w, 0.5+w, dist)`，`w=fwidth(dist)`（钳到 ≥1e-5）；MSDF coverage 用 `median(r,g,b)`。距离场不做 mip，跨 mip 混距离尺度。
4. **大图集 UV 用 highp**：mediump 尾数 ~10bit，4096 图集误差数 texel。`fwidth` 只能在非一致控制流外算，先算 alpha 再 `discard`。
5. **一条字符串/一个图集 = 一次 draw**：动态 VBO（`glMapBufferRange`+`GL_MAP_INVALIDATE_RANGE_BIT` 环形）或 `glDrawArraysInstanced` 逐字形实例；逐字 draw 是 UI 头号杀手。
6. **预乘 alpha 输出** + `glBlendFunc(GL_ONE, GL_ONE_MINUS_SRC_ALPHA)`：消除 AA 边缘暗晕。
7. **动态图集管理**：shelf/skyline 分配器 + `glTexSubImage2D` 部分上传；亚像素偏移量化到 1/4px 防重烘；CJK 按 256 码位分页 + LRU。
8. **彩色 emoji 走独立 RGBA 位图层**，距离场只编码 coverage。
9. **TBDR**：文本是 alpha overdraw——quad 收紧到 ink box（非 em advance 方框），UI 排在帧末使混合 tile 只 flush 一次。

## 代码模式

```glsl
#version 300 es
precision mediump float;
uniform sampler2D u_Atlas;   // GL_R8 MSDF, CLAMP_TO_EDGE, LINEAR, 无 mipmap
in highp vec2 v_Uv;
in vec4 v_Color;
out vec4 fragColor;
float median(float r,float g,float b){ return max(min(r,g),min(max(r,g),b)); }
void main(){
    vec3 s = texture(u_Atlas, v_Uv).rgb;
    float sd = median(s.r, s.g, s.b) - 0.5;
    float w  = max(fwidth(sd), 1e-5);
    float a  = smoothstep(-w, w, sd);
    if (a <= 0.0) discard;
    fragColor = vec4(v_Color.rgb * a, a) * v_Color.a;  // 预乘
}
```

## 常见陷阱

| 陷阱 | 后果 | 修正 |
|:-----|:-----|:-----|
| SDF 图集用 sRGB 格式 | 缩放后笔画忽粗忽细 | `GL_R8`，coverage 后校 gamma |
| 给距离场开 mipmap | 掠射角模糊收缩 | `GL_TEXTURE_MAX_LEVEL 0` + LINEAR |
| `fwidth` 在 if 分支内 | 部分驱动 AA 失效 | 无条件算 AA，之后 discard |
| 4096 图集用 mediump UV | 字形抖动偏移 | highp vec2 或缩图集 |
| 逐字形 draw call | UI 吃光 draw 预算 | 合批 VBO/实例化 |
| advance 宽度 quad | 每串 2× overdraw | ink bounds 收紧 |

## 关联卡片

- [02-texture-formats-compression](02-texture-formats-compression.md) — R8 格式
- [05-shader-precision-layout](05-shader-precision-layout.md) — 精度限定符
- [12-draw-call-optimization](12-draw-call-optimization.md) — 合批/实例化
- [27-texture-streaming-lod](27-texture-streaming-lod.md) — 图集部分上传
