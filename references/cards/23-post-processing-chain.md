# 移动端后处理链 — Bloom / 模糊 / 调色

> **Category**: Post-Processing | **GLES Version**: 3.0+ | **Source**: `references/rules/post-processing-chain.md`

## 核心规则

1. **先降采样再模糊**：bloom/blur 在 1/2 → 1/4 → 1/8 链上操作，远比全分辨率模糊便宜，且质量损失不可察觉。
2. **最小化 pass 数**：能合并就合并（bloom composite + tone-map + color grade 在最终 pass 完成）。每省一个 pass = 省一次全屏读写。
3. 可分离模糊用 **ping-pong FBO**（H→V）；消费完的 buffer 及时 `glInvalidateFramebuffer`。
4. HDR bloom 源用 `RGBA16F` 或 `R11F_G11F_B10F`；进 LDR 后中间结果用 `RGBA8` 省带宽。
5. **模糊算法按预算选**：Gaussian+线性采样（~半 taps）、Kawase（便宜）、Dual Filter（带宽友好）、Tent（COD AW，bloom 优秀）。
6. **线性采样技巧**：bilinear 硬件过滤合并两个 Gaussian tap 为一个加权 tap，tap 数近半。
7. **3D LUT 调色**：32³ 3D LUT（`GL_RGB8` + linear）一次采样替代逐通道曲线计算，放最终 pass。
8. bright pass 可并入首个降采样（降采样时做阈值），省一个 pass。

## 代码模式

```
scene(HDR) → bright+downsample → blur down → blur up → composite+tonemap+grade → display
```

```glsl
// 3D LUT 调色（最终 pass）
uniform mediump sampler3D u_LUT;
mediump vec3 Grade(mediump vec3 c) {
    mediump float inset = 0.5 / 32.0;                 // half-texel inset
    return texture(u_LUT, clamp(c, 0.0, 1.0) * (1.0 - 2.0*inset) + inset).rgb;
}
```

## 常见陷阱

| 陷阱 | 后果 | 修正 |
|:-----|:-----|:-----|
| 全分辨率模糊 | 4–16× 模糊成本 | 降采样链先行 |
| 中间结果全用 RGBA16F | 带宽暴涨 | LDR 后用 RGBA8 |
| ping-pong 消费后不 invalidate | 多余 store | `glInvalidateFramebuffer` |
| 对称 tap 手动 N 次采样 | 2× taps | 线性采样技巧 |
| tone-map/grade/bloom 各自独立 pass | 3× 全屏 pass | 最终 pass 合并 |

## 关联卡片

- [04-framebuffer-objects](04-framebuffer-objects.md) — ping-pong FBO 与 invalidate
- [20-hdr-and-display](20-hdr-and-display.md) — HDR 管线与 tone map
- [08-tbdr-bandwidth](08-tbdr-bandwidth.md) — 全屏 pass 带宽代价
