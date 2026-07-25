# 同步 — Fence / Memory Barrier / Buffer Orphaning

> **Category**: Synchronization | **GLES Version**: 3.0 / 3.1 | **Source**: `references/rules/gles-api-standards.md` §6, `references/rules/glsl-es-optimization.md` §5.5-5.6

## 核心规则

1. **CPU 等 GPU**：`glFenceSync` + `glClientWaitSync(timeout)`——带超时，不无限阻塞。
2. **GPU 等 GPU（跨队列/跨线程）**：`glWaitSync`——GPU 侧等待，CPU 不 stall。
3. **禁止 `glFinish()` 在渲染循环中**——仅用于 benchmark。
4. **Buffer orphaning**：`glBufferData(NULL)` 或 `GL_MAP_INVALIDATE_BUFFER_BIT` 避免 CPU/GPU 竞争同一存储。
5. **Compute 跨命令同步**：`glMemoryBarrier(<BITS>)` 描述下一步读取方式：
   - VBO 读取 → `GL_VERTEX_ATTRIB_ARRAY_BARRIER_BIT`
   - Texture 采样 → `GL_TEXTURE_FETCH_BARRIER_BIT`
   - Image load/store → `GL_SHADER_IMAGE_ACCESS_BARRIER_BIT`
   - Indirect draw → `GL_COMMAND_BARRIER_BIT`
6. **TBDR 友好**：fragment image 同像素读写用 `glMemoryBarrierByRegion()`（避免全 tile flush）。
7. **纹理回读**：PBO + `glReadPixels` 到 PBO → 下一帧 map（异步双缓冲）。

## 代码模式

```cpp
// ✅ Fence: CPU 等待特定 GPU 工作完成
GLsync fence = glFenceSync(GL_SYNC_GPU_COMMANDS_COMPLETE, 0);
GLenum r = glClientWaitSync(fence, GL_SYNC_FLUSH_COMMANDS_BIT, 5'000'000); // 5ms
if (r == GL_CONDITION_SATISFIED) { /* done */ }
glDeleteSync(fence);

// ✅ Compute → Draw 同步
glDispatchCompute(gx, 1, 1);
glMemoryBarrier(GL_VERTEX_ATTRIB_ARRAY_BARRIER_BIT);
glDrawElements(GL_TRIANGLES, count, GL_UNSIGNED_SHORT, nullptr);

// ✅ Buffer orphaning (避免 stall)
glBindBuffer(GL_ARRAY_BUFFER, vbo);
glBufferData(GL_ARRAY_BUFFER, size, nullptr, GL_DYNAMIC_DRAW); // orphan
void* p = glMapBufferRange(GL_ARRAY_BUFFER, 0, size,
    GL_MAP_WRITE_BIT | GL_MAP_INVALIDATE_BUFFER_BIT);
memcpy(p, newData, size);
glUnmapBuffer(GL_ARRAY_BUFFER);
```

## 常见陷阱

| 陷阱 | 后果 | 修正 |
|:-----|:-----|:-----|
| 渲染循环中 `glFinish()` | CPU/GPU 完全串行 | `glFenceSync` + timeout |
| Compute dispatch 后直接 draw | 读旧数据 | `glMemoryBarrier` 匹配读取方式 |
| `glMemoryBarrier(GL_ALL_BARRIER_BITS)` 滥用 | 过度同步，TBDR tile flush | 精确指定 bit；同像素用 ByRegion |
| 每帧 `glBufferData` 更新同一 buffer 不 orphan | CPU 等 GPU 用完旧数据 | orphan 或 triple-buffer |
| `glReadPixels` 到 CPU 指针 | 全管线 stall | PBO 异步 |

## 关联卡片

- [06-compute-shader](06-compute-shader.md) — Compute 同步详解
- [07-egl-context-lifecycle](07-egl-context-lifecycle.md) — 跨线程 fence
- [08-tbdr-bandwidth](08-tbdr-bandwidth.md) — glReadPixels / glFinish 禁令
