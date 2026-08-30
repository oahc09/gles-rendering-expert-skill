# Transform Feedback — GPU 侧缓冲更新

> **Category**: Buffer / Vertex Pipeline | **GLES Version**: 3.0 core | **Source**: `references/rules/transform-feedback.md`

## 核心规则

1. **链接前声明 varyings**：`glTransformFeedbackVaryings(program, n, names, GL_INTERLEAVED_ATTRIBS|GL_SEPARATE_ATTRIBS)` 必须在 `glLinkProgram` 之前——链接依赖输出清单。
2. 输出缓冲用 `glBindBufferBase(GL_TRANSFORM_FEEDBACK_BUFFER, index, buffer)` 绑定；INTERLEAVED 只用 index 0，SEPARATE 每个 varying 一个 index（上限 `GL_MAX_TRANSFORM_FEEDBACK_SEPARATE_ATTRIBS`，最小 4）。
3. `glBeginTransformFeedback(mode)` 的 mode 只有 `GL_POINTS`/`GL_LINES`/`GL_TRIANGLES`，且必须匹配末级 pre-rasterization 阶段的输出类型（有 GS 时匹配 GS 输出）。
4. 纯计算用途开 `GL_RASTERIZER_DISCARD`；需要边更新边渲染则不开。
5. 可变输出（GS 放大）用 `GL_TRANSFORM_FEEDBACK_PRIMITIVES_WRITTEN` 查询写入的图元数（注意：图元数 ≠ 顶点数）。
6. **Ping-pong 双缓冲**做迭代模拟；同一次 feedback 会话禁止读写同一段缓冲。缓冲尺寸按最坏情况（`max_vertices` 放大）分配。
7. **GLES 3.1+ 优先评估 compute shader**（随机访问/原子/共享内存）；TF 保留给 3.0 兼容或输出直接进 draw 的零拷贝场景（ARM SDK Boids 模式）。
8. ES 没有 `glGetBufferSubData`——CPU 回读用 fence + `glMapBufferRange(..., GL_MAP_READ_BIT)`。
9. TBDR 上 TF 只消耗顶点处理 + 缓冲写带宽，**无 tile 流量**。

## 代码模式

```cpp
// ✅ 粒子积分：A → B ping-pong，纯 GPU 循环
const GLchar* varyings[] = { "v_pos", "v_vel" };
glTransformFeedbackVaryings(simProgram, 2, varyings, GL_INTERLEAVED_ATTRIBS);
glLinkProgram(simProgram);

glBindBufferBase(GL_TRANSFORM_FEEDBACK_BUFFER, 0, bufB);
glUseProgram(simProgram);
glBindVertexArray(vaoA);                       // 从 bufA 读
glEnable(GL_RASTERIZER_DISCARD);
glBeginTransformFeedback(GL_POINTS);
glDrawArrays(GL_POINTS, 0, particleCount);
glEndTransformFeedback();
glDisable(GL_RASTERIZER_DISCARD);
std::swap(vaoA, vaoB); std::swap(bufA, bufB);  // 下一帧反向
```

## 常见陷阱

| 陷阱 | 后果 | 修正 |
|:-----|:-----|:-----|
| 链接后才调 `glTransformFeedbackVaryings` | varyings 不被捕获 | 链接前声明，重新链接 |
| feedback 缓冲按当前粒子数分配 | GS 放大时 `INVALID_OPERATION` | 按最坏情况分配 |
| `glBeginTransformFeedback` mode 与 GS 输出不符 | 报错 | 匹配 `triangle_strip` → `GL_TRIANGLES` 等 |
| 同缓冲读写同会话 | 未定义结果 | ping-pong 双缓冲 |
| 用 `glGetBufferSubData` 回读 | ES 无此函数，编译失败 | `glMapBufferRange` + fence |
| 3.1+ 场景硬用 TF | 丢失原子/共享内存能力 | 改用 compute（见卡片 06） |

## 关联卡片

- [03-buffer-objects](03-buffer-objects.md) — 缓冲与 usage hint
- [06-compute-shader](06-compute-shader.md) — 3.1+ 替代方案
- [26-geometry-shader](26-geometry-shader.md) — GS 放大输出
- [11-synchronization](11-synchronization.md) — fence 回读
