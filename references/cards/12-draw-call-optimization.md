# Draw Call 优化 — 批处理 / 实例化 / Indirect Draw

> **Category**: Draw Call / CPU | **GLES Version**: 3.0 / 3.1 | **Source**: `references/rules/mali-arm-best-practices.md` §7, `references/rules/gles-api-standards.md` §4

## 核心规则

1. **每个 draw call 有 CPU 开销**（状态验证、命令编码）——减少 draw call 数量是 CPU 端首要优化。
2. **Instancing**（GLES 3.0）：相同网格不同 transform → `glDrawArraysInstanced` / `glDrawElementsInstanced` + per-instance 属性或 UBO 数组。
3. **Indirect Draw**（GLES 3.1）：GPU 生成 draw 参数 → `glDrawArraysIndirect` / `glDrawElementsIndirect`；配合 compute culling 实现 GPU-driven rendering。
4. **Texture Array + Instancing** 渲染大量重复/平铺内容（地形 clipmap、植被）——少量 draw call 覆盖大量几何。
5. **Transform Feedback**（GLES 3.0）：捕获 vertex 阶段输出到 buffer——compute 不可用时的 GPU 粒子/boids 方案。
6. **PBO 异步流式上传**：大型/频繁更新数据（地形高度图）用 PBO + fence 避免 stall render thread。
7. **状态排序**：按 shader → texture → material 分组 draw call，减少状态切换。

## 代码模式

```cpp
// ✅ Instancing: 1000 个相同网格
glBindVertexArray(vao);
glBindBuffer(GL_ARRAY_BUFFER, instanceVbo);  // per-instance offsets
glEnableVertexAttribArray(3);
glVertexAttribPointer(3, 3, GL_FLOAT, GL_FALSE, sizeof(vec3), nullptr);
glVertexAttribDivisor(3, 1);  // advance once per instance
glDrawElementsInstanced(GL_TRIANGLES, idxCount, GL_UNSIGNED_SHORT, nullptr, 1000);

// ✅ Indirect Draw (GPU-driven, GLES 3.1)
// Compute shader fills DrawArraysIndirectCommand in an SSBO
glDispatchCompute(numGroups, 1, 1);
glMemoryBarrier(GL_COMMAND_BARRIER_BIT);
glBindBuffer(GL_DRAW_INDIRECT_BUFFER, cmdBuf);
glDrawArraysIndirect(GL_TRIANGLES, nullptr);
```

## 常见陷阱

| 陷阱 | 后果 | 修正 |
|:-----|:-----|:-----|
| 每个物体一个 draw call（1000+） | CPU bound | Instancing / batching |
| 每帧重新上传所有顶点 | CPU→GPU 带宽 + stall | `GL_STATIC_DRAW` + orphan 仅更新部分 |
| 频繁切换 shader/texture | 状态验证开销 | 按 material 排序 |
| 同步 PBO 上传大纹理 | Render thread stall | 异步 PBO + `glFenceSync` |
| 不用 indirect draw 做 GPU culling | CPU 回读 visible list | Compute cull → indirect draw |

## 关联卡片

- [03-buffer-objects](03-buffer-objects.md) — VBO/VAO/PBO 基础
- [06-compute-shader](06-compute-shader.md) — GPU-driven culling + indirect
- [11-synchronization](11-synchronization.md) — PBO fence 同步
