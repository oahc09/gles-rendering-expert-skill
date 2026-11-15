# v1.0.9 W6 texture mechanisms (PARTIAL)

```sh
python3 benchmarks/texture_access/mechanisms.py --config DRIVER_JSON --output REPORT_JSON
python3 -m unittest discover -s benchmarks/texture_access -v
```

The new mechanism runner performs **14 actual GLES draws/readbacks**, not coordinate
aliases: ETC2 block, optional ASTC constant block, legal anisotropy parameters, direct upload baseline, generated mip, explicit mip, texture-array layer
selection, PBO upload, R8 swizzle, RGB565 format, linear filtering, guarded atlas,
atlas bleed negative control and resolution-loss negative control. Each validates
64 RGBA8 pixel bytes against an independent finite CPU oracle. Mip implementations
and direct/PBO paths are additionally paired for pixel identity. Texture storage,
filtering, upload and shader paths are genuinely exercised. Reports retain source
hashes and pixels, but no host/OS/library/executable identifiers or paths.

Both `evidence/mechanisms-mesa.json` and `evidence/mechanisms-angle.json` report
HOST_PASS: 12 expected quality passes and two expected quality failures each.
CPU upload submission milliseconds are observed wall-clock API-call durations,
including driver work and mip generation where applicable, **not** GPU timing,
upload stalls or an optimization speedup. `logical_texture_bytes` is payload
accounting, not resident memory. CPU transcode, physical residency, GPU stalls and
DRAM remain null. No device-independent performance conclusion follows.

Compression/aniso routing inspects the active context's extension availability:
ASTC falls back to RGBA8 without its extension; anisotropy to isotropic sampling.
ETC2 executes an all-zero individual-mode block with independent RGB=(2,2,2) oracle.
ASTC executes a LDR void-extent opaque-red block only when its extension is present.
Anisotropy uses a complete mip chain, finite screen-space gradients, and a legal
parameter capped at the queried maximum; the constant-red image is a correctness
control, not a filtering quality benchmark. Both current software contexts expose
these extensions; absence retains the documented fallback, never forces support.
Historical first-batch boundary (KTX2 transcoding and varied compressed blocks
were subsequently implemented in the sections below): ASTC hardware quality, anisotropy
quality under oblique views, and physical-GPU timing/power remain NOT_RUN or hardware-blocked. Bounded synchronous
streaming/eviction is now covered separately in `../texture_streaming/`; full
production streaming and physical residency remain unverified.
Use existing `benchmarks/texture_pipeline/` for the broader asset selection path.

`run.py` retains the earlier eight simple coordinate-regression controls for
backward compatibility; they are not counted as eight new texture mechanisms.

During development constant texture coordinates in the anisotropy control produced
different software-driver results. The accepted control now supplies finite
screen-space UV gradients and complete mip levels. This does not establish a vendor
bug or general anisotropy equivalence. Compression ratio never implies measured
resident-memory, DRAM-bandwidth, GPU-time or power savings.

## Normative oracle derivation (checked 2026-11-15)

The CPU constants are derived from Khronos, not fitted to driver output:

- **ETC2:** [Khronos Data Format 1.4, §22, Tables 141–143](https://registry.khronos.org/DataFormat/specs/1.4/dataformat.1.4.html). Eight zero bytes select individual mode (D=0), zero RGB base colors, modifier table 0 and pixel selector 00. That selector chooses +2; clamping gives RGB=(2,2,2). This RGB-only payload is sampled with opaque alpha.
- **ASTC:** [same specification, §23.22, Table 185](https://registry.khronos.org/DataFormat/specs/1.4/dataformat.1.4.html). The 2D block starts `FC FD FF FF FF FF FF FF`: void-extent mode, D=0 (LDR), reserved bits 10–11 set, and all-one extents, meaning constant color. The remaining little-endian UNORM16 RGBA words are `FFFF 0000 0000 FFFF`, hence opaque red. This proves only the selected constant block, not arbitrary ASTC decoding.

[EXT_texture_filter_anisotropic](https://registry.khronos.org/OpenGL/extensions/EXT/EXT_texture_filter_anisotropic.txt) permits implementation-dependent filtering formulations. The original zero-gradient control did not constrain a meaningful filtering footprint; its differing output remains a recorded limitation, not erased evidence. The finite-gradient replacement establishes only legal-parameter/constant-color correctness. It does **not** satisfy the original plan's oblique-view anisotropy quality, bandwidth or performance targets, nor establish that the original difference was permitted or forbidden by the specification.

## Actual KTX2/UASTC multicolor experiment

`ktx2_experiment.py --config DRIVER_JSON --ktx-root OFFICIAL_KTX_ROOT --output REPORT_JSON [--pattern smooth|steep]`

This builds the existing `examples/texture_pipeline/transcode.cpp` against official
[KTX-Software 4.4.2](https://github.com/KhronosGroup/KTX-Software/releases/tag/v4.4.2),
encodes original 4×4 RGB pixels to UASTC with `toktx`, actually calls libktx for
RGBA32/ETC2_RGBA/ASTC_4x4_RGBA conversion, validates each resulting container, and
uploads its payload into real GLES. Tools/libraries are external Apache-2.0 dependencies,
not vendored. The official archive matched the existing pinned receipt; no local
executable/library identities are published in these experiment reports.

`ktx2_container.py` implements a bounded structural subset of the
[Khronos KTX2 specification](https://registry.khronos.org/KTX/specs/2.0/ktxspec.v2.html):
size budget, identifier, one-level 2D topology, whitelisted UNORM formats,
no supercompression, section bounds/alignment/nonoverlap, payload size, basic DFD
model/transfer/block geometry and KVD framing. This is **not** a full KTX conformance
validator or arbitrary untrusted-file security guarantee; unsupported topologies,
sRGB, supercompressed containers and metadata semantics require other paths.

Both drivers executed multicolor ETC2/ASTC blocks (not just constant blocks).
The independent golden is the original authored RGB formula, not another GPU's
output. With fixed maximum per-channel error budget 32, the smooth gradient
(x×8,y×8,(x+y)×4) passes: RGBA/ASTC maximum error 8, ETC2 14 on both drivers.
The initially attempted steep gradient (x×64,y×64,(x+y)×32) failed this same budget:
RGBA/ASTC 34, ETC2 119. That failed positive experiment is retained explicitly as
an expected quality-rejection regression fixture, not recast as successful lossy
quality. The separate `ktx2-steep-*.json` HOST_PASS means rejection logic worked.
These tiny-image budgets are not universal perceptual-quality thresholds.

`evidence/ktx2-{mesa,angle}.json` and `evidence/ktx2-steep-{mesa,angle}.json`
contain 12 actual conversion/upload/readbacks total and five malformed-container
rejections per run. Fifteen texture unit-test methods pass, including 19 header
mutations and seven truncations. CPU subprocess elapsed includes compilation-excluded
process startup, transcode, decoder/output I/O; it is not isolated transcoder cost.
GPU performance, physical compression quality, residency, bandwidth, streaming
and broad KTX2 coverage remain unverified. No change was made to the earlier frozen
mechanism implementation or its evidence.

### Codec versus orientation check

The rerun also preserves the existing libktx experiment's **independent CPU-decoded
RGBA pixels** for the RGBA32 and ASTC branches. GPU/CPU maximum discrepancy is zero
on Mesa; ANGLE is zero for RGBA32 and one for ASTC. CPU versus original golden is
8 (smooth) / 34 (steep), while CPU versus vertically flipped golden is 24 / 192.
The linear UNORM header/DFD is checked before upload. Thus the steep RGBA/ASTC
failure is already present in the lossy UASTC→CPU decode, not introduced by a
vertical readback flip or an sRGB sampling path. RGBA32 here is a *decoded UASTC*
branch, not a lossless upload of the original RGB image.

The initial ETC2 result lacked an independent CPU decoder. The follow-up audit
below closes that specific gap for these blocks; it does not establish arbitrary
ETC2 decoder equivalence.


## Fourth-batch audit: CPU ETC2 oracle and fail-closed acceptance

The official [KTX 4.4.2 public header](https://github.com/KhronosGroup/KTX-Software/blob/v4.4.2/include/ktx.h)
provides ASTC decoding, but not an equivalent public ETC2 decode API. The pinned
release also exports the internal `_ktxUnpackETC` implementation whose signature,
RGBA8 output path and allocation ownership were checked against
[official `lib/etcunpack.cxx`](https://github.com/KhronosGroup/KTX-Software/blob/v4.4.2/lib/etcunpack.cxx).
`etc2_cpu_oracle.py` uses that **version-specific internal ABI** only for a 16-byte,
4×4 ETC2_RGBA block generated by this experiment. Missing symbols fail explicitly.
It is not a supported public libktx integration API, general untrusted decoder, or
cross-platform ABI guarantee. The Apache-2.0 implementation remains external.

Every run first checks an independent normative constant block: alpha base 255,
zero alpha multiplier, zero RGB individual-mode block yields (2,2,2,255).
The multicolor blocks then produce CPU/GPU maximum discrepancy **0 on both Mesa
and ANGLE**, for both smooth and steep gradients. CPU-versus-original errors
remain **14 / 119**; CPU-versus-vertical-flipped original errors are **24 / 182**.
Thus those errors already exist before GLES sampling. This confirms the finite
transcode/decode path, not all ETC2 modes or general perceptual quality.

The bounded KTX loader now also checks exact supported DFD sample layouts,
primaries, duplicate/empty/invalid-UTF8 KVD keys and semantic metadata. It rejects
unsupported orientation, swizzle and unknown reserved KTX semantics rather than
silently rendering a mismatched image. Strict-subset rejection may reject valid
KTX files outside its declared profile. Tests include every truncation of a
200-byte valid fixture, 32/64-bit boundary mutations, excessive dimensions,
unsupported mip/supercompression/format, DFD corruption and KVD manipulation.
These are hostile-input regression controls, not full parser-security certification.

`quality_gate.py` independently recomputes image error from saved pixels and
requires nonempty unique RGBA/ETC2 branches, successful compile/link/GL execution,
and the unchanged quality budget. It rejects forged labels and missing pixels.
A correctly rejected steep negative control can yield harness HOST_PASS, but its
optimization status is always **REJECTED_BY_QUALITY**, never a successful
optimization. Smooth software correctness yields **INSUFFICIENT_EVIDENCE** for
performance. Automatic acceptance and verified improvement are always false.
Integration tests exercise these distinctions against the actual saved reports.
