# Bounded multi-frame streaming infrastructure

`planner.py` is a reusable logical-byte LRU planner. `plan(requests)` is nonmutating:
it deduplicates frame requests, rejects unknown assets, upload-budget overflow and
an oversized pinned working set before eviction. It evicts only cold resources
not requested in the frame. `commit(plan)` rejects stale/tampered plans. No logical
budget means physical GPU residency, allocation size or driver memory usage.

`run.py` executes 40 frames of hot reuse, cold eviction and reload through actual
GLES textures. Five authored 4×4 RGBA8 patterns compete for a three-texture logical
capacity and two-texture upload/frame limit. Eviction calls glDeleteTextures;
reload creates and uploads again. Every requested asset is drawn/read back and
compared byte-for-byte to its authored CPU oracle. Frame reports preserve budgets,
evictions, uploads and pixels. Two rejected requests leave planner and GL object
ledger unchanged. No GL operation is attempted for rejected plans.

```sh
python benchmarks/texture_streaming/run.py --config DRIVER.json --output report.json
python -m unittest discover -s benchmarks/texture_streaming -v
```

Run each actual driver in its own CLI subprocess. Unit tests require no local
configuration and do not skip. Mesa and ANGLE saved reports both HOST_PASS.
Reports intentionally omit host metadata, local paths and executable hashes.

Limits: synchronous whole RGBA8 assets, fixed CPU catalog, no mip-tier refinement,
compressed streaming, async worker/fence scheduler, background prefetch, production
integration or device-loss recovery. A GL/upload/quality failure aborts the run;
this is not an atomic GPU rollback guarantee after partial resource eviction.
Logical bookkeeping and actual object lifecycle are covered; physical residency,
GPU stall/frame time, bandwidth and performance acceptance remain unmeasured.
CPU transcode phase decomposition is not implemented in this runner; the separate
KTX experiment still measures total subprocess load/transcode/decode/I/O time.
