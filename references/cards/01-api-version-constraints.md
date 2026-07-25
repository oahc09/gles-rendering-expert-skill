# API 版本约束 & 桌面 OpenGL 禁用

> **Category**: API Standards | **GLES Version**: 3.0 / 3.1 / 3.2 | **Source**: `references/rules/gles-api-standards.md`

## 核心规则

1. **默认目标 OpenGL ES 3.0 + GLSL ES 3.00**；仅在明确需要时使用 3.1/3.2 特性。
2. **严禁生成任何桌面 OpenGL API**：`glBegin/glEnd`、`glVertex*`、`glMatrixMode`、`glLight`、`glFog`、`glPushAttrib`、Display Lists、`GL_QUADS`、`glPolygonMode`、`glDrawPixels`、Evaluators 等。
3. 版本-特性对应：
   - **3.0**: VAO, UBO, MRT, ETC2, Transform Feedback, Instancing, PBO
   - **3.1**: Compute Shader, SSBO, Image Load/Store, Indirect Draw, Separate Shader Objects
   - **3.2**: Geometry Shader, Tessellation, ASTC, Debug Output, Blend Equation Advanced
4. 使用扩展前必须：查询可用性 → `eglGetProcAddress` 加载函数指针 → 提供 fallback。
5. 图元类型仅限：`GL_TRIANGLES`、`GL_TRIANGLE_STRIP`、`GL_TRIANGLE_FAN`、`GL_POINTS`、`GL_LINES`、`GL_LINE_STRIP`、`GL_LINE_LOOP`。

## 代码模式

```cpp
// ✅ 正确的 GLES 3.0 绘制
glBindVertexArray(vao);
glDrawElements(GL_TRIANGLES, indexCount, GL_UNSIGNED_SHORT, nullptr);

// ✅ 扩展检查
const char* exts = (const char*)glGetString(GL_EXTENSIONS);
bool hasASTC = strstr(exts, "GL_KHR_texture_compression_astc_ldr") != nullptr;
```

## 常见陷阱

| 陷阱 | 后果 | 修正 |
|:-----|:-----|:-----|
| 使用 `glBegin/glEnd` 立即模式 | 编译失败（GLES 无此 API） | VBO + VAO + `glDrawArrays` |
| `GL_QUADS` 图元 | 无效枚举 | 拆分为三角形 |
| `glPolygonMode(GL_LINE)` 线框 | 不支持 | 重心坐标 shader 或 Geometry Shader (3.2) |
| `glLineWidth(>1.0)` | 仅保证 1.0 | 用几何体模拟宽线 |
| 未检查扩展直接使用 | 运行时崩溃 | 查询 + fallback |

## 关联卡片

- [05-shader-precision-layout](05-shader-precision-layout.md) — GLSL ES 版本对应
- [02-texture-formats-compression](02-texture-formats-compression.md) — 格式严格配对
- [06-compute-shader](06-compute-shader.md) — 3.1+ 特性
