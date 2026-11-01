# System effects: correctness before device optimization

## Scope and primary sources (historical context; checked 2026-11-01)

- [GLES 3.1 specification §7.11](https://registry.khronos.org/OpenGL/specs/es/3.1/es_spec_3.1.pdf): choose memory barrier bits for the **next consumer**. Shader-storage, image access, texture fetch, vertex fetch and API buffer mapping are distinct consumers. Coherent qualifiers do not replace API barriers between different mechanisms. This lab records each dependency in `benchmarks/system_scenes/dependencies.json` and actually draws from the compute output before CPU verification.
- [GLSL ES 3.00 §§4.5, 8.4](https://registry.khronos.org/OpenGL/specs/es/3.0/GLSL_ES_Specification_3.00.pdf): precision qualifiers are minimum guarantees; explicit binary16 packing is a separately controlled experiment, not proof of FP16 ALU execution or speed.
- [McGuire and Bavoil, Weighted Blended Order-Independent Transparency, JCGT 2013](https://jcgt.org/published/0002/02/09/): primary algorithm reference; its [author’s implementation guide](https://casual-effects.blogspot.com/2015/03/implemented-weighted-blended-order.html) was also checked. Accumulate weighted premultiplied color/alpha, multiply revealage, then composite. Our bounded demo deliberately uses **two geometry passes**, avoiding an assumption that per-target blend functions are available. Its chosen bounded weight curve is an engineering variant, not an exact reproduction of every paper parameter.

## Compute / fallback contract

`simulation particle|boids|wave STEPS gpu|cpu|degraded OUTPUT.json`:
- Seed1337, 64 particle/Boid states; wave16x16, periodic boundaries. Particle wall collisions are real state updates; Boids includes cohesion/alignment/separation. Wave is a height equation, not incompressible fluid simulation.
- GPU SSBO/image ping-pong never reads and writes the same state buffer in one step. CPU uses the same input and documented equations but an independent loop implementation. Numerical comparison is absolute-error bounded, not assumed bit exact across compilers/vendors.
- `cpu` needs no GL context, compute, SSBO, images or GLES3.1 symbols at runtime. An ES3.0 renderer may upload returned positions/height samples through its existing VBO/texture path; this standalone fallback validates simulation output, **not a physical ES3.0 device**. GPU paths require GLES3.1. Capability selection must occur before invoking them; failure does not silently certify GPU correctness using CPU output.
- Forced incorrect timestep/wave coefficient tests the numeric oracle. A deliberately missing barrier is **not** used as a reliable negative control because some coherent software implementations could accidentally pass it.

## Transparency / refraction

Sorted straight-alpha uses back-to-front ordering. It is a fallback with different overlap behavior, not a golden proof that weighted OIT is physically correct. OIT can misrepresent high-opacity intersecting layers and depth ordering; revealage RGBA8 quantization and accumulation RGBA16F range are documented limits. MSAA and opaque-depth occlusion require additional integration; this checkerboard-background demo does not certify them.

Glass renders front/back analytic orthographic depth signals, obtains positive thickness, perturbs a background lookup and applies Beer-like absorption. This is single-layer screen-space approximation: no offscreen refraction, total internal reflection, internal bounce or physically correct caustic transport. Before OIT, an actual temporary RGBA16F FBO completeness/error probe gates allocation. Unsupported capability exits3 with an explicit sorted/fallback recommendation; the sorted path uses an ES3.0 context and GLSL ES3.00 without any half-float target. `fallback` explicitly selects that path. The test-only missing16F override is labeled injected evidence. [EXT_color_buffer_half_float](https://registry.khronos.org/OpenGL/extensions/EXT/EXT_color_buffer_half_float.txt) supports half-float rendering/blending; [EXT_float_blend](https://registry.khronos.org/OpenGL/extensions/EXT/EXT_float_blend.txt) concerns 32-bit floating-point blending and is **not** wrongly required for RGBA16F here.

## Shadows, water and Forward+

Two real depth targets cover two fixed orthographic domains. Their sampled PCF result modulates the water-background composition; scene depth drives attenuation, with procedural caustic intensity. This is a small cascade/PCF correctness example, **not** production camera-frustum fitting, stabilization, perspective depth reconstruction or physically based caustics.

Forward+ performs real compute tile/light intersection and consumes a compact SSBO list in the fragment stage. The all-lights fallback is an actual uniform-array GLES3.0 shader path without dispatch/SSBO calls. A conservative 2D cull is correct for this planar signal; extending to 3D requires depth ranges and projection-aware bounds. No speed benefit is inferred from reduced loop counts.

## Four independent precision axes

Twelve W8 pairs isolate: three input storage/transfer cases; three ALU cases; three blend/alpha cases; three attachment cases. Positive results additionally compare to CPU expression oracles with tolerances; negative differences alone are insufficient validation. Explicit small power-of-two blend increments avoid treating a CPU round-to-nearest half converter as a GPU blend specification. The prior v1.0.5 real mediump/highp probes remain separate and unchanged.

## Release boundary

Frozen images and CPU↔Mesa comparisons establish L1 correctness for this software implementation. Android NDK compilation establishes buildability only. Mali/Adreno/PowerVR, mobile tile behavior, HDR display output, thermals, energy and cross-driver tolerances remain NOT_RUN_DEVICE/BLOCKED_BY_HARDWARE. Budgets are analytical logical byte/pass counts, not measured residency or bandwidth. A visually rejected optimization cannot pass solely because it reduces estimated passes.
