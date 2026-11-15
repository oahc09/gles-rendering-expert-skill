# S05 software HDR → SDR numerical controls

```sh
python3 -m unittest discover -s benchmarks/hdr_controls -v
python3 benchmarks/hdr_controls/run.py --config DRIVER_JSON --output REPORT_JSON
```

Uses the existing operator-provisioned differential Host configuration. Report output excludes machine metadata, OS details, executable/library hashes and local paths. Only authored shader hashes, scene values, actual pixel arrays and numerical comparisons are published. Unsupported/incomplete floating attachment or float readback does not become PASS; the command returns nonzero unless all checks execute as expected.

## Actual two-pass GPU work

1. Render a 16×8 linear-HDR pattern into a real RGBA16F texture attachment. Eight values span 0 through 16, at exposures 0.25, 1 and 4 (maximum 64). Read that attachment as floating RGBA and compare exactly against independently generated binary-representable CPU values.
2. Bind a separate RGBA8 framebuffer, sample the HDR texture using texelFetch, apply Reinhard `L/(1+L)`, then the piecewise sRGB transfer function, and quantize on RGBA8 write. Alpha remains one. No sRGB framebuffer conversion is enabled; the explicit shader transfer writes sRGB-encoded values into a linear-format UNORM storage target.
3. Render three actual negative controls per exposure: clamp before tone mapping; gamma in the wrong direction; and gamma before tone mapping. They must fail the one-code RGBA8 budget against the same CPU golden.

## Verified software results

Mesa and ANGLE each completed 3 floating-point HDR draws/readbacks and 12 sampled SDR draws/readbacks. Floating values matched exactly. All three correct SDR outputs per driver matched CPU golden exactly (maximum code error 0). All nine negative outputs per driver were rejected; maximum errors span 43–133 codes. All 16 structural/CPU/invalid-input unit tests passed.

Full actual RGBA16F float values, RGBA8 pixel arrays, independent CPU goldens and per-arm source hashes are in `evidence/mesa.json` and `evidence/angle.json`. Both reports are HOST_PASS. Reference row order is bottom-up RGBA.

## Boundaries

This validates finite software-rendered HDR arithmetic, tone-map ordering, explicit sRGB transfer and SDR quantization. It does **not** establish HDR output/display support, HDR10/PQ/HLG/EOTF calibration, wide-gamut color management, perceptual fidelity, swapchain colorspace handling or physical GPU performance/power. No speedup or display acceptance is claimed. The HDR/SDR physical-device gate remains unverified; this test does not waive inherited HDR gates. Values are deliberately binary-representable to isolate pipeline correctness; it does not characterize all half-float precision/overflow/subnormal behavior.
