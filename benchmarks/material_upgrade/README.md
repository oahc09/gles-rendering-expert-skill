# W6: versioned thin-film reference

`model.py` supplies independent CPU numerical reference, version 1→2 upgrade,
lossless-only rollback, canonical cache identity (parameters + prior std140 ABI +
shader + driver + precision). It reuses the v1.0.7 material validator.
`examples/material_upgrade/film.cpp` reuses the existing EGL 3.0 context,
compiler, FBO and readback harness. It reflects the UBO size before drawing.

Run `python3 benchmarks/material_upgrade/run.py --output /tmp/film` with EGL/GLES
headers and libraries installed. Optional `GLES_SDK_ROOT` is a prefix containing
`include`; `GLES_LIBRARY_DIR` identifies an extracted official runtime. The runner
compiles once and executes independent highp and mediump shaders, comparing a
64×64 thickness/angle chart to a CPU-generated PPM golden. Tolerances are 1 and
3 RGBA8 code values respectively; all pixels must pass. They measure numerical
agreement with this approximation, NOT physical or perceptual fidelity. The
entire shader uses ES 3.0 features, no compute/SSBO or 3.1 extension is needed.

The model uses Snell optical path and normal-incidence interface amplitudes at
650/510/475 nm. It omits angle-dependent polarization, spectral-to-XYZ integration,
absorption, dispersion and full layered BRDFs. This is a teaching approximation,
not an implementation of Filament's iridescence model and not a new GLES API.
Zero film thickness collapses to the air/substrate Fresnel reference (0.04).

The original plan's Filament release-date claims remain preserved as historical
research data, not newly verified facts. Consult upstream shader/material source
before interpreting a material revision as an API change:
https://github.com/google/filament/tree/main/shaders/src

No missing tool, exception, unavailable context or unsupported render target is
reported PASS. Real mobile precision and performance remain BLOCKED_BY_HARDWARE.
Negative contracts cover future versions, unknown fields, negative/NaN thickness,
invalid index/strength, invalid migration targets and lossy rollback. Changing
shader, driver or precision invalidates the program-cache identity.
