# GPU 驱动剔除

> **Category**: Culling / GPU-Driven | **GLES Version**: 3.0 (TF) / 3.1 (compute+indirect) | **Source**: `references/rules/gpu-culling.md`

## 核心规则

1. **3.1 标准管线**：包围体数组 → compute 剔除（视锥+LOD+小图元）→ 每元素写/清零自己的 `DrawArraysIndirectCommand` 槽（count=0 即跳过，近乎免费）→ `glMultiDrawArraysIndirect` 配 `GL_DRAW_INDIRECT_BUFFER`。CPU 永不回读可见性。仅当元素数远超存活数才加 atomic 压实。
2. **链接 pass 间的 barrier 纪律**：dispatch 与 indirect draw 之间 `glMemoryBarrier(GL_COMMAND_BARRIER_BIT | GL_DRAW_INDIRECT_BARRIER_BIT | GL_VERTEX_ATTRIB_ARRAY_BARRIER_BIT)`；TBDR release 驱动无校验层，漏 barrier = 一帧竞态。
3. **遮挡剔除是最后手段**：occlusion query 强制提前 resolve samples → TBDR tile flush。用 `GL_ANY_SAMPLES_PASSED_CONSERVATIVE`，只测粗簇不测单对象，接受 1 帧延迟；用 `GL_QUERY_RESULT_AVAILABLE` 延后读取，禁阻塞读 `GL_QUERY_RESULT`。
4. **层级深度优于遮挡查询**：1/16 分辨率早期 Z pass（`glDrawBuffer(GL_NONE)`+深度后失效），compute 采 hi-Z 做视锥+深度测试（ReSTricted 思路移植 ES 3.1）。
5. **视锥 6 平面入 UBO**（归一化 vec4）；per-instance 做球测试 `dot(plane,center) >= -radius`，不用 AABB。
6. **稳定性优先于最优性**：LOD/剔除决策留滞回带；帧间一致的输出缓冲排序比多剔 5% 更重要。
7. **小图元剔除**：投影尺寸 <~2px 的实例丢弃（tile GPU 上图元 setup 非免费）。
8. **GLES 上限**：无 mesh shader / 无 bindless / 无 shader-driven 光栅化——上面即 ES GPU-driven 天花板。

## 代码模式

```glsl
// cull.comp — 310 es — 每 batch 一线程，逐槽预测（无压实、无跨线程排序）
#version 310 es
layout(local_size_x = 64) in;
struct Batch { vec4 sphere; uvec2 range; };
layout(std140, binding=0) uniform Frustum { vec4 planes[6]; };
layout(std430, binding=1) readonly buffer Batches { Batch items[]; } u_Batch;
layout(std430, binding=3) buffer DrawArgs { uvec4 cmd[]; } u_Draw; // 必须是 SSBO，计算不能写 UBO
uniform uint u_BatchCount;
void main() {
    uint b = gl_GlobalInvocationID.x;
    if (b >= u_BatchCount) return;              // 本核无 barrier，guard 安全
    bool vis = true;
    for (int p=0;p<6;++p) vis = vis && dot(planes[p].xyz,u_Batch.items[b].sphere.xyz)
                                    + planes[p].w >= 0.0;
    Batch bt = u_Batch.items[b];
    u_Draw.cmd[b] = vis ? uvec4(bt.range.y,1u,bt.range.x,0u) : uvec4(0u);
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
