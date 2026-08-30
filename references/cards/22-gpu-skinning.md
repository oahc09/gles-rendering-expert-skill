# GPU 骨骼蒙皮

> **Category**: Animation | **GLES Version**: 3.0/3.1 | **Source**: `references/rules/gpu-skinning.md`

## 核心规则

1. **矩阵调色板存法**：默认 **UBO**（`std140`，GLES 3.0，~64–120 骨骼）；骨骼多或数量每帧变化用 **SSBO**（`std430`，GLES 3.1）；顶点纹理调色板是 GLES 2.0 时代遗留，3.0+ 不用。
2. **每顶点 4 个骨骼影响**（`ivec4` 索引 + `vec4` 权重）是移动端标准；8 影响是 2 倍顶点开销。
3. 混合后**必须重新归一化法线**（旋转混合会破坏单位长度）。
4. 权重可能不归一：混合前 `w / dot(w, 1)` 防御性归一。
5. **调色板每帧更新一次**（`glBufferSubData` 或 orphan 映射），不是每个 draw。
6. **蒙皮包围盒要膨胀**——蒙皮顶点会超出绑定姿势 AABB，否则剔除时物体弹出。
7. 蒙皮是顶点阶段开销：VS-bound 时先减骨骼数/影响数，再砍片元质量。
8. 大旋转关节质量要求高时用 **dual-quaternion** 蒙皮（防糖纸扭转），但 ALU 更贵。

## 代码模式

```glsl
// VS：UBO 调色板 + 4 影响（binding= 需 3.10；3.00 用 glUniformBlockBinding）
#define MAX_BONES 96
layout(std140, binding = 2) uniform SkinningBlock { mat4 u_Bones[MAX_BONES]; };

void main() {
    mediump vec4 w = a_BoneWeight / max(dot(a_BoneWeight, vec4(1.0)), 1e-5);
    mat4 skin = u_Bones[a_BoneIndex.x] * w.x + u_Bones[a_BoneIndex.y] * w.y
              + u_Bones[a_BoneIndex.z] * w.z + u_Bones[a_BoneIndex.w] * w.w;
    gl_Position = u_ViewProj * (skin * vec4(a_Position, 1.0));
    v_Normal = normalize(mat3(skin) * a_Normal);   // 重新归一化
}
```

## 常见陷阱

| 陷阱 | 症状 | 修正 |
|:-----|:-----|:-----|
| 骨骼数超 UBO 预算 | 链接错误 | 换 SSBO（GLES 3.1） |
| 权重未归一 | 网格收缩 | 混合前归一化权重 |
| 混合后不重归一化法线 | 光照变暗/条带 | `normalize(mat3(skin)*n)` |
| 绑定姿势 AABB 剔除 | 物体屏幕边缘弹出 | 膨胀包围盒 |
| 每 draw 更新调色板 | 带宽浪费 | 每帧一次 |
| 默认 8 骨骼影响 | 2× 顶点开销 | 4 影响 |

## 关联卡片

- [03-buffer-objects](03-buffer-objects.md) — UBO/SSBO 布局与更新
- [05-shader-precision-layout](05-shader-precision-layout.md) — VS 精度（蒙皮矩阵用 highp）
- [12-draw-call-optimization](12-draw-call-optimization.md) — 实例化同姿态蒙皮
