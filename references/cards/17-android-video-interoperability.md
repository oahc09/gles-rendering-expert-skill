# Android 视频纹理 & 缓冲区互操作

> **Category**: Interop | **GLES Version**: 3.0+ | **Source**: `references/rules/android-interoperability.md`

## 核心规则

1. 相机/解码器帧**只能**通过 `GL_TEXTURE_EXTERNAL_OES` + EGLImage 路径进入 GLES——不可 `glTexImage2D` 上传。
2. Shader 必须 `#extension GL_OES_EGL_image_external(_essl3) : require` + `samplerExternalOES`，运行时检查扩展。
3. 外部纹理强制 `GL_CLAMP_TO_EDGE` + `NEAREST/LINEAR` 过滤，**无 mipmap**（`glGenerateMipmap` 报错）。
4. 每帧由 `SurfaceTexture::updateTexImage()` 刷新内容，不要重复调用 `glEGLImageTargetTexture2DOES` 除非换 buffer。
5. YUV→RGB 由硬件完成，不要手写转换；仅在直接导入原始 plane（AHardwareBuffer 多平面）时手写。
6. API 26+ 优先 `AHardwareBuffer` + `EGL_ANDROID_get_native_client_buffer`（稳定 NDK C ABI），替代裸 gralloc。
7. **生产者/消费者必须 fence 同步**（`EGL_SYNC_NATIVE_FENCE_ANDROID` + `glWaitSync`），否则撕裂/花帧。
8. 销毁顺序：纹理 → EGLImage → AHardwareBuffer。

## 代码模式

```cpp
// ✅ AHardwareBuffer 导入（API 26+）
EGLClientBuffer cb = eglGetNativeClientBufferANDROID(ahb);
EGLint attrs[] = { EGL_IMAGE_PRESERVED_KHR, EGL_TRUE, EGL_NONE };
EGLImageKHR img = eglCreateImageKHR(dpy, EGL_NO_CONTEXT,
                                    EGL_NATIVE_BUFFER_ANDROID, cb, attrs);
glBindTexture(GL_TEXTURE_EXTERNAL_OES, tex);
glEGLImageTargetTexture2DOES(GL_TEXTURE_EXTERNAL_OES, img);
```

## 常见陷阱

| 陷阱 | 后果 | 修正 |
|:-----|:-----|:-----|
| 外部图绑到 `GL_TEXTURE_2D` | 黑屏/未定义 | 用 `GL_TEXTURE_EXTERNAL_OES` |
| 缺 `#extension` | 编译失败/采样错误 | 添加 require 指令 |
| `GL_REPEAT` wrap | 边缘未定义 | 强制 `CLAMP_TO_EDGE` |
| 忘记 `updateTexImage()` | 画面停在首帧 | 帧到达回调驱动 |
| 先销毁 EGLImage 后删纹理 | 驱动 use-after-free | 先删纹理 |
| 无 fence 同步直接绘制 | 撕裂/花帧 | `glWaitSync` 等生产者 fence |

## 关联卡片

- [02-texture-formats-compression](02-texture-formats-compression.md) — 普通纹理格式规则
- [07-egl-context-lifecycle](07-egl-context-lifecycle.md) — EGLImage 与上下文
- [11-synchronization](11-synchronization.md) — Fence 同步原语
