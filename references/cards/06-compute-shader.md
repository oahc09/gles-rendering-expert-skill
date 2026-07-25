# Compute Shader — 工作组织 & 同步

> **Category**: Compute | **GLES Version**: 3.1+ (GLSL ES 3.10) | **Source**: `references/rules/glsl-es-optimization.md` §5, `references/rules/mali-arm-best-practices.md` §3

## 核心规则

1. `#version 310 es` + `layout(local_size_x, local_size_y, local_size_z) in;`；local_size 选 warp 倍数（Adreno 32, Mali 16）；最低保证 128 invocations/workgroup。
2. **SSBO 用 `std430`**（紧凑）；最小 128 MiB；支持 unsized array + `.length()`。
3. **Shader image 纹理必须不可变**（`glTexStorage*`）；format qualifier 必须匹配 `glBindImageTexture` 的 format 参数；用 `layout(binding=N)` 而非 `glUniform1i`。
4. **`shared` 内存** ≥16 KiB，未初始化、非持久——用于 workgroup 内数据复用以减少带宽。
5. **同步正确性（关键）**：
   - Workgroup 内：`memoryBarrierShared()` **必须在** `barrier()` **之前**；`barrier()` 只能在 dynamically-uniform 控制流中调用。
   - 跨 GL 命令：`glMemoryBarrier(<BITS>)` 描述下一步如何读取数据（如 `GL_VERTEX_ATTRIB_ARRAY_BARRIER_BIT`）。
6. **TBDR 友好**：fragment image load/store 用 `glMemoryBarrierByRegion()`（避免全 tile flush）；加 `layout(early_fragment_tests) in;` 恢复 early-Z。
7. Compute 相对 GL 其余部分 **异步执行**——dispatch 后不自动同步。

## 代码模式

```glsl
#version 310 es
layout(local_size_x = 64) in;
layout(std430, binding = 0) buffer ParticleBuf {
    Particle particles[];
};
uniform uint u_Count;
uniform float u_Dt;

shared float s_MaxSpeed;  // workgroup-local reduction

void main() {
    uint id = gl_GlobalInvocationID.x;
    if (id >= u_Count) return;
    particles[id].pos += particles[id].vel * u_Dt;

    // Workgroup reduction example
    s_MaxSpeed = 0.0;
    memoryBarrierShared();  // ← MUST be before barrier()
    barrier();
    // ... atomicMax into s_MaxSpeed ...
}
```

```cpp
// Host: dispatch → barrier → draw from same SSBO
glDispatchCompute(groups, 1, 1);
glMemoryBarrier(GL_VERTEX_ATTRIB_ARRAY_BARRIER_BIT);
glDrawElements(GL_TRIANGLES, count, GL_UNSIGNED_SHORT, nullptr);
```

## 常见陷阱

| 陷阱 | 后果 | 修正 |
|:-----|:-----|:-----|
| `barrier()` 前不调 `memoryBarrierShared()` | 读到 stale shared 数据 | 先 memory barrier 再 execution barrier |
| `barrier()` 在 divergent branch 中 | 死锁 | 仅 uniform 分支或所有线程都到达 |
| Dispatch 后直接 draw 同一 SSBO | 读到旧数据 | `glMemoryBarrier(GL_VERTEX_ATTRIB_ARRAY_BARRIER_BIT)` |
| 用 `glTexImage2D` 创建 image 纹理 | 未定义行为 | `glTexStorage2D` 不可变 |
| 全屏 fragment image 用 `glMemoryBarrier` | 全 tile flush 到 DRAM | `glMemoryBarrierByRegion()` |
| local_size 非 warp 倍数 | 线程浪费 | Adreno→32, Mali→16 的倍数 |

## 关联卡片

- [03-buffer-objects](03-buffer-objects.md) — SSBO std430 布局
- [11-synchronization](11-synchronization.md) — Memory barrier 全表
- [09-overdraw-fillrate](09-overdraw-fillrate.md) — early_fragment_tests
