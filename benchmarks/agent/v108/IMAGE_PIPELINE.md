# Bounded fragment-source image repair

`image_pipeline.py` draws a full-screen triangle into a fixed **4×4 RGBA8**
framebuffer using GLES 3.0 and reads all 64 channel values back. It extends the
existing W5 `Host` for actual drawing and reuses W1 process quotas; Mesa and
ANGLE run separately under 45-second / 4-GiB / 1-MiB log-output limits. No
network, provider, arbitrary command, loop, shader extension, texture, compute
write or variable-size target is accepted. Shader expressions are deliberately
restricted to a finite set of 12 reviewed sources, not arbitrary model code.

Four non-arithmetic defect families each have a repaired shader, original
broken shader and a different **compilable wrong repair**:

1. UV x/y swizzle versus vertically/horizontally inverted UV.
2. RGBA/BGRA swizzle versus another incorrect channel mapping.
3. Premultiplied RGB with unchanged alpha versus missing/double alpha treatment.
4. Output alpha 0.5 versus opaque alpha or incorrect RGB premultiplication.

The CPU oracle independently evaluates scalar pixel-center and channel formulas.
Both drivers must match it within one RGBA8 code value **and** match each other.
Two identical wrong images cannot pass. The original and wrong repair must both
compile/link, execute without GL error, and fail the image oracle. Compile or
runtime failure is UNKNOWN, never accepted as the intended image negative.
No sRGB conversion, blending, dithering or color-managed display is involved;
readback rows are bottom-to-top. This is a numeric image test, not calibrated
display validation or pixel-level replication of a user artwork.

```sh
python3 -m unittest discover -s benchmarks/agent/v108 -p 'test_image_pipeline.py' -v
python3 benchmarks/agent/v108/image_pipeline.py \
  --config /path/to/trusted-two-driver-config.json --output /tmp/new-image-run
```

Config follows `shader_pipeline.validate_configs`: exactly one Mesa and one
ANGLE entry, existing trusted absolute EGL/GLES library paths and ANGLE ICD.
The executable is fixed by the harness, never supplied by a model. Report
captures source strings/hashes, driver/library metadata, all raw pixels, CPU
goldens, compiler/linker logs and the twelve comparisons.

## Actual run

`evidence/image-2026-11-14/report.json` records **HOST_PASS**:
- Four repaired shaders: CPU and peer image comparison PASS.
- Four originals and four wrong repairs: compile/link success, intended image FAIL.
- Twelve variants × two real software implementations = 24 tiny draws/readbacks.
- Twelve dedicated boundary tests pass.

These are authored repair controls. **BLOCKED_BY_PROVIDER**, model quality
**NOT_EVALUATED**, physical GPU **BLOCKED_BY_HARDWARE** remain unchanged.
The finite-domain controls do not claim general model-generated shader safety,
full W7 completion, hardware performance, or a real model quality improvement.
