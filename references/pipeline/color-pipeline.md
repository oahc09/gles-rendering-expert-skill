# Color/material pipeline correctness

Classification: GLES Core (sRGB texture decode, RGBA8 blend/resolve), capability-
gated extension (RGBA16F color renderability), Recommendation (analytic regression
thresholds). Software numerical reproduction is not physical display validation.

## Reference contract

`benchmarks/pipeline/runtime.py` generates six 32×32 RGB8 P6 references using CPU
arithmetic, independent of the C++/GLSL implementation. Every run validates the
frozen image SHA256, dimensions, exact inventory, per-scene threshold and exact
agreement with the analytic oracle. It never accepts a runtime screenshot as a
new golden. It reuses the existing visual-quality strict P6 decoder and writer.
The explicit `--write-analytic-references` option recreates only analytic files;
reference changes must be reviewed alongside the equations and tests.

| ID | Actual pipeline | Independent equation / quantization | Maximum channel error |
|---|---|---|---|
| C01 | sRGB texture → linear light ramp → SRGB8_ALPHA8 FBO → SDR readback | IEC sRGB piecewise decode/encode, input (128,192,64), light=(x+.5)/32 | 2/255 (sRGB conversion precision and byte rounding) |
| C02 | Background + glass ramp + particle disk, premultiplied blend | src×alpha + dst×(1-alpha), quantize after each layer | 2/255 (two blend/store roundings) |
| C03 | HDR ramp → RGBA16F → Reinhard | IEEE binary16 roundtrip, then x/(1+x), final RGB8 | 1/255 (half and byte quantization) |
| C04 | Scene → bright extract → 3-tap blur → bloom composite | Per-pass byte quantization, clamp-to-edge taps (1,2,1)/4, weight 0.5 | 2/255 (four stores and interpolation arithmetic) |
| C05 | std140 material + linear RGBA8 base-color texture | baseColor×texture×(1-0.5×roughness)+0.1×metallic | 1/255 (float-to-byte rounding) |
| C06 | RGBA8 multisample blend → matching resolve → tonemap | Quantize base and premultiplied blend before x/(1+x) | 1/255 (resolve and final conversion) |

These are numerical output contracts, **not one universal platform pixel error**.
The comparator uses maximum per-channel error, so a small corrupted region cannot
hide behind low global MAE. MAE is also recorded for diagnosis. Each of the six
scenes has an intentionally wrong rendering that must exceed its own tolerance.
Disabling the regression assertion cannot turn a broken render into acceptance.

C05 is a deliberately small material-binding/lighting formula, not a claim of a
complete energy-conserving PBR BRDF. S09 additionally renders two distinct material
parameter sets and rejects a real shader variant with swapped member offsets.

## Engineering rules and diagnostics

1. Tag source textures by intended encoding. Color images normally use sRGB
   formats, data maps normally linear formats. Sampling sRGB decodes before
   lighting. Do not manually decode a texture already decoded by the sampler.
2. Light and composite in linear space. Writing linear values to sRGB FBOs encodes
   at storage; avoid a second shader gamma. FBO support/completeness must be
   checked, not assumed from a requested format.
3. Pick straight or premultiplied alpha deliberately. Premultiplied output uses
   `ONE, ONE_MINUS_SRC_ALPHA`; multiplying by alpha twice produces dark edges.
   The glass ramp and disk regression makes that failure measurable.
4. Preserve HDR in a renderable floating-point attachment until tone mapping.
   This lab checks `EXT_color_buffer_half_float` or `EXT_color_buffer_float` and
   FBO completeness before using RGBA16F. An extension string alone is not proof
   every requested size/sample combination is valid.
5. Resolve uses compatible formats, equal rectangles, single-sample destination
   and `NEAREST`. Query renderbuffer sample support with `glGetInternalformativ`.
   This demo resolves RGBA8 and tests HDR separately: no unsupported float-MSAA
   promise is inferred. Polygon-edge sample coverage remains NOT_RUN.
6. ABI failures are binding failures, not artistic image differences. Reflect
   block size and member offsets, check sampler units, reject incompatible
   layouts before drawing, and retain the parameter name in the diagnosis.

## Backend comparison report template

Record device/GPU/driver/OS, EGL/GLES version and extensions, source/binary hashes,
attachment encodings/formats/sample counts, viewport, seed, capture orientation,
blend state, tone mapper and exact intermediate precision. Attach raw readbacks
and reference hashes, per-scene max error/MAE and difference images. For a failure,
classify input encoding / gamma / alpha / HDR clamp / ABI / backend arithmetic;
rerun the injected negative and known-good baseline before changing thresholds.

Separate result statuses:
- Software readback correctness: REPRODUCED in committed runtime report.
- Physical GPU correctness across vendors: NOT_RUN unless new captures attached.
- Real screen appearance/calibration, HDR display presentation: NOT_RUN.
- Physical GPU performance/bandwidth/thermal A/B: NOT_RUN.

Sources (normative specification, historical-context):
- https://registry.khronos.org/OpenGL/specs/es/3.0/es_spec_3.0.pdf
- https://registry.khronos.org/OpenGL/specs/es/3.1/es_spec_3.1.pdf
- https://registry.khronos.org/OpenGL/extensions/EXT/EXT_color_buffer_half_float.txt
- https://registry.khronos.org/OpenGL/extensions/EXT/EXT_color_buffer_float.txt

Reproduce with `examples/pipeline/build.sh`, then
`python3 benchmarks/pipeline/runtime.py`. See `examples/pipeline/README.md` for
SDK variables, the GLES version matrix and limits of each acceptance scenario.
