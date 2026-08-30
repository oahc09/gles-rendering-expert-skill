# 屏幕空间深度特效 — SSAO / 软粒子 / 运动模糊

> **Category**: Post-Processing / Depth | **GLES Version**: 3.0+ | **Source**: `references/rules/screen-space-effects.md`

## 核心规则

1. **禁止采样当前 FBO 自己绑定的深度附件**——纹理-FBO 反馈环在 GLES 是未定义行为；特效 pass 必须读"另一张深度纹理"或渲染到不同 FBO。
2. **TBDR 深度复用成本模型**：`GL_DEPTH_COMPONENT24` 存 4B/px + 特效读 4B/px = 8B/px；改在 opaque 片元末尾旁路写出**线性视深到 `R16F` 颜色附件**（2B/px 存 + 2B/px 读），真实深度附件若无人再测则 `glInvalidateFramebuffer` 丢弃。
3. **窗口 Z 非线性——读时线性化，绝不平均原始 Z**：`viewZ = 2nf/(f+n-z_ndc(f-n))`；深度重建用 `highp`，AO 输出用 `mediump`。
4. **SSAO 跑半分辨率或 1/4**，法线由 `dFdx/dFdy(linearZ)` 重建（剪影处零导数要兜底），上采样用**双边滤波**（距离+深度双权重）防 AO 越边渗透。
5. **半球采样随机化用 hash 不用噪声贴图**：`hash3(gl_FragCoord)` 约 10 ALU，比占一个采样器槽的 RG8 旋转图更适合 tile GPU；采样数 4–8，时域累积仅在已有 jitter/运动矢量时启用。
6. **软粒子用视空间深度差**：`fade = clamp((sceneDist - particleDist) * softness, 0, 1)`；比较窗口 Z 会因远平面精度堆积产生硬缝。
7. **运动模糊要速度信号**：逐物 = opaque FS 写 `RG16F` 屏幕空间速度附件（或上帧 viewProj 重投影）；纯相机运动 = 免缓冲，逆 view-proj delta 直接算。4–8 步采样，**零速度像素先早退**再采样。
8. **MSAA 深度不可直接采样**：先 resolve（`GL_EXT_multisampled_render_to_texture` 留在 GMEM）或直接用规则 2 的颜色深度旁路。
9. **TBDR 混合链融合**：AO×粒子×模糊等串联全屏混合 = 每级一次 store+load；合并进单个 composite pass 读多附件，别用 blit 串。
10. **格式表**：线性深度 `R16F`（配缩放因子），速度 `RG16F`，AO 结果 `R8`；GLES 3.0 半浮点线性过滤是 core，`R32F` 过滤需 `OES_texture_float_linear`——避开。

## 代码模式

```glsl
// opaque.frag 末尾 —— 2 字节旁路存线性视深
layout(location = 2) out mediump vec2 outLinearDepth;   // R16F 附件
highp float viewZ = -(u_View * vec4(v_WorldPos, 1.0)).z;
outLinearDepth = vec2(viewZ * u_DepthScale, 0.0);       // 缩放使值域适配 R16F

// particle.frag —— 对非绑定的线性深度纹理做软衰减
highp float sceneDist = texture(u_LinearDepth, uv).r * u_DepthInvScale;
mediump float fade = clamp((sceneDist - v_ViewDist) * u_Softness, 0.0, 1.0);
if (fade <= 0.001) discard;   // 场景表面在粒子前方：早退
```

## 常见陷阱

| 陷阱 | 后果 | 修正 |
|:-----|:-----|:-----|
| 采样当前 FBO 的深度附件 | 黑块/驱动相关随机输出 | 分离 FBO 或颜色深度旁路（规则 1/2） |
| 核内平均原始窗口 Z | 远处 AO 渗到近处 | 先线性化（规则 3） |
| `mediump` 重建深度 | ~10 m 外带状跳变 | highp 做 Z 数学（规则 3） |
| 全分辨率 SSAO+全分辨率模糊 | 双倍全帧缓冲流量 | 1/2–1/4 + 双边上采样（规则 4） |
| 静止像素也走速度采样 | 全屏幕白付模糊开销 | 零速度早退（规则 7） |
| 直接采样 MSAA 深度 | `INVALID_OPERATION`/垃圾值 | resolve 或颜色深度（规则 8） |

## 关联卡片

- [04-framebuffer-objects](04-framebuffer-objects.md) — MRT 附件与深度格式
- [08-tbdr-bandwidth](08-tbdr-bandwidth.md) — store/load 成本模型
- [23-post-processing-chain](23-post-processing-chain.md) — 这些 pass 的排序位
- [10-msaa-antialiasing](10-msaa-antialiasing.md) — 片上 resolve
- [05-shader-precision-layout](05-shader-precision-layout.md) — 精度选择
