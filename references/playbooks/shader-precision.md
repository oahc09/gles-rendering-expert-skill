# Shader precision, linkage and UBO diagnosis (C05 / C11)

Capture the source after preprocessing, GL/GLSL version, enabled extensions, compiler/linker logs and program interface. Compile success does not imply link success or visual correctness. Offline glslang acceptance does not replace the target driver.

* Choose `#version 300 es`, `310 es`, or `320 es` according to the actual context and feature; a newer header does not raise the device version.
* Set explicit fragment floating-point precision. Use highp for large world positions, depth-sensitive calculations and values outside mediump range; only lower bounded calculations after visual/range testing.
* Match stage interfaces as required by the selected GLSL ES version. Test intended matching and deliberately mismatching precision/type/linkage separately; don't treat all compiler warnings as failures.
* For `std140` uniform blocks, CPU struct packing is not a portable layout calculator. Query active uniform offsets, array/matrix stride and row-major state, or calculate the exact standard layout; account for aligned arrays and matrices. UBO base offset must satisfy `GL_UNIFORM_BUFFER_OFFSET_ALIGNMENT`.
* Render stress patterns: large coordinate magnitudes, very small deltas, HDR bright values and gradients. Compare highp reference and candidate with a documented error tolerance. Fix the minimum required variables; “all mediump” is not a valid universal optimization.

Regression: legal versions, illegal cross-version syntax, stage linkage errors, two array elements plus matrix in UBO, offset-alignment negative case. See the [driver smoke](../../examples/validation/egl_smoke.cpp) and [precision card](../cards/05-shader-precision-layout.md). Actual compiler result and modeled rule result must remain distinct.

Sources: [GLSL ES 3.00](https://registry.khronos.org/OpenGL/specs/es/3.0/GLSL_ES_Specification_3.00.pdf), [GLES 3.0](https://registry.khronos.org/OpenGL/specs/es/3.0/es_spec_3.0.pdf).
