# Shader variants and driver-local program caches

Scope: GLES Core 3.0/3.1/3.2. The validator is a conservative policy subset, not a GLSL compiler. `compute`, `ssbo`, and `image` require 3.1; core geometry/tessellation require 3.2. Extension alternatives need separately authored shader paths, not a lower core version flag. `external_texture` requires the probed `GL_OES_EGL_image_external_essl3` snapshot. PBR/unlit exclusivity is a project Recommendation, not a GLES requirement.

## Reproduce

- `python -m unittest discover -s benchmarks/pipeline -p test_variants.py -v`
- `benchmarks/pipeline/cases/variants.json`: 14 positive/negative inputs spanning 3.0, 3.1, 3.2, unsupported versions, extension probing, exclusive features and low-tier fallback.
- `benchmarks/pipeline/schemas/variant.schema.json`: interchange shape; `variants.validate` adds semantic constraints.
- `variants.generate` enumerates feature subsets × versions × quality under a pre-expansion candidate ceiling. Valid results beyond the accepted-variant budget are explicitly counted as pruned; illegal combinations remain rejected. The caller chooses a supported low-tier path rather than silently downgrading shaders.

## Cache contract

`cache_key(source, macros, options, device)` hashes the complete combined stage sources, macro map, ordered compile options, GL_VENDOR, GL_RENDERER, GL_VERSION, explicit driver/build identity, backend identity, material ABI identity and sorted extension snapshot. The required device fields `backend` and `material_abi` must be nonempty strings: use a canonical ABI digest/version that changes with types, layouts, bindings and interface contracts. Backend changes (including native/ANGLE/Vulkan translation paths) must invalidate the entry. Source must include transitive include contents and generated preambles; supply all linked stages, not just the fragment stage. Persist the key, the driver-returned binary format and bytes atomically. Cache storage and eviction are application responsibilities.

GLES 3.0 exposes `glGetProgramBinary` / `glProgramBinary`, but `GL_NUM_PROGRAM_BINARY_FORMATS` can be zero. Query supported formats on the current context. Set `GL_PROGRAM_BINARY_RETRIEVABLE_HINT` before linking where needed, retrieve the actual length and format, and never infer binary portability across vendors, drivers or ANGLE backends.

`load_program` calls the supplied binary loader only for matching lowercase 64-character SHA256 keys, nonempty bytes within the configured bound and supported formats. The default binary cap is 16 MiB, configurable from 1 byte to an absolute 64 MiB cap. Oversized blobs fall back without reaching the GL loader. Enforce the same bound before disk/network allocation; this in-memory policy cannot undo an already allocated buffer. That callback must check GL errors and `GL_LINK_STATUS` after `glProgramBinary`; exceptions, rejection or bad format invoke source compile/link. Source callback failure raises a hard error. Restore uniforms, block bindings and sampler units after either link path. Tests cover key changes, unsupported formats, empty/corrupt binaries, thrown loader errors and failed source fallback. Python callback tests are policy tests; actual GL results belong to the runtime lab, not this unit-test claim.

Offline glslang checks GLSL syntax and interfaces. Successful glslang output is not evidence of driver compilation, link success, program-binary portability or improved performance. Use the linked runtime lab for actual GLES compilation and cache fallback evidence.

## Sources and evidence

- [GLES 3.0 specification](https://registry.khronos.org/OpenGL/specs/es/3.0/es_spec_3.0.pdf), program binaries and shader compilation/linking: SPEC_CONFIRMED, historical-context.
- [GLES 3.1 specification](https://registry.khronos.org/OpenGL/specs/es/3.1/es_spec_3.1.pdf), compute, image load/store and SSBO interfaces: SPEC_CONFIRMED, historical-context.
- [GLES 3.2 specification](https://registry.khronos.org/OpenGL/specs/es/3.2/es_spec_3.2.pdf), geometry/tessellation core: SPEC_CONFIRMED, historical-context.
- [OES external ESSL3](https://registry.khronos.org/OpenGL/extensions/OES/OES_EGL_image_external_essl3.txt): extension contract, historical-context.

No static result establishes a physical-device performance claim.
