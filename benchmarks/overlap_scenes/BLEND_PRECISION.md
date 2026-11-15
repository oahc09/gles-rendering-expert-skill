# RGBA8 blend discrepancy: diagnosis and explicit precision alternatives

`blend_precision.py --config DRIVER_JSON --output REPORT_JSON` runs nine views
(8/24/48 authored Gaussian billboards × three cameras). Per driver: 45 readbacks,
including original RGBA8, RGBA16F baseline/foreground-removal negative, and RGBA32F
baseline/negative. Floating-point attachments are actually rendered and blitted
to RGBA8. The original `tiered-*` failed evidence is unchanged.

## Results and original-target preservation

The original gate stays max color error 4 codes, silhouette disagreement <=2
pixels, centroid error <=0.1 pixels. Three distinct CPU references are retained:
per-layer RGBA8 quantization, per-layer half accumulation, and ideal linear
accumulation with final RGBA8 quantization. Changing attachment format changes
the mathematical contract; it does not silently replace the original target.

* Mesa RGBA16F: maximum error 1 against independent half reference; 8-object
  camera-zero silhouette disagreement is still 4 pixels at the alpha threshold
  (12 vs 13), so overall status **FAIL**. Other eight views pass.
* ANGLE RGBA16F: all nine views exactly match the half reference.
* RGBA32F: both drivers match independent ideal linear reference exactly in all
  nine views; all nine negatives are rejected. `explicit_float32_correction=PASS`
  applies only to this explicitly chosen linear contract.
* Both floating formats differ from the **original per-layer RGBA8 golden by up
  to 6 codes**, exceeding the old color gate. Thus neither is a lossless repair
  of the old UNORM contract. Reports retain these errors and mask/centroid metrics.

Each evidence JSON has a deterministic ZIP with all actual/golden/negative RGBA
images; extract alongside it. `--require-contract-only` is a narrowly named CI
mode: it requires advertised and actually passing float32 controls, while still
preserving the half-float silhouette FAIL in JSON. Capability absence is
`NOT_SUPPORTED`, not acceptance. Advertised-but-broken compile/FBO/GL operations
raise hard errors, not an unsupported success. Default CLI remains nonzero on
any required visual failure.

## Quantitative diagnosis, not a proved installed-driver root cause

For Mesa camera zero, ideal per-layer UNORM error is 2/6/11 codes for tiers
8/24/48. A diagnostic model quantizing source color/alpha before blending gives
2/5/8; separately rounding both blend products gives 1/3/6 and reduces differing
channels to 49/50/50 from 474/1016/1354. These are hypotheses, **not substituted
acceptance goldens**. The residual mismatch prevents claiming an exact model.
The float32 result isolates the larger accumulation discrepancy to a precision-
sensitive route but does not identify the installed driver's exact arithmetic.

GLES 3.2 permits internal fixed-point blending with minimum destination precision
(§15.1.5), and normalized conversion permits adjacent integers, nearest preferred
(§2.3.5.2). See the [official GLES 3.2 specification](https://registry.khronos.org/OpenGL/specs/es/3.2/es_spec_3.2.pdf).
An independent source review found current Mesa `generate_blend` converts through
`lp_build_conv_auto` before `lp_build_blend_aos`, and normalized multiply helpers
use integer rounding/shifting. This supports investigating source quantization,
but current upstream code was not matched to the installed binary. No Mesa
conformance bug or definitive root cause is asserted.

Half-float rendering requires an advertised color-buffer float/half-float
capability. Float32 additionally requires `GL_EXT_color_buffer_float` and
`GL_EXT_float_blend`; framebuffer completeness and actual readback/GL errors are
checked. Without support, use original RGBA8 only when its own unchanged quality
gate passes, otherwise reject the tier. No automatic production fallback occurs.
Float attachments cost more storage/bandwidth; no performance or physical-GPU
benefit, million-scale capability, or overall W4 completion is claimed.
