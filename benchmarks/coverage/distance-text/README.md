# Authored distance-field coverage representative

Actual GLES 3.0 RGBA8 texture upload, GL_LINEAR + CLAMP_TO_EDGE sampling,
fullscreen triangle, no blending/dither/depth, RGBA8 FBO and complete readback.
8×8 atlas rendered to 16×16 and 32×32. All atlas bytes are authored mathematics,
not font assets. No third-party binaries or fonts are imported.

The SDF is the signed Euclidean distance to a centered rectangle. The synthetic
three-channel case stores perpendicular x/y edge distances and their minimum.
Its median restores the inside-edge distance and deliberately differs from
selecting red alone. This bounded MSDF **decoder fixture** is not an msdfgen
output, a complete edge-coloring algorithm, or proof of arbitrary corner/glyph
quality. The outside-corner perpendicular metric differs from Euclidean SDF.

CPU oracle: independent clamp-addressed four-texel interpolation, sorted median,
cubic smoothstep and rounded UNORM8. GPU uses hardware filtering and GLSL
min/max median + smoothstep. Fixed ±1/output-size distance ramp, not a claim of
optimal filter footprint, derivative rendering, or perspective text quality.
Budget is 3 code values; not retuned per driver. Small PPM goldens are CPU
coverage over black, top-down; JSON pixels are actual bottom-up readbacks.

The grayscale coverage/alpha-mask fallback is generated independently at the
requested resolution, uploaded and actually sampled with NEAREST in another
GL draw. It does not merely return the CPU result. Fallback uses more per-size
storage and proves no performance advantage. Both atlas kinds have independent
goldens; SDF is not assumed interchangeable with MSDF around corners.

## Actual saved outcomes

18 draws and 18 readbacks per driver. MSDF max errors Mesa 0/1 at sizes16/32;
ANGLE 0/0. SDF errors Mesa 2/9, ANGLE0/0. Thus Mesa SDF32 **FAILS** budget3
and selects the independently rendered alpha-mask fallback, error0. Every
fallback is exactly equal to its original target on both drivers.
Wrong threshold, outline-instead-of-fill, and red-instead-of-median controls
all fail with max255. `HOST_PASS` means this fixed execution/rejection/fallback
contract passed, **not** every distance candidate passed. Candidate quality and
selection remain explicit. GPU timing and physical devices are NOT_MEASURED /
NOT_RUN. The filtering discrepancy alone is not proof of a driver violation.

## Run

```
python benchmarks/coverage/distance-text/run.py --config DRIVER_JSON --output REPORT_JSON
python -m unittest discover -s benchmarks/coverage/distance-text -v
```

Actual driver runs must be independent processes. CLI exits0 only for HOST_PASS;
exception/contract failure is nonzero. Reports omit environment fingerprints.

## Primary sources and attribution

Reviewed the original [msdfgen README, Using a multi-channel distance field](https://github.com/Chlumsky/msdfgen#using-a-multi-channel-distance-field): median after sampling, linear rather than sRGB channels, and scale-aware coverage. Its example uses a clamped linear opacity ramp; this fixture deliberately uses a cubic ramp with a separately defined oracle, not a claim to reproduce that example exactly.
[msdfgen license](https://github.com/Chlumsky/msdfgen/blob/master/LICENSE.txt) is MIT; no generator code, font, example asset, or library was imported. Atlas/runner are original work; elementary median mathematics is used with attribution. This module does not redistribute msdfgen.

## Lossless evidence delivery

`evidence/{mesa,angle}.json.gz` retains the complete JSON capture byte for byte.
`manifest.json` records compressed/uncompressed SHA256, sizes, draw/observation
counts and pixel-value counts. Raw `.json` files remain locally but are ignored
by Git. `run.py --output REPORT_JSON` still writes uncompressed reproducible JSON;
no shader, oracle, tolerance or decision was changed for packaging. To repackage
local captures, run `python benchmarks/coverage/distance-text/package_evidence.py`.
Gzip uses fixed timestamp and normalized header; unit tests decompress, hash,
validate all pixel-array lengths, recompute every error/quality, and verify
byte-identical repackaging. This is transport compression, not evidence reduction.
