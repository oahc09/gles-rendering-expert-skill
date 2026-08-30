# 纹理流送与 LOD 控制

> **Category**: Textures / Memory | **GLES Version**: 3.0+ | **Source**: `references/rules/texture-streaming-lod.md`

## 核心规则

1. **一次性分配完整 mip 链的不可变存储**：`glTexStorage2D(target, levels, ifmt, w, h)`，`levels = 1 + floor(log2(max(w,h)))`；之后逐 mip 用 `glTexSubImage2D` 填充，禁止每级重新 `glTexImage2D`。
2. **用 resident 区间门控可见性**：上传完 mip N 后再 `glTexParameteri(GL_TEXTURE_MAX_LEVEL, n)` 放行；回收时抬高 `GL_TEXTURE_BASE_LEVEL`。改 base/max 是廉价状态，不是重传。
3. **上传必须走 PBO**：绑定 `GL_PIXEL_UNPACK_BUFFER` + 字节偏移（`nullptr` 起点），避免 client-pointer 卡住打包线程；见 `pbo_streaming_upload.cpp`。
4. **共享上下文工作线程上传 + fence 同步**：`glFenceSync`+`glFlush`（生产），消费端 `glWaitSync` 后 `glDeleteSync`；渲染线程永不等待。
5. **按带宽预算而非张数**：移动纹理流送约 200–400 MB/s；重流送内容优先 ASTC 6×6/8×8。
6. **LOD 控制决定驻留需求**：`glSamplerParameterf(GL_TEXTURE_LOD_BIAS)` 或 shader 内 `textureLod`/`textureQueryLod`；LOD 变化留 ±1 级滞回防抖动。
7. **帧内禁止 `glGenerateMipmap`**：全链读写（≈1.33× 带宽）且多为隐式同步；离线烘 KTX2，仅在加载期对未采样纹理生成。
8. **各向异性是扩展**：`GL_EXT_texture_filter_anisotropic`，查 `GL_MAX_TEXTURE_MAX_ANISOTROPY_EXT` 并钳制（移动端 4× 足够）。
9. **GLES 无 sparse texture**：虚拟纹理用 `GL_TEXTURE_2D_ARRAY` tile 阵列 + `vec3(uv, tileLayer)` + LUT 模拟，按 128² tile 粒度流送。
10. **TBDR**：上传流量走 DRAM 不碰 tile；tile 成本来自后续 fetch。大块上传排在加载期/帧间，勿在 render pass 内。

## 代码模式

```cpp
// 工作线程：上传 mip level，再让渲染线程放行该级
glBindBuffer(GL_PIXEL_UNPACK_BUFFER, pbo[slot]);
void* m = glMapBufferRange(GL_PIXEL_UNPACK_BUFFER, 0, size,
    GL_MAP_WRITE_BIT | GL_MAP_INVALIDATE_BUFFER_BIT);
memcpy(m, cpuPixels, size);
glUnmapBuffer(GL_PIXEL_UNPACK_BUFFER);
glBindTexture(GL_TEXTURE_2D, tex);
glPixelStorei(GL_UNPACK_ALIGNMENT, 1);
glTexSubImage2D(GL_TEXTURE_2D, level, 0, 0, w>>level, h>>level,
                GL_RGBA, GL_UNSIGNED_BYTE, nullptr);
GLsync f = glFenceSync(GL_SYNC_GPU_COMMANDS_COMPLETE, 0); glFlush();
// 渲染线程下一帧： glWaitSync(f,...); glDeleteSync(f);
glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MAX_LEVEL, level);
```

## 常见陷阱

| 陷阱 | 后果 | 修正 |
|:-----|:-----|:-----|
| 每个流送 mip 调 `glTexImage2D` | 存储重分配、旧 mip 丢失、驱动停顿 | 一次 `glTexStorage2D` + 逐级 `glTexSubImage2D` |
| 顶级 mip 未就绪就采样 | 纹理不完整、黑块 | 上传完成前保持 `MAX_LEVEL` 在驻留下界 |
| 帧内 `glGenerateMipmap` | 周期性帧尖峰 | 离线烘 mip；仅加载期生成 |
| 无 LOD 滞回 | 相机抖动时反复上传 | ±1 级滞回 |
| 工作线程上传后不加 fence | 撕裂/不确定 mip | `glFenceSync`/`glWaitSync` |

## 关联卡片

- [02-texture-formats-compression](02-texture-formats-compression.md) — ASTC/ETC2/KTX2
- [03-buffer-objects](03-buffer-objects.md) — PBO
- [11-synchronization](11-synchronization.md) — fence 跨线程
- [08-tbdr-bandwidth](08-tbdr-bandwidth.md) — 带宽预算
