# W4 resource pressure / ownership regression

```sh
python benchmarks/resource_pressure/run.py --output /tmp/resource-pressure.json
# Optional local SDK and Android cross-compile (NOT device execution):
python benchmarks/resource_pressure/run.py --sdk "$GLES_SDK_ROOT" \
  --ndk "$ANDROID_NDK_ROOT" --output /tmp/resource-pressure.json
GLES_SDK_ROOT=/path/to/host/sdk/usr python -m unittest discover \
  -s benchmarks/resource_pressure -p 'test_*.py' -v
```

`--sdk` uses the existing Debian x86-64 extracted SDK layout; omit it with normal
system headers/libraries. Runtime defaults to Mesa surfaceless software rendering.
Override `EGL_PLATFORM` and `LIBGL_ALWAYS_SOFTWARE` deliberately for another
implementation, keeping its actual capability snapshot. Missing compiler, missing
GL context, timeout, invalid report, GL error or failed assertion exits nonzero.

## Actual scope

- Reuses `examples/validation/egl_smoke.cpp` EGL owner, capability and pixel checks;
  no second lifecycle framework and no modifications to old shared code.
- 100 scene changes (configurable 100–10000). Tiny 16×16 RGBA8 textures enforce an
  **8 KiB engine estimate**; pinned essential tier plus LRU evictable tier. This
  tests policy/ownership churn, NOT physical GPU memory exhaustion.
- Eight PBO upload bursts and four fenced PBO readbacks per scene. One readback and
  three upload results canceled per scene; cancellation suppresses consumption,
  not already submitted GPU writes. PBO storage is not recycled before completion.
- Real zero-timeout fence results counted, bounded waits, actual mapped readback
  bytes checked. Software GL may finish immediately; a reported pending count of
  zero is not missing data and is **not** claimed as a delayed GPU test.
- Separately named `synthetic-completion-policy` injects Pending/Failed states into
  the same policy used by actual transfers. It verifies cancellation retention,
  fail-closed behavior and thread/generation guards; it is not GPU timing evidence.
- Ten pbuffer surface recreations and four controlled context replacements per
  100 scenes. Every new generation rebuilds a texture from retained CPU pixels and
  reads it back. These are deliberate teardown/rebuilds, not EGL_CONTEXT_LOST,
  Android background/foreground, or real low-memory callbacks.
- Four resource-kind counters track created/deleted/peak handles. Deleted texture,
  buffer and FBO names are checked via GL queries. Every scene ends with zero
  owned handles; this does **not** prove zero driver allocations or exact VRAM.

`result.json` records raw NDJSON, compiler logs, current source hashes, binary
hashes, actual renderer and Android target compile result. The NDK binary is not
executed. The regression suite runs current GL code again; its corrupted-report
negative cases are explicitly validator tests, not additional GPU workloads.

Real Android loss, AHB/external import, native fence handoff, device thermal/memory
pressure and GPU-driver leak profiling remain `NOT_RUN_DEVICE`/unmeasured. Reuse
v1.0.4 Android integration rather than replacing it with a host mock.
