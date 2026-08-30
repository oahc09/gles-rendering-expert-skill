# HDR & 广色域显示管线

> **Category**: Display | **GLES Version**: 3.0+ ext | **Source**: `references/rules/hdr-and-display.md`

## 核心规则

1. **WCG（广色域）与 HDR（高动态范围）是两个独立轴**：WCG = 超出 sRGB 的色域（通常 Display-P3），不需要 HDR 屏；HDR = PQ/HLG 扩展亮度，需要 HDR 显示。别混为一谈。
2. **先查能力再选路径**：WCG 用 `Surface.isWideColorGamut()`/`AConfiguration_isWideColorGamut`；HDR 用 `Display.getMode()`/`HdrCapabilities`（JNI 查询，GLES 无此查询）。
3. 表面色彩空间在 **创建时声明**（`EGL_GL_COLORSPACE`），事后不可改：
   - 默认 `EGL_GL_COLORSPACE_SRGB_KHR`
   - `EGL_GL_COLORSPACE_SCRGB_LINEAR_EXT`（scRGB 线性：1.0 = 80 nits，>1.0 扩展范围，GLES HDR 首选路径）
   - `EGL_GL_COLORSPACE_DISPLAY_P3_PASSTHROUGH_EXT`
   使用前检查 `EGL_EXT_gl_colorspace_scrgb_linear`；Display-P3 检查 `EGL_EXT_gl_colorspace_display_p3`（`_EXT`/`_LINEAR_EXT` token）或 `EGL_EXT_gl_colorspace_display_p3_passthrough`（`_PASSTHROUGH_EXT` token）。
4. HDR10 直通必须通过 `EGL_EXT_surface_CTA861_3` 提供 **mastering metadata**（SMPTE ST 2086 原色/白点/亮度）——填内容母带意图，不是面板参数；缺 metadata 通常被当 SDR 处理。
5. **渲染侧全程线性扩展范围**（RGBA16F）到最终 tone/gamut map，禁止中途存 sRGB8 再线性化。
6. 最终输出必须匹配表面色彩空间：scRGB 表面输出 1.0 = SDR 白的线性值；P3 表面做场景空间 → Display-P3 转换。
7. UI 覆盖层与场景同色彩空间，否则发灰。
8. 至少在 1 台 WCG 设备 + 1 台 HDR 面板上实测——sRGB 开发机上色彩管理 bug 完全不可见。

## 代码模式

```cpp
// ✅ scRGB 线性 HDR 表面（先验证扩展）
const EGLint attribs[] = {
    EGL_GL_COLORSPACE, EGL_GL_COLORSPACE_SCRGB_LINEAR_EXT,
    EGL_NONE
};
EGLSurface surf = eglCreateWindowSurface(dpy, cfg, win, attribs);

// ✅ CTA-861-3 mastering metadata（HDR10 直通）
eglSurfaceAttrib(dpy, surf, EGL_SMPTE2086_MAX_LUMINANCE_EXT, 1000); // cd/m2
eglSurfaceAttrib(dpy, surf, EGL_SMPTE2086_MIN_LUMINANCE_EXT, 1);    // x10000 缩放
```

## 决策表

| 设备能力 | 路径 |
|:---|:---|
| SDR sRGB | sRGB 表面 + filmic/ACES tone map |
| WCG 无 HDR | Display-P3 色彩空间表面，SDR 亮度范围 |
| HDR10 面板 | scRGB-linear 表面 + CTA-861-3 metadata + 线性管线 |

## 常见陷阱

| 陷阱 | 后果 | 修正 |
|:-----|:-----|:-----|
| 不查能力默认 HDR | SDR 屏画面过曝/发灰 | 运行时查询 + 降级路径 |
| 缺 CTA-861-3 metadata | HDR 内容被当 SDR | 填母带意图元数据 |
| 中途存 tonemapped sRGB8 | 二次转换精度损失 | 全程线性到最终输出 |
| UI 色彩空间不匹配 | UI 发灰/过饱和 | 与场景同空间 |
| 只在 sRGB 开发机验证 | 色彩 bug 不可见 | WCG + HDR 真机实测 |

## 关联卡片

- [02-texture-formats-compression](02-texture-formats-compression.md) — 纹理格式基础
- [05-shader-precision-layout](05-shader-precision-layout.md) — 线性管线精度（RGBA16F 用 highp）
- [04-framebuffer-objects](04-framebuffer-objects.md) — HDR FBO 生命周期
