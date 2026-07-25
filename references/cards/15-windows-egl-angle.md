# Windows Platform — EGL / ANGLE / Windows-on-ARM

> **Category**: Platform | **GLES Version**: 3.0/3.1 via ANGLE | **Source**: `references/rules/windows-platform.md`

## 核心规则

1. **Windows 无原生 GLES 驱动**。裸 WGL context 拿到的是**桌面 OpenGL**（语义不同：无 `precision` 要求、扩展集不同）——真正的 GLES 走 **ANGLE**。
2. **ANGLE** 把 GLES 2.0/3.0/3.1 翻译到后端：**D3D11**（Windows 默认）、**Vulkan**、桌面 GL；随程序分发 `libEGL.dll` + `libGLESv2.dll`。
3. **显式固定后端**：用 `EGL_ANGLE_platform_angle` 扩展 + `eglGetPlatformDisplayEXT`，桌面用 D3D11，Windows-on-ARM 用 Vulkan——不要依赖默认值。
4. **创建 context 后运行时校验 GLES 版本**（`glGetString(GL_VERSION)`）——ANGLE 的 3.1 支持取决于后端与 feature level。
5. **Windows-on-ARM (Snapdragon) = 真 Adreno 硬件**：`references/rules/adreno/*` 全部适用（GMEM、LRZ、VRS、on-tile MSAA）；优先 Vulkan 后端；必须 ARM64 原生构建，x64 模拟性能不可信。
6. **Android 模拟器 GPU 是宿主机代理**（host driver / ANGLE / SwiftShader）：仅做**功能**测试，**性能/带宽必须真机测**。
7. **保留 TBDR 优化**：`glInvalidateFramebuffer`、pass 开始 clear、on-tile MSAA 在桌面是廉价 no-op，绝不为 Windows 构建 `#ifdef` 掉——目标机是 Adreno/Mali。
8. **不要链接 `opengl32.lib`**；ANGLE DLL 需 post-build 拷到可执行文件旁。

## 代码模式

```cpp
// ANGLE EGL tokens — not in standard Khronos eglext.h, must guard:
#ifndef EGL_ANGLE_platform_angle
#define EGL_ANGLE_platform_angle 1
#define EGL_PLATFORM_ANGLE_ANGLE              0x3202
#define EGL_PLATFORM_ANGLE_TYPE_ANGLE         0x3203
#define EGL_PLATFORM_ANGLE_TYPE_D3D11_ANGLE   0x3208
#define EGL_PLATFORM_ANGLE_TYPE_VULKAN_ANGLE  0x3450
#endif

// ANGLE：固定 D3D11 后端初始化 EGL
auto eglGetPlatformDisplayEXT =
    (PFNEGLGETPLATFORMDISPLAYEXTPROC)eglGetProcAddress("eglGetPlatformDisplayEXT");
const EGLint da[] = { EGL_PLATFORM_ANGLE_TYPE_ANGLE,
                      EGL_PLATFORM_ANGLE_TYPE_D3D11_ANGLE, EGL_NONE };
EGLDisplay dpy = eglGetPlatformDisplayEXT(
    EGL_PLATFORM_ANGLE_ANGLE, EGL_DEFAULT_DISPLAY, da);
eglInitialize(dpy, &major, &minor);
const EGLint ca[] = { EGL_CONTEXT_CLIENT_VERSION, 3, EGL_NONE };
EGLContext ctx = eglCreateContext(dpy, cfg, EGL_NO_CONTEXT, ca);
// 校验：glGetString(GL_VERSION) → "OpenGL ES 3.1 (ANGLE ...)"
```

```bat
REM --- Import library from pre-built ANGLE DLL (Developer Command Prompt) ---
dumpbin /exports libEGL.dll > libEGL.exports.txt
REM → 编辑为 libEGL.def (LIBRARY libEGL / EXPORTS / eglGetDisplay / ...)
lib /def:libEGL.def /out:libEGL.lib /machine:x64
```

```cmake
# vcpkg path:
find_package(unofficial-angle CONFIG REQUIRED)
target_link_libraries(app PRIVATE
    unofficial::angle::libEGL unofficial::angle::libGLESv2)
# OR pre-built .lib path:
target_link_libraries(app PRIVATE
    ${CMAKE_SOURCE_DIR}/third_party/angle/libEGL.lib
    ${CMAKE_SOURCE_DIR}/third_party/angle/libGLESv2.lib)
add_custom_command(TARGET app POST_BUILD COMMAND ${CMAKE_COMMAND} -E
    copy_if_different ${ANGLE_DLL_DIR}/libEGL.dll
    ${ANGLE_DLL_DIR}/libGLESv2.dll $<TARGET_FILE_DIR:app>)
```

## 常见陷阱

| 陷阱 | 后果 | 修正 |
|:-----|:-----|:-----|
| 用 WGL/`opengl32` 当 GLES | 桌面 GL 语义，“PC 能跑真机崩” | 走 ANGLE `libEGL`/`libGLESv2` |
| 不固定 ANGLE 后端 | 各机器行为不一致 | 显式 D3D11 / Vulkan |
| Khronos eglext.h 缺 ANGLE token | 编译报 undefined symbol | `#ifndef` 守卫宏 + 数值 fallback |
| 预构建 DLL 无 .lib | 链接报 unresolved external | `dumpbin→.def→lib /def:` 生成 import lib |
| vcpkg 构建 ANGLE 超时/失败 | 30+ min、磁盘爆 | Chrome/Edge 提取预构建 DLL 作备选 |
| 信任模拟器性能数据 | 带宽/填充率结论错误 | 真机测性能 |
| 为 Windows 去掉 invalidate/clear | 目标机 GMEM 流量暴涨 | 保留 TBDR 优化 |
| 忘记拷 ANGLE DLL | 运行时加载失败 | post-build copy |
| WoA 下用 x64 模拟构建 | 性能不代表原生 | ARM64 原生构建 |

## 关联卡片

- [07-egl-context-lifecycle](07-egl-context-lifecycle.md) — EGL 初始化/销毁通用规则
- [01-api-version-constraints](01-api-version-constraints.md) — 桌面 GL 禁用 & 版本约束
- [14-adreno-gmem-vrs-lrz](14-adreno-gmem-vrs-lrz.md) — Windows-on-ARM 复用的 Adreno 规则
- [08-tbdr-bandwidth](08-tbdr-bandwidth.md) — 需保留的 TBDR 带宽优化
