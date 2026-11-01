# Auditable local fault reduction

`python3 benchmarks/reducer/reduce.py --compiler /path/glslangValidator --output /tmp/reduction` runs ten **authored missing-resource-identifier faults**, not ten vendor-driver bugs. Every case has an exact diagnostic substring, target shader stage, source/fixed files and SHA binding. Positive patches compile independently. Each final failure is reproduced three times.

The reducer deletes line chunks while preserving original `#version`, precision, compute local layout and main envelope. “one_minimal” means no single remaining line can be removed **within that structural domain** while preserving the diagnostic. It does not mean global semantic minimum. Attempt exhaustion, timeout, process crash and I/O error cannot establish minimality. Initial unknown is INCONCLUSIVE; a valid nonmatching compile is NOT_REPRODUCED. Raw trials and compiler hash are retained. Fixture sources must be shader basenames and cannot escape through symlinks. No shell is invoked.

This intentionally small reducer can later use an external semantics-aware reducer behind the same predicate contract. It is not a substitute for reproducing a GPU crash on the original driver. The actual `examples/repro/state_fixture.cpp` captures GL identity, FBO bindings/status, viewport and RGBA readback for a missing-attachment fault and its patch on software GLES.

## Capture/replay guide

1. Record DeviceLab identity, extension set, API/version, resource descriptors and exact shader/input hashes. Exclude credentials, device serials and protected-content pixels.
2. Record a stable failure predicate before minimizing: compiler diagnostic, GL error/FBO status, pixel mask or bounded device crash. Do not change predicate to obtain a smaller input.
3. Reproduce on the original backend. An unavailable target is BLOCKED, not a software pass.
4. Save every attempted deletion, exact tool command/version/hash and output. Crashes/timeouts are a distinct outcome unless the explicitly reviewed original bug predicate is that exact crash.
5. Patch the minimized case, compile/link, execute regression and replay untouched controls. For a performance bug, separately collect same-device A/B with stable workload/thermal conditions.
6. Use [RenderDoc's documented GLES capture/replay support](https://renderdoc.org/docs/) only on supported, authorized targets. A captured resource stream is not portable proof across driver versions. Never capture/export protected resources.

Current evidence proves local compiler reduction and software FBO state correction only. Driver capture/replay and Agent-generated patches remain unrun.
