# Extension index and scoped capability decisions

The combined catalog contains every frozen applicable GLES/EGL extension with
namespace, supported APIs, original attributes and conditional require/remove
blocks. All are INDEXED_ONLY, semantic_status NOT_REVIEWED. An empty extension
command list does not imply no behavior or unconditional support.

`CapabilityNegotiator(catalog, api_version, extensions, entrypoints, limits)` uses
explicit context data. `negotiate(name, extension=..., required_extensions=...,
minimum_limits=..., probe_pass=..., dependency_reviewed=...)` returns
core / extension / implementation / unsupported plus usable and fallback.
The exact function pointer must exist. Aliases never authorize substitution.
Unknown semantic conditions, parameters, unreviewed extension dependencies or
absent runtime probe fail closed as implementation-dependent, not usable.
All supplied probes are scoped caller evidence, not authenticated runtime tests.
No performance statement is made.

## Three bounded reviewed decision adapters

`priority(family, ...)` has positive/negative unit cases, not live GPU certification:

- `debug_callback`: GLES3.2 core `glDebugMessageCallback`; earlier GLES uses
  advertised GL_KHR_debug and `glDebugMessageCallbackKHR`. This is callback entry
  selection, not acceptance of every debug-object type (pipeline support differs).
- `external_texture`: GL_OES_EGL_image_external requires EGL1.2 and
  EGL_KHR_image_base or EGL_KHR_image. ESSL3 sampler use additionally requires
  GL_OES_EGL_image_external_essl3. A scoped image/target/sampler probe remains
  mandatory. No AHardwareBuffer/native fence/protected-image support is inferred.
- `timer_query`: advertised GL_EXT_disjoint_timer_query, exact QueryCounterEXT
  pointer, scoped probe and explicitly false GPU disjoint. Unknown/true disjoint
  rejects timing use. No elapsed timing is collected by this module.

Primary pinned specification URLs, retrieval hashes and bounded summaries are in
`source-manifest.json` → `extension_specs`. Full prose is **not vendored** because
redistribution permission was not confirmed. Earlier reading of dependencies and
interactions, not extension-name guesses, informed these adapters. The offline
checker verifies citation metadata only, not the absent specification text.

## Actual bounded probes and remaining boundaries

The structural catalog remains INDEXED_ONLY. Separate runtime evidence does not
promote every related Registry entry to complete semantic acceptance.

- [Debug output](debug-output.md): real core/KHR callback, filtering, group/label and safe unregister checks; authored messages only, not arbitrary driver diagnostics.
- [Multiview](multiview.md): two-layer draw and sequential fallback, not all multiview configurations.
- [Robust readback](robust-readback.md): byte-size/canary checks, not actual reset recovery.
- [Framebuffer fetch](framebuffer-fetch.md): ANGLE finite ordered cases pass; Mesa crash remains FAIL with ping-pong fallback.
- [PLS](pixel-local-storage.md): runtime-matched ANGLE-specific finite scopes; Mesa fallback only.
- [Texture buffer](texture-buffer.md): bounded range/update checks; ANGLE ignored-offset boundary mismatch remains FAIL.

External native image/AHardwareBuffer ownership, MSRTT, VRS, protected resources,
actual reset recovery, arbitrary ASTC/HDR and timer-query collection still need
scope-specific runtime acceptance. Existing ASTC constant-block decode and EGL
image/sync controls do not close those larger families. Use the candidate release
matrix for current evidence; no GPU is assumed to implement every extension.
