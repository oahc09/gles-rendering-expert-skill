# Actual compressed asset streaming chain (bounded synchronous)

The chain is original CPU pixels → official UASTC encode → libktx transcode →
strict KTX2 container parse → independent CPU decode/quality gate → content-keyed
CPU payload cache → budgeted LRU GL texture upload/eviction → sampling/readback.
It is not a juxtaposition of independent transcode and streaming reports.

KTX-Software 4.4.2 is an external Apache-2.0 dependency. The runner requires the
[official Linux x86_64 archive](https://github.com/KhronosGroup/KTX-Software/releases/download/v4.4.2/KTX-Software-4.4.2-Linux-x86_64.tar.bz2)
and extracted installation, verifies the pinned SHA256
`a8781bad05f9624edbf910b7f258cd0a4ba7d3e63b49ecc0a0ab440bf6a0a245`, then compares
extracted regular files and symlink targets with that archive before invoking
its tools. No external binaries are vendored. A system C++ compiler builds the
existing `examples/texture_pipeline/transcode.cpp` helper.

```sh
python benchmarks/compressed_streaming/run.py --config DRIVER.json --output REPORT.json --ktx-root KTX_ROOT --ktx-archive OFFICIAL_ARCHIVE
python -m unittest discover -s benchmarks/compressed_streaming -v
```

Three assets: smooth ETC2, smooth ASTC (ETC2 fallback without ASTC extension), and
steep ETC2. CPU errors against original are14/8/119 in both tested drivers.
Fixed limit32 rejects the third compressed result; fallback uploads original
lossless RGBA8, **not lossy UASTC decoded to RGBA32**. Successful compressed quality
still is INSUFFICIENT_EVIDENCE for performance; the failed route remains
REJECTED_BY_QUALITY even though its fallback works.

Both software drivers execute24 frames/27 readbacks,17 GL reloads,7 GL cache hits
and20 CPU payload-cache hits. Actual compressed uploads use ETC2 or ASTC enums;
fallback uses RGBA8. Capacity80 and upload/frame64 are **logical payload bytes**.
Every sampled output matches independent decoded pixels within1 and original
within32; fallback matches original exactly. Invalid working-set/unknown requests
are rejected before GL state changes. CPU cache is bounded by this fixed three
asset catalog, keyed by source bytes/codec/tool lock; it is not a general persistent
cache with arbitrary-input eviction or mutable asset invalidation.

CPU times are deliberately separate: encode subprocess (startup included),
libktx input load, libktx TranscodeBasis, Python container validation and CPU
ETC2 decode or ASTC decoded-file read. ASTC decode itself occurs inside the helper
outside its transcode interval; that decode is **not separately timed**. These
are CPU timings, not GPU transfer stalls or a throughput/benefit comparison.
The ETC2 oracle uses the previously documented pinned internal libktx ABI.

Preparation is synchronous and prewarms the CPU payload cache before streaming.
No async worker/fence claims, compressed mip-chain progression, context-loss
recovery, arbitrary texture sizes or physical residency are covered. Unexpected
GL failures abort rather than claiming transactional recovery. Reports exclude
machine metadata, local paths and executable fingerprints. Full hardware and
provider gates remain unchanged.
