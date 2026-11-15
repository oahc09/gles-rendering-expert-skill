# Bounded KHR robustness / GLES3.2 readback evidence

Primary sources were actually read at fixed Khronos OpenGL Registry revision `1cdd228e34966dd6b95bd203e9f84faba0f371a1`: [KHR_robustness](https://raw.githubusercontent.com/KhronosGroup/OpenGL-Registry/1cdd228e34966dd6b95bd203e9f84faba0f371a1/extensions/KHR/KHR_robustness.txt), and [GLES3.2 specification](https://raw.githubusercontent.com/KhronosGroup/OpenGL-Registry/1cdd228e34966dd6b95bd203e9f84faba0f371a1/specs/es/3.2/es_spec_3.2.pdf), sections7.12 and16.1.2. Retrieved hashes in `benchmarks/coverage/robust-readback/sources.json`; source prose/PDF not vendored. This is AI source review, not independent human signoff.

## Exact contract and safe test design

- Query actual GL major/minor and extension advertisement. Core unsuffixed `glReadnPixels`/`glGetnUniformfv` only at GLES3.2+. Advertised GL_KHR_robustness admits the distinct KHR-suffixed ES entries. Each exact pointer is loaded and required; pointer existence alone never grants capability.
- Both APIs' `bufSize` unit is **bytes**, including floating uniform results, not float count. Undersized destinations require GL_INVALID_OPERATION(0x0502). An error command must not perform the transfer. We test both all untouched output and guard bytes, rather than merely seeing an error.
- Actual4×4 RGBA8 single-sample FBO is cleared to four different column colors using scissor. CPU oracle independently enumerates expected bytes. PACK_BUFFER=0, pack alignment4. Tight read size64 versus63/0.
- A second layout uses row length6, skip row1, skip pixel1: start28, stride24, final row writes through byte115, therefore required span116 bytes, **not128 allocated bytes** and not96 full-row storage. Test116 and115; untouched holes/prefix/trailing payload remain sentinel165.
- Program compiles/links a live vec4 uniform set to(.25,.5,.75,1); independent CPU IEEE float-byte oracle checks16-byte transfer versus15/0. No draw is needed for a uniform query. The four framebuffer clear operations are not presented as draw calls.
- Every destination allocates128 bytes plus16-byte prefix/suffix guard. Even undersized declared cases have enough actual backing memory, avoiding intentionally unsafe host overflows while checking the API guarantee. Actual guards and full payload are archived; ctypes has correct GLsizei integer and void-pointer signatures.

## Actual results / limits

Mesa queried GLES3.2 and KHR advertisement: both core and KHR routes,16 actual robust calls total. ANGLE queried GLES3.1: KHR route only,8 calls. Each route has5 pixel calls and3 uniform calls. Every exact-sized result matched CPU bytes; every undersized call returned0x0502 and left the full payload and both guards unchanged. Both CLI runs exited0; reports `mesa.json`/`angle.json` contain the actual observed bytes and errors, not synthesized verdict fixtures.

No robust-access context flag was requested, no GPU fault/reset was induced, and no context-loss recovery was tested. Bounded readback entrypoints do not establish robust shader indexing or real reset handling. Physical GPU, performance, PBO mapping/overflow, arbitrary formats, ES2 extension paths, GetnUniform integer variants and protected-content readback are NOT_RUN. No claim of overall robustness closure or device certification follows.

## Reproduce

```sh
python3 benchmarks/coverage/robust-readback/run.py --config DRIVER_CONFIG.json --output REPORT.json
python3 -m unittest discover -s benchmarks/coverage/robust-readback -p 'test_*.py' -v
```

Each driver runs in a separate process using the existing differential Host. Configs provide locally provisioned EGL/GLES and optional ANGLE ICD paths; reports intentionally exclude library/executable fingerprints, OS metadata and absolute paths. Exit0=finite HOST_PASS,77=unsupported (not acceptance),1=failure. Tests cover unavailable/core/KHR gates, offsets, injected canary/error rejection, archived real evidence completeness and metadata sanitization. They do not substitute for the actual driver runs.
