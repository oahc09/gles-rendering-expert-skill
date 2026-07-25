# EGL Context 生命周期 & 多线程 & Context Lost

> **Category**: EGL / Platform | **GLES Version**: EGL 1.4+ | **Source**: `references/rules/egl-and-context.md`

## 核心规则

1. **初始化顺序**：`eglGetDisplay` → `eglInitialize` → `eglChooseConfig` → `eglCreateContext` → `eglCreateWindowSurface` → `eglMakeCurrent`。
2. **销毁顺序**：`eglMakeCurrent(NO_SURFACE/NO_CONTEXT)` → `eglDestroySurface` → `eglDestroyContext` → `eglTerminate`。
3. **每线程最多一个 current context**；`eglMakeCurrent` 是 per-thread 的。
4. **共享上下文**：共享对象 = Textures, Buffers, Shaders, Programs, Samplers, Sync；**不共享** = VAO, FBO, Query（per-context）。
5. **跨线程 GPU 资源交接必须用 `glFenceSync`**：worker 上传后插 fence → render 线程 `glWaitSync` 后使用。
6. **Android Context Lost**：`eglSwapBuffers` 返回 `EGL_FALSE` + `EGL_CONTEXT_LOST` → 销毁旧 EGL 对象 → 重建 context/surface → 从 CPU 缓存重建所有 GPU 资源。
7. **从第一天就设计 context loss 恢复**——所有 GPU 资源必须可从 CPU 数据重建。
8. Worker 线程优先用 `EGL_KHR_surfaceless_context` 或 1×1 Pbuffer。

## 代码模式

```cpp
// ✅ 跨线程纹理交接
// Worker thread:
glTexSubImage2D(GL_TEXTURE_2D, 0, 0, 0, w, h, GL_RGBA, GL_UNSIGNED_BYTE, px);
GLsync fence = glFenceSync(GL_SYNC_GPU_COMMANDS_COMPLETE, 0);
renderThread.Notify(texId, fence);

// Render thread:
glWaitSync(fence, 0, GL_TIMEOUT_IGNORED);
glDeleteSync(fence);
glBindTexture(GL_TEXTURE_2D, texId);  // safe

// ✅ Context lost 检测
if (!eglSwapBuffers(display, surface)) {
    if (eglGetError() == EGL_CONTEXT_LOST) HandleContextLost();
}
```

## 常见陷阱

| 陷阱 | 后果 | 修正 |
|:-----|:-----|:-----|
| 两线程同时 MakeCurrent 同一 context | 未定义行为 | 每线程独立 context（shared） |
| Worker 上传后不加 fence 就通知 render | 渲染到未完成纹理 | `glFenceSync` + `glWaitSync` |
| 不处理 context loss | 后台回前台黑屏/崩溃 | ResourceRegistry + RebuildAll |
| 销毁 context 前不 MakeCurrent(null) | 资源泄漏 | 先 release 再 destroy |
| Android `APP_CMD_TERM_WINDOW` 后继续调 GL | 崩溃 | 暂停渲染直到 `APP_CMD_INIT_WINDOW` |

## 关联卡片

- [11-synchronization](11-synchronization.md) — Fence sync 详细用法
- [04-framebuffer-objects](04-framebuffer-objects.md) — FBO 是 per-context 不共享
- [08-tbdr-bandwidth](08-tbdr-bandwidth.md) — EGL swap behavior 与 TBDR
