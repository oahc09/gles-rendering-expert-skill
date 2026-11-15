# Source-informed attachment transition controls

```sh
python3 -m unittest discover -s benchmarks/attachment_controls -v
python3 benchmarks/attachment_controls/run.py --config DRIVER_JSON --output REPORT_JSON
```

Finite controls informed by the ANGLE attachment/blending implementation review (commit prefix `035f888`), not an exact reproduction of that upstream defect. They use the existing software GLES Host and load only the operator-provisioned driver configuration. Public reports contain source hashes, independent expected pixels, actual readbacks and feature outcomes, never environment metadata.

## Actual workload and oracle

On one 4×4 FBO, replace COLOR_ATTACHMENT0 in sequence: RGBA8 → RGBA32UI → the original RGBA8 texture. Keep blending enabled throughout these three draws. For normalized RGBA8, clear destination to (0.2,0.4,0.6,1) then draw (0.8,0.2,0.4,0.5) with separate source-alpha RGB blending and alpha ONE/ONE_MINUS_SRC_ALPHA. The scalar CPU expected RGBA8 values are (128,77,128,255), with one-code quantization allowance. Before/after outputs must also be byte-identical. For unsigned integer attachment, draw (7,42,65535,123456); integer color must bypass blend arithmetic and match exactly. Query blend enable state after each transition.

Negative controls actually disable blending before the normalized draw, or change integer 42 to 43. They must fail the unchanged oracle.

When indexed draw-buffer state and at least three outputs are supported, attach normalized output at slot 0 and integer output at slot 2, set draw buffers `[COLOR_ATTACHMENT0,NONE,COLOR_ATTACHMENT2]`, enable indexed blending for 0 and 2, and draw mixed float/uint outputs. Read both attachments independently. An indexed negative control disables blend only on slot 0 and must fail its normalized golden. Core entrypoints are used only for GLES 3.2; otherwise the advertised EXT/OES suffix is used. `eglGetProcAddress` returning a core stub does not prove the core feature is supported.

If the indexed feature or mixed sparse FBO is unavailable, the report explicitly records UNSUPPORTED for that optional branch and the finite single-attachment scope remains. This is not reported as sparse-MRT PASS.

## Verified results

Both Mesa and ANGLE executed the full single-attachment **and sparse indexed MRT** branches. Per driver:

- 7 real draws and 8 independent readbacks.
- 5 positive comparisons passed (3 transition results +2 sparse attachments).
- 3 rendered negative comparisons failed as expected.
- Normalized max error 1 code; uint max error 0; before/after normalized outputs byte-identical.

Twelve unit tests passed. `evidence/mesa.json` and `evidence/angle.json` preserve every readback and independent golden. Both report HOST_PASS. No physical-device, performance, exhaustive MRT permutation, arbitrary attachment mutation or complete upstream-regression-reproduction claim is made.
