# Bounded ANGLE pixel local storage and portable fallback

## Source and precise ABI

Read official [ANGLE vendor specification at bb55ea10fcef3759e4db7ef8a473a9ceac2c6aa6](https://raw.githubusercontent.com/google/angle/bb55ea10fcef3759e4db7ef8a473a9ceac2c6aa6/extensions/ANGLE_shader_pixel_local_storage.txt), matching the tested runtime's reported commit prefix. This draft labels itself **Incomplete**. It is an ANGLE-specific extension, not generic GLES core or the differently named EXT/ARM PLS specifications. Source SHA256 and review scope are in `benchmarks/coverage/pixel-local-storage/source.json`; no full source prose is distributed.

The first attempted Khronos Registry extension URL was unavailable. The latest official ANGLE draft was retrieved but adds a `usage` argument not present in the tested runtime. Rather than silently mix ABIs, the implementation uses the pinned runtime revision's **four-argument** `glFramebufferTexturePixelLocalStorageANGLE(plane,texture,level,layer)`. Begin/End take `n` and GLenum arrays. The shader requires `GL_ANGLE_shader_pixel_local_storage` with `layout(binding=0,rgba8) uniform highp pixelLocalANGLE`. All exact pointers are required after advertisement; one plane must fit queried MAX_PIXEL_LOCAL_STORAGE_PLANES_ANGLE. Successful real Begin/draw/End and readbacks, not advertisement alone, establish this bounded result.

## Actual finite experiment

A4×4 immutable RGBA8 texture backs plane0 on a separate FBO with no ordinary color attachment and drawbuffer NONE. The backing texture is never sampled during PLS, nor simultaneously attached to an enabled PLS drawbuffer. Dither, blending, depth/stencil/scissor/cull are disabled. The FBO used for readback is distinct and used only after End.

1. Begin ZERO, full-screen triangle adds byte-equivalent(64,32,16,64).
2. Actual `glPixelLocalStorageBarrierANGLE`, then a second triangle adds(32,64,16,64).
3. End STORE; separate FBO readback matches independent CPU oracle(96,96,32,128) at all16 pixels.
4. Begin LOAD on the same plane, third triangle adds(16,16,16,16), End STORE; all16 pixels match(112,112,48,144).
5. Deterministic wrong-load negative begins ZERO instead of LOAD and adds only the last delta. Actual output is(16,16,16,16), correctly rejected against the LOAD oracle. We do **not** read DONT_CARE contents or omit barriers as a deterministic negative.
6. Nested Begin while active and End while inactive are issued as defined invalid operations. Both return GL_INVALID_OPERATION(0x0502); subsequent legal result remains correct.

ANGLE executed4 PLS draws (including wrong-load negative),1 explicit barrier,3 PLS texture readbacks. A separate3-draw GLES3 ping-pong fallback executes on **both** ANGLE and Mesa: each draw samples one immutable RGBA8 texture and writes the other, never feedback sampling the current attachment. Its stage2/stage3 readbacks independently match the same CPU oracle. No fallback calls PLS entrypoints on Mesa, which does not advertise this extension.

Actual reports: ANGLE `HOST_PASS`, Mesa `FALLBACK_PASS` with `pls=UNSUPPORTED`; both CLI exit0. Mesa fallback success must not be counted as Mesa PLS support. Exact bytes/errors, scope events and source/shader hashes are archived.

## Synchronization and claims boundary

The tested ANGLE advertises `_coherent`, so primitive ordering already provides its vendor guarantee; this run additionally executes the explicit barrier and follows the noncoherent safe pattern. It **does not empirically validate a noncoherent-only implementation** or prove that omitting the barrier fails. Two triangles each cover a pixel once per pass; no within-pass intentional race occurs.

No hardware tile storage, bandwidth saving or performance improvement is inferred. ANGLE may lower this extension through other rendering mechanisms. No native tile or DRAM counter was measured. Physical devices, memoryless/CLEAR/DONT_CARE variants, interrupt/restore, multiple planes, MSAA, other formats, cross-context use and real lifecycle loss remain NOT_RUN. Protected content, SDK installation and context-reset injection are not involved.

```sh
python3 benchmarks/coverage/pixel-local-storage/run.py --config DRIVER_CONFIG.json --output REPORT.json
python3 -m unittest discover -s benchmarks/coverage/pixel-local-storage -p 'test_*.py' -v
```

Each driver runs in a separate process with the existing Host. Configs remain private; public reports exclude OS/library/executable fingerprints and absolute paths. `HOST_PASS` and `FALLBACK_PASS` are different outcomes. Exit1 means failure, including an advertised capability with missing entrypoint, rejected shader, failed GL operation or wrong pixels. Six tests cover CPU oracle, rejected wrong pixels/length, real error controls, Mesa unsupported handling, both real fallbacks, evidence hashes and sanitization; not substitutes for driver execution.
