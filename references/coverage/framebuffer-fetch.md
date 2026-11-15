# Framebuffer fetch: ordered probe and safe fallback

Source: [official combined EXT specification](https://github.com/KhronosGroup/OpenGL-Registry/blob/1cdd228e34966dd6b95bd203e9f84faba0f371a1/extensions/EXT/EXT_shader_framebuffer_fetch.txt), revision8, September6 2018, inspected2026-11-15. Copyright/IP notices remain at source; no full specification vendored.

Original implementation summary: coherent fetch follows prior overlapping API primitive order. Noncoherent fetch needs its shader layout plus an explicit fetch barrier before consuming prior writes, including clears. Missing barriers produce undefined observations, not a guaranteed GL error: the policy rejects such requests **before dispatch**. Enabling only the noncoherent extension while omitting its required output qualifier is a compile-error control. This test does not cover multisample, sRGB, discard/helper invocation or PLS semantics.

Actual two-pass single-sample RGBA8 test cyclically permutes RGB, checks all16 pixels against an independent integer oracle and compares a separate-source/destination ping-pong control. Normal blending is disabled. Noncoherent draws have two explicit barriers. No feedback-loop texture sampling is used.

## Results and limits

- ANGLE: coherent fetch, barrier-ordered noncoherent fetch, separate-attachment ping-pong and missing-qualifier compile rejection passed.
- Mesa: **both fetch draw routes crash with signal11 despite advertisement**. Process isolation preserves FAIL. Ping-pong and the compile negative pass. Do not select fetch solely from its extension string. No driver fix or universal Mesa failure is claimed.
- Policy requires successful ordered runtime evidence; otherwise ping-pong is selected. Missing-ordering requests are rejected, not run to manufacture a driver error.

`benchmarks/coverage/framebuffer-fetch/suite.py` exits nonzero on the Mesa failure. Archived-contract tests verify that this failure remains visible; they do not turn it into feature acceptance. Raw local diagnostic logs/host identities are not published. No physical bandwidth or speedup claim.
