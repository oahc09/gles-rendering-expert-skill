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

## Remaining priority cards: INDEXED_ONLY, not semantically closed

EGLImage/AHardwareBuffer and native Sync, Robustness, Multiview,
Framebuffer Fetch/PLS, MSRTT, ASTC, VRS and Protected Content still require
spec-specific dependency, image/format/ownership/parameter probes and fallback
cards. The complete index makes these discoverable but does not claim they are
implemented on all GPUs or that the priority-card DoD is finished. A request for
an unimplemented family returns implementation-dependent/not usable.
