# Selected primary-source review (AI analysis, not independent human sign-off)

Six actual release-note bodies were requested and read. The Vulkan CTS tag has no
body and is explicitly deferred. `release-review.json` records URLs, event dates,
body hashes and bounded implications. References below identify existing relevant
controls, **not reproductions of upstream bugs**. No performance rule is promoted.

| Source | Assessment | Engineering consequence |
|---|---|---|
| glslang 16.6.0 | Multiple malformed-input/constant-folding repairs, plus non-GLES extensions. | Keep compile-positive/compile-negative controls and runtime image oracles separate. New version acceptance needs regression tests; do not infer GPU speed. |
| Filament 1.80.1 | Shadow shader-program lifetime fix when program caching is disabled. | Resource-pressure infrastructure is relevant, but this finite test suite does not reproduce Filament's shadow/cache lifecycle. No local fix copied without reproduction. |
| RenderDoc 1.47 | OpenGL debugging corrections and mixed-API tool fixes. | A debugger's shader display is not the sole oracle. Preserve raw numerical pixels. No inference that our selected software driver has the described bug. |
| Perfetto 59.1 | Additional optional draw-level stage data and CLI/output changes. | Check trace schema and collector support before interpreting it; do not equate CPU slices or process duration with GPU elapsed time. Real device capture remains blocked. |
| SPIRV-Tools 2026.4 | Validator/optimizer correctness and robustness fixes. | SPIR-V checks apply to a relevant translation backend; native GLES compile/link/readback still required. The release does not prove transformed shader equivalence. |
| Vulkan CTS 1.4.7.1 | Empty release notes; Vulkan-labelled tag. | Defer any GLES normative claim until relevant source changes and GL CTS scope are verified. |

The selected sources support instrumentation and validation cautions, not new
quantitative optimization results. No speculative GPU-vendor workaround is enabled.
Full 1,319-candidate review, manual vendor/X verification and independent human
review are still incomplete. Read `implementation-review.md` for selected actual
ANGLE/Filament patch analysis; do not count title screening as source review.
