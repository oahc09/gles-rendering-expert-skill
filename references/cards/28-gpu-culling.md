# GPU 驱动剔除

> **Category**: Culling / GPU-Driven | **GLES Version**: 3.0 (TF) / 3.1 (compute+indirect) | **Source**: `references/rules/gpu-culling.md`

## 核心规则

1. **3.1 核心路径**：compute 每元素写/清零独立的 indirect 槽，绑定 `GL_DRAW_INDIRECT_BUFFER` 后按固定偏移分别调用 `glDrawArraysIndirect`（索引版 `glDrawElementsIndirect`），不回读可见性。仅在当前 context 支持 `GL_EXT_multi_draw_indirect` 且成功加载带 `EXT` 后缀的入口时合并提交；否则保留核心循环。
2. **按消费者选择 barrier**：indirect 参数用 `GL_COMMAND_BARRIER_BIT`；compute 还写了随后读取的 vertex 属性或 SSBO 时，再加 `GL_VERTEX_ATTRIB_ARRAY_BARRIER_BIT` 或 `GL_SHADER_STORAGE_BARRIER_BIT`。
3. **遮挡剔除是最后手段**：occlusion query 强制提前 resolve samples → TBDR tile flush。用 `GL_ANY_SAMPLES_PASSED_CONSERVATIVE`，只测粗簇不测单对象，接受 1 帧延迟；用 `GL_QUERY_RESULT_AVAILABLE` 延后读取，禁阻塞读 `GL_QUERY_RESULT`。
4. **层级深度优于遮挡查询**：depth-only 用户 FBO 用 `glDrawBuffers(1, &none)` 和 `glReadBuffer(GL_NONE)`，检查完整性；保留深度纹理直至 Hi-Z 消费结束。
5. **视锥 6 平面入 UBO**（归一化 vec4）；per-instance 做球测试 `dot(plane,center) >= -radius`，不用 AABB。
6. **稳定性优先于最优性**：LOD/剔除决策留滞回带；帧间一致的输出缓冲排序比多剔 5% 更重要。
7. **小图元剔除**：投影尺寸 <~2px 的实例丢弃（tile GPU 上图元 setup 非免费）。
8. **GLES 上限**：无 mesh shader / 无 bindless / 无 shader-driven 光栅化——上面即 ES GPU-driven 天花板。

## 代码模式

```glsl
// cull.comp — GLSL ES 3.10 — one thread per batch, per-slot predication.
// No compaction, no cross-thread ordering: every slot is written every frame.
#version 310 es
layout(local_size_x = 64) in;

struct Batch { vec4 sphere;        // xyz = center, w = radius
               uvec2 range; };     // first, count in the shared static VB

layout(std140, binding = 0) uniform Frustum { vec4 planes[6]; };
layout(std430, binding = 1) readonly buffer Batches { Batch items[]; } u_Batch;
// DrawArraysIndirectCommand == uvec4 — the args block MUST be `buffer` (SSBO):
// compute cannot write a UBO, and the same GL buffer is rebound as
// GL_DRAW_INDIRECT_BUFFER on the host.
layout(std430, binding = 3) buffer DrawArgs { uvec4 cmd[]; } u_Draw;

uniform uint u_BatchCount;

void main() {
    uint b = gl_GlobalInvocationID.x;
    if (b >= u_BatchCount) return;  // no barrier in this kernel, guard is safe
    Batch bt = u_Batch.items[b];
    bool visible = true;
    for (int p = 0; p < 6; ++p)
        visible = visible && dot(planes[p].xyz, bt.sphere.xyz)
                            + planes[p].w >= -bt.sphere.w;
    u_Draw.cmd[b] = visible
        ? uvec4(bt.range.y, 1u, bt.range.x, 0u)   // count, instanceCount, first, reservedMustBeZero
        : uvec4(0u);                              // zero-count draw: skipped
}
```

## 常见陷阱

| 陷阱 | 后果 | 修正 |
|:-----|:-----|:-----|
| 剔除与 draw 间漏 `glMemoryBarrier` | 实例数据过期/损坏 | 声明全部 dependent-use bit |
| 阻塞读 occlusion 结果 | 每帧多毫秒 CPU 停顿 | `GL_QUERY_RESULT_AVAILABLE`+1 帧延迟 |
| 逐对象遮挡查询 | 每查询一次 tile flush，比不剔还慢 | 粗簇或 hi-Z compute |
| 每帧重分配缓冲 | orphan 流量+驱动开销 | 最坏尺寸持久缓冲 |
| 决策逐帧翻转 | pop-in | 滞回带+帧间稳定排序 |

## 关联卡片

- [12-draw-call-optimization](12-draw-call-optimization.md) — indirect draw
- [06-compute-shader](06-compute-shader.md) — barrier 纪律
- [25-transform-feedback](25-transform-feedback.md) — 3.0 剔除路径
- [08-tbdr-bandwidth](08-tbdr-bandwidth.md) — 查询为何 flush tile
