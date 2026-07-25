# Overdraw & Fill-Rate 优化

> **Category**: Performance / Fragment | **GLES Version**: All | **Source**: `references/rules/tbdr-bandwidth-rules.md` §5, `references/rules/mali-arm-best-practices.md` §8

## 核心规则

1. **不透明物体 front-to-back 排序**——最大化 early-Z 剔除，减少 fragment shader 执行次数。
2. **透明物体 back-to-front 排序**——正确 blend 所需；depth test on, depth write off。
3. **避免 `discard` / `gl_FragDepth`**——它们禁用 early-Z（Mali/Adreno 均受影响），导致所有 fragment 都执行 shader。
4. **合并全屏后处理 pass**：每个全屏 pass = `width × height × bpp` 读 + 写。能合一个 shader 就不拆多个。
5. **把 per-fragment 计算上移到 vertex shader 或 CPU**：线性插值结果（旋转/缩放矩阵、光照方向）用 varying 传入，fragment 只做最终组合。
6. **减少 dependent texture read** 和 fragment 中的 dynamic branch——用 `mix`/`step`/`smoothstep` 替代 data-dependent `if`。
7. 使用 `layout(early_fragment_tests) in;`（GLES 3.1+）恢复因 image/atomic 副作用而丢失的 early-Z。

## 代码模式

```glsl
// ❌ BAD: divergent branch + discard
if (texture(u_Mask, v_UV).a < 0.5) discard;  // 禁用 early-Z

// ✅ GOOD: alpha-to-coverage 或 blend（保留 early-Z）
// 或隔离 alpha-test 物体到单独 pass，不影响主场景 early-Z

// ✅ GOOD: 把计算移到 vertex
// Vertex: v_LightDir = normalize(u_LightPos - worldPos.xyz);
// Fragment: 直接用 v_LightDir（硬件免费插值）
```

```cpp
// ✅ 合并后处理
// 一个 shader 同时做 bloom extract + tonemap + FXAA
// 而非 3 个全屏 pass（省 2× 全屏读写带宽）
```

## 常见陷阱

| 陷阱 | 后果 | 修正 |
|:-----|:-----|:-----|
| 不透明物体 back-to-front | 大量 overdraw，fragment 白跑 | front-to-back 排序 |
| 大面积 `discard`（植被） | early-Z 失效，全屏 fragment cost | alpha blend 或独立 pass |
| 3 个后处理全屏 pass 不合并 | 3× 全屏带宽 | 合并为 1 个 shader |
| Fragment 中做矩阵运算 | 每像素 16 MAD×N | 移到 vertex/CPU，varying 传入 |
| 写 `gl_FragDepth` | late-Z，overdraw 全执行 | 避免；或 `early_fragment_tests` |

## 关联卡片

- [08-tbdr-bandwidth](08-tbdr-bandwidth.md) — 带宽模型 & FBO 切换
- [05-shader-precision-layout](05-shader-precision-layout.md) — Fragment 优化技巧
- [14-adreno-gmem-vrs-lrz](14-adreno-gmem-vrs-lrz.md) — Adreno LRZ & VRS
- [10-msaa-antialiasing](10-msaa-antialiasing.md) — MSAA 与 fill-rate
