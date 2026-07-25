# 纹理格式 & ASTC/ETC2 压缩

> **Category**: Texture | **GLES Version**: 3.0+ | **Source**: `references/rules/gles-api-standards.md` §3, `references/rules/mali-arm-best-practices.md` §4

## 核心规则

1. **始终使用压缩纹理**（ASTC 优先，ETC2 为 GLES 3.0 保底）。
2. GLES 要求 `glTexImage2D` 的 internalformat/format/type **严格配对**，不可随意组合。
3. 优先使用 **`glTexStorage2D`（不可变存储）** 而非 `glTexImage2D`——驱动优化更好，且 shader image 必须用不可变纹理。
4. **`glTexStorage2D` 的 `levels` 参数必须满足 `levels >= 1 + floor(log2(max(w,h)))`**——这是完整 mipmap chain 的层数。若 levels 小于此值，后续调用 `glGenerateMipmap` 会触发 `GL_INVALID_OPERATION`（不可变纹理不允许新增层级）。
5. **始终生成/附带 mipmaps**——减少纹理缓存 miss、带宽和走样。
6. ASTC 使用前必须 **运行时检查** `GL_KHR_texture_compression_astc_ldr`。
7. 选择 **满足视觉要求的最大 ASTC block（最低 bpp）**，不要一刀切 4x4。

## 代码模式

```cpp
// ✅ 不可变纹理 + mipmap（levels 必须覆盖完整 mip chain）
GLsizei mipLevels = 1 + static_cast<GLsizei>(std::floor(std::log2(
    static_cast<float>(std::max(w, h)))));
glBindTexture(GL_TEXTURE_2D, tex);
glTexStorage2D(GL_TEXTURE_2D, mipLevels, GL_RGBA8, w, h);
glTexSubImage2D(GL_TEXTURE_2D, 0, 0, 0, w, h, GL_RGBA, GL_UNSIGNED_BYTE, data);
glGenerateMipmap(GL_TEXTURE_2D);  // OK: levels 已预分配
glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MIN_FILTER, GL_LINEAR_MIPMAP_LINEAR);

// ✅ ASTC 上传
glCompressedTexImage2D(GL_TEXTURE_2D, 0, GL_COMPRESSED_RGBA_ASTC_6x6_KHR,
                       w, h, 0, dataSize, astcData);
```

**ASTC Block 选择表：**

| Block | bpp | 适用场景 |
|:------|:----|:---------|
| 4×4 | 8.00 | UI、主角 albedo（最高质量） |
| 6×6 | 3.56 | 通用 albedo / 平衡 |
| 8×8 | 2.00 | 大面积 diffuse / 低频细节 |
| 12×12 | 0.89 | 天空盒 / 背景（最低成本） |

## 常见陷阱

| 陷阱 | 后果 | 修正 |
|:-----|:-----|:-----|
| `glTexStorage2D` 的 levels < 完整 mip chain | `glGenerateMipmap` 触发 `GL_INVALID_OPERATION` | `levels = 1 + floor(log2(max(w,h)))` |
| `glTexImage2D` 传 `GL_RGBA8` 作 internalformat (GLES 2.0 兼容模式) | INVALID_ENUM | 用 `GL_RGBA` 或改用 `glTexStorage2D` |
| 未检查 ASTC 扩展直接上传 | INVALID_ENUM / 黑屏 | 运行时查询，fallback 到 ETC2 |
| 法线贴图用 ETC2 | 通道耦合导致质量差 | ASTC uncorrelated 模式或 RG 双通道 |
| 无 mipmap 的 minify 采样 | 闪烁走样 + 带宽浪费 | 生成 mipmap + `GL_LINEAR_MIPMAP_LINEAR` |
| 用 `glTexImage2D` 创建 shader image 纹理 | 未定义行为 | 必须 `glTexStorage*` 不可变 |

## 关联卡片

- [01-api-version-constraints](01-api-version-constraints.md) — 扩展检查流程
- [03-buffer-objects](03-buffer-objects.md) — PBO 异步纹理上传
- [08-tbdr-bandwidth](08-tbdr-bandwidth.md) — 纹理带宽是 TBDR 主要开销
