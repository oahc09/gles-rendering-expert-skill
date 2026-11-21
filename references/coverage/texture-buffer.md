# EXT texture-buffer finite probe

[Fixed official spec](https://github.com/KhronosGroup/OpenGL-Registry/blob/1cdd228e34966dd6b95bd203e9f84faba0f371a1/extensions/EXT/EXT_texture_buffer.txt), revision14 (2014-07-14), inspected2026-11-15. Original summary/code only; copyrighted source text not vendored.

EXT requires GLES3.1/GLSL310. Exact EXT entrypoints, advertised extension and queried limits are required for this probe; OES/core aliases do not substitute. Buffer texels use integer coordinates, without filtering/mips. The range uses byte offset/size and queried alignment. Out-of-range or detached shader fetches are undefined and **never executed**. CPU BufferSubData storage updates are expected to become visible; this test does not establish shader-write synchronization.

Actual four-texel RGBA8 range is placed after a magenta prefix. Shader textureSize checks catch incorrect range selection. A storage update turns red into cyan, and whole-store fetch uses a nonzero base index. All are checked against exact CPU bytes. Independent GLES3 2D texelFetch fallback renders the original colors. Wrong target/unsized format, negative offset/zero size/overrun/misalignment are API negatives.

## Actual results and unresolved discrepancy

Mesa passes all12 records. ANGLE matches every pixel and other boundary, but `glTexBufferRangeEXT(buffer=0, offset=-1,size=0)` returns INVALID_VALUE rather than ignoring offset/size as the pinned spec requires. This is preserved as **FAIL**, not waived by a working positive path. Whole-store `glTexBufferEXT(buffer=0)` succeeds on both; no detached fetch follows either operation.

The acceptance policy falls back to 2D for a non-passing report, even when EXT is advertised. The CLI remains nonzero for ANGLE's discrepancy. CI runs the passing Mesa route and verifies both archived reports; this is not ANGLE feature closure. No exact driver root cause, native fix, performance gain or physical-device acceptance is claimed. R8/integer/float formats, shader image writes, huge stores and other aliases remain untested.
