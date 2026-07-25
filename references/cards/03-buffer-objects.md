# Buffer Objects — VAO / VBO / UBO / SSBO / PBO

> **Category**: Buffer | **GLES Version**: 3.0 / 3.1 | **Source**: `references/rules/gles-api-standards.md` §4, `references/rules/glsl-es-optimization.md` §3, §5.3

## 核心规则

1. **始终使用 VAO**（GLES 3.0+ 默认 VAO name 0 已废弃）；先绑 VAO 再设顶点属性。
2. VBO usage hint 如实设置：`GL_STATIC_DRAW`（一次上传多次绘制）、`GL_DYNAMIC_DRAW`（每帧更新）、`GL_STREAM_DRAW`（每帧更新且只绘一次）。
3. 全量更新用 `glMapBufferRange` + `GL_MAP_WRITE_BIT | GL_MAP_INVALIDATE_BUFFER_BIT`（orphan 旧存储，避免同步阻塞）。
4. **UBO** 用 `std140` 布局，按更新频率分组（per-frame vs per-material），绑定到显式 binding point。
5. **SSBO**（3.1+）用 **`std430`** 布局（紧凑打包，不像 std140 把标量数组 pad 到 vec4）；最小保证 128 MiB；支持 unsized trailing array。
6. **PBO** 用于异步纹理上传/像素回读，避免 CPU-GPU 同步阻塞。
7. 映射指针 **不得跨帧持有** 而不 unmap。

## 代码模式

```cpp
// ✅ VAO + VBO 标准流程
glGenVertexArrays(1, &vao);
glBindVertexArray(vao);
glBindBuffer(GL_ARRAY_BUFFER, vbo);
glBufferData(GL_ARRAY_BUFFER, size, data, GL_STATIC_DRAW);
glEnableVertexAttribArray(0);
glVertexAttribPointer(0, 3, GL_FLOAT, GL_FALSE, stride, (void*)offset);
glBindVertexArray(0);

// ✅ UBO std140 (binding set from host via glUniformBlockBinding in ES 3.00;
//    layout(binding=N) requires ES 3.10+)
layout(std140) uniform Matrices {
    highp mat4 u_Model;   // offset 0
    highp mat4 u_View;    // offset 16
    highp mat4 u_Proj;    // offset 32
};

// ✅ SSBO std430 (requires GLES 3.1 / #version 310 es)
layout(std430, binding = 1) buffer Particles {
    Particle data[];      // unsized array, query .length()
};
```

## 常见陷阱

| 陷阱 | 后果 | 修正 |
|:-----|:-----|:-----|
| 不绑 VAO 直接设 attrib | INVALID_OPERATION (GLES 3.0+) | 先 `glBindVertexArray` |
| 每帧 `glBufferData` 更新 UBO | 重新分配存储，驱动 stall | `glBufferSubData` 或 `glMapBufferRange` |
| SSBO 用 `std140` | 标量数组 4× 内存浪费 | 改用 `std430` |
| 映射指针跨帧不 unmap | 未定义行为 / 内存泄漏 | 每帧结束前 `glUnmapBuffer` |
| PBO 回读后立即 map 同一 PBO | CPU 阻塞等待 GPU | 双 PBO ping-pong |

## 关联卡片

- [06-compute-shader](06-compute-shader.md) — SSBO 在 compute 中的使用
- [11-synchronization](11-synchronization.md) — Buffer orphaning & fence
- [12-draw-call-optimization](12-draw-call-optimization.md) — Instancing + VBO
