# 聚类前向光照 (Forward+)

> **Category**: Lighting | **GLES Version**: 3.1+ (compute+SSBO) | **Source**: `references/rules/clustered-lighting.md`

## 核心规则

1. **版本门槛**：完整 Forward+ 需 compute+SSBO+atomic（GLES **3.1+**）；3.0 只能用 UBO 批量前向或模板分块。
2. **网格尺寸**：16×9 屏幕 tile × 24–32 深度 slice 是移动甜点；平行光留在全局小列表处处评估，只有点/聚光进聚类。
3. **对数 Z 分层**：`slice = clamp(int(log2(zFar/z)/log2(zFar/zNear)*slices),0,slices-1)`；均匀 slice 近相机浪费精度。
4. **剔除 compute（每 cluster 一个 workgroup）**：光球 vs cluster AABB 六平面测试，存活索引进 per-cluster 列表（`atomicAdd` 计数）。**硬上限 lights/cluster（~64）**,溢出走 remainder；组内 `memoryBarrierShared()` 在 `barrier()` 前。
5. **dispatch 与着色之间 `glMemoryBarrier(GL_SHADER_STORAGE_BARRIER_BIT)`**——片段读 compute 写的；漏 barrier release 驱动表现为灯闪烁。
6. **片段侧查表**：`clusterIdx = (y/tileH)*gridX*gridZ + (x/tileW)*gridZ + slice`，行主序在 host/shader 保持同源；内层循环 `for(i=0;i<min(count,CAP);++i)` 常量上界便于展开。
7. **带宽决定收益**：列表 = clusters×cap×2B(uint16)+counts，16×9×32×64×2B≈590KB，远小于 G-Buffer MRT ≥12B/px 每帧读写。列表项用 uint16。
8. **单前向 pass 寄存器累加**；需预 pass（decal/复杂 BSDF）用 PLS/framebuffer-fetch 留在 tile——除非 tile 预算确知溢出，否则不做"类延迟"MRT+全屏 resolve。
9. **阴影交互**：聚类×per-light 阴影图会爆带宽——只聚类无阴影光，保留 1–2 个阴影"主光"在全局列表。
10. **厂商**：PowerVR HSR 已消隐，聚类近免费，勿加深度预 pass；Mali 注意 warp 内 cluster 计数分歧；Adreno 可用 `QCOM_shading_rate` 联动列表密集区。

## 代码模式

```glsl
// lightcull.comp — 310 es — 每 workgroup 一 cluster（骨架）
#version 310 es
layout(local_size_x = 64) in;
layout(std140,binding=0) uniform ClusterGlob { vec4 planes[6]; uint u_LightCount; };
layout(std430,binding=0) readonly buffer Lights { vec4 posRadius[]; } u_Lights;
layout(std430,binding=1) writeonly buffer Lists { uint counts[]; uint indices[]; } u_Lists;
const uint CAP = 64u;
shared uint s_Count;
void main(){
    uint c = gl_WorkGroupID.x;
    if (gl_LocalInvocationIndex==0u) s_Count=0u;
    memoryBarrierShared(); barrier();
    for (uint l=gl_LocalInvocationIndex; l<u_LightCount; l+=64u){
        vec4 L=u_Lights.posRadius[l]; bool hit=true;
        for(int p=0;p<6;++p) hit=hit && dot(planes[p].xyz,L.xyz)+planes[p].w>=-L.w;
        if(hit){ uint slot=atomicAdd(s_Count,1u); if(slot<CAP) u_Lists.indices[c*CAP+slot]=l; }
    }
    memoryBarrierShared(); barrier();
    if(gl_LocalInvocationIndex==0u) u_Lists.counts[c]=min(s_Count,CAP);
}
```

## 常见陷阱

| 陷阱 | 后果 | 修正 |
|:-----|:-----|:-----|
| 漏 `GL_SHADER_STORAGE_BARRIER_BIT` | 灯光滞后/闪烁 | dispatch 与 draw 间 barrier |
| 均匀 Z 分层 | 近相机列表暴涨 | 对数分层 |
| 无上限 per-cluster 循环 | 寄存器压力毁 occupancy | 固定 CAP+溢出表 |
| host/shader cluster 公式不一致 | 光照条纹错位 | 共享头文件常量 |
| 阴影光也聚类 | 阴影图×列表长度爆炸 | 全局主光（规则 9） |
| "以防万一"上 G-Buffer MRT | 每像素 +GB/s DRAM | PLS/fetch 或单 pass 累加 |
| uint32 光索引 | 列表带宽翻倍 | uint16 列表 |

## 关联卡片

- [06-compute-shader](06-compute-shader.md) — barrier/atomic
- [09-overdraw-fillrate](09-overdraw-fillrate.md) — 前向 overdraw
- [13-mali-pls-multiview](13-mali-pls-multiview.md) — PLS 免回 DRAM
- [16-powervr-hsr-img-extensions](16-powervr-hsr-img-extensions.md) — HSR 消隐
- [21-shadow-mapping](21-shadow-mapping.md) — 主光阴影
