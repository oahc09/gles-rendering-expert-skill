# Material parameter ABI and binding validation

The flat contract in `benchmarks/pipeline/manifests/pbr-material.json` is additive and independent of engine public APIs. It describes a 32-byte std140 `Material` UBO: `baseColor` vec4 at 0, `roughness` float at 16 and `metallic` float at 20. `baseColorTex` uses texture unit 0, sampler2D and RGBA8. The runtime lab provides actual C++17 layout assertions, linked shader reflection and rendering.

## Version and interface boundaries

- GLES 3.0: UBO/std140 and samplers. Bind UBOs through `glUniformBlockBinding` and `glBindBufferBase`; sampler uniforms through `glUniform1i`. Shader `layout(binding=...)` must not be copied indiscriminately into GLSL ES 3.00.
- GLES 3.1+: SSBO/std430 and program-interface reflection. A std430 UBO is rejected by this contract. UBO and SSBO binding indices are separate namespaces.
- `location`, when present on a sampler, is the observed linked-program uniform location, not an offset or immutable cross-link identity. Refresh it after every link. Inactive optimized-away parameters require a deliberately smaller contract; this validator expects declared contract resources to be active.
- Optional `interfaces` compare flat producer/consumer type, extent and interpolation (varying precision may legally differ between stages). These are expected shader-interface agreements, not a replacement for real link diagnostics. This subset does not implement interface blocks, structures, row-major or nonsquare matrices.
- GLES has no Vulkan descriptor sets. A `set` field is rejected. Binding limits must be queried on the current context and supplied as `max_ubo_bindings`, `max_ssbo_bindings`, and `max_texture_units`; the default 16 texture units is a conservative application budget, not a queried device capability.

## Layout rules and checks

`layout_members` supports scalar, integer/vector and square column-major matrices, with fixed-size arrays. std140 scalar/vector arrays round alignment to 16; std430 retains natural alignment. Matrix columns follow corresponding vector-array rules. vec3 has 16-byte alignment but occupies 12 component bytes, so a following float may occupy its tail. Final block size rounds to maximum block alignment. Reflection remains authoritative on a real linked program; do not blindly memcpy an arbitrary C++ struct.

`material.validate(manifest, reflection=None, baseline=None)` reports named parameters, expected offsets/strides, block sizes, colliding bindings, format/sampler mismatches, texture unit limits, sampler-type aliasing and version errors. Same-type sampler aliases are allowed. The optional reflection uses the same block names, binding, size and member offsets/strides, types, array extents and matrix orientation; sampler reflection is required for contracted samplers and checks name, type, unit and location. `baseline` rejects differing ABI signatures across variants. Array extents/types must not change unnoticed.

Format validation is deliberately a documented subset, not a claim that all listed formats are renderable/filterable on every target. Query format/extension capabilities, sampler state and framebuffer completeness separately. Depth comparison state and shadow sampling need runtime state inspection. Numeric sampler type compatibility is mandatory.

## Reproduce

`python -m unittest discover -s benchmarks/pipeline -p test_material.py -v`

Fourteen fixture cases include valid PBR, std140 offsets/size, illegal UBO std430, version-gated SSBO, unit range, integer texture mismatch, sampler collisions, binding collisions, descriptor-set rejection, sRGB and array stride. Additional tests exercise vec3 tail packing, mat2 std140/std430, reflected offsets/units/locations, shader-interface mismatch and cross-variant ABI drift.

Sources: [GLES 3.0 spec](https://registry.khronos.org/OpenGL/specs/es/3.0/es_spec_3.0.pdf), uniform blocks, texture completeness and linking; [GLES 3.1 spec](https://registry.khronos.org/OpenGL/specs/es/3.1/es_spec_3.1.pdf), shader storage and program interfaces. Evidence: SPEC_CONFIRMED, historical-context. Python fixture results are REPRODUCED contract tests, not a conformance suite or physical-device certification.
