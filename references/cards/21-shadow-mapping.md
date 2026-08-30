# 移动端阴影贴图

> **Category**: Lighting | **GLES Version**: 3.0+ | **Source**: `references/rules/shadow-mapping-mobile.md`

## 核心规则

1. 两遍结构：Pass 1 从光源把深度渲到**深度纹理**（不是 renderbuffer，后面要采样）；Pass 2 采样比较得阴影因子。
2. 深度用 `GL_DEPTH_COMPONENT24`；只渲深度的 FBO 要 `glDrawBuffer(GL_NONE)` + `glReadBuffer(GL_NONE)`，且深度必须被保留（不 invalidate）。
3. **阴影图分辨率是带宽预算**：移动端默认 1024²，hero 光才 2048²；级联阴影 2–3 级足够。
4. **偏移必须调**：常数偏移 + 斜率偏移（`glPolygonOffset`）防阴影痤疮；偏移过大 → peter-panning。每个光单独调。
5. 用 `sampler2DShadow` + `GL_COMPARE_REF_TO_TEXTURE` 走硬件过滤的 PCF，比手动多 tap 便宜。
6. 光源正交矩阵收紧到可见接收范围，提升有效分辨率；只对投射物渲染阴影遍。
7. 透明物体不进阴影遍（需要时用 alpha-tested 变体——注意 `discard` 会关该 draw 的 early-Z）。
8. 阴影遍本身是一次 FBO 切换，尽量让它紧邻消费它的 pass。

## 代码模式

```cpp
glTexStorage2D(GL_TEXTURE_2D, 1, GL_DEPTH_COMPONENT24, 1024, 1024);
glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_COMPARE_MODE, GL_COMPARE_REF_TO_TEXTURE);
glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_COMPARE_FUNC, GL_LEQUAL);
glFramebufferTexture2D(GL_FRAMEBUFFER, GL_DEPTH_ATTACHMENT, GL_TEXTURE_2D, shadowTex, 0);
glDrawBuffer(GL_NONE); glReadBuffer(GL_NONE);   // depth-only
```

```glsl
// 硬件过滤 3×3 PCF
mediump float ShadowFactor() {
    highp vec3 p = v_LightSpacePos.xyz / v_LightSpacePos.w * 0.5 + 0.5;
    if (p.z > 1.0) return 1.0;
    mediump float s = 0.0; float t = 1.0/1024.0;
    for (int x=-1; x<=1; ++x) for (int y=-1; y<=1; ++y)
        s += texture(u_ShadowMap, vec3(p.xy + vec2(x,y)*t, p.z));
    return s / 9.0;
}
```

## 常见陷阱

| 陷阱 | 症状 | 修正 |
|:-----|:-----|:-----|
| 无偏移 | 阴影痤疮条纹 | 常数+斜率偏移 |
| 偏移过大 | 阴影脱离物体 | 减偏移、收紧光源视锥 |
| 深度用 renderbuffer | 主 pass 无法采样 | 深度**纹理**附件 |
| `sampler2D` 手动比较 | 无硬件过滤、tap 多 | `sampler2DShadow` + compare mode |
| depth-only FBO 漏设 `glDrawBuffer(GL_NONE)` | 部分驱动 INVALID_OPERATION | draw/read buffer 置 NONE |

## 关联卡片

- [04-framebuffer-objects](04-framebuffer-objects.md) — FBO 生命周期与 invalidate
- [09-overdraw-fillrate](09-overdraw-fillrate.md) — `discard` 与 early-Z
- [08-tbdr-bandwidth](08-tbdr-bandwidth.md) — 阴影遍的带宽代价
