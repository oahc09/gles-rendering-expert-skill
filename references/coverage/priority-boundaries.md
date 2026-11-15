# Six scoped priority-extension boundaries

`tools/coverage/priority_boundaries.py` is an additional narrow policy layer; it
leaves the existing CapabilityNegotiator/catalog untouched. An extension string
or nonnull function pointer alone never makes a feature usable. Exact API route,
reviewed parameters/dependencies and a successful scoped probe are required.
`probe_pass=True` is caller-supplied evidence, not authenticated device proof.
Unknown families fail closed. No performance thresholds or benefits are invented.

## Reviewed scopes and sources

- **Sync:** core EGL1.5 names versus KHR suffixes; the older fence route requires
  its EGL/client-API dependencies and a current context. Probe creates, flush-
  waits and destroys a fence. Fallback is a separately verified completion path,
  not an asynchronous guarantee. [KHR_fence_sync v24](https://registry.khronos.org/EGL/extensions/KHR/EGL_KHR_fence_sync.txt).
- **EGLImage:** only owned complete2D texture to image lifecycle is covered.
  KHR route dependencies and core1.5 names differ. No native buffer/AHB import
  or zero-copy guarantee follows. [KHR_gl_image v13](https://registry.khronos.org/EGL/extensions/KHR/EGL_KHR_gl_image.txt).
- **Robustness:** core GLES3.2 reset-query versus KHR entrypoint. A returned
  NO_ERROR proves only this query's observed result, not robust-buffer context
  creation, actual reset recovery or permission to issue out-of-bounds accesses.
  [KHR_robustness v11](https://registry.khronos.org/OpenGL/extensions/KHR/KHR_robustness.txt).
- **MSRTT:** exact EXT entrypoints, requested samples within queried limit and
  verified RGBA8 attachment/probe are required. Single-sample or validated
  explicit resolve remains fallback. [EXT_multisampled_render_to_texture rev7](https://registry.khronos.org/OpenGL/extensions/EXT/EXT_multisampled_render_to_texture.txt).
- **ASTC:** conservative explicit-profile gate, only4×4 one-block LDR upload
  with16 bytes. Actual bad byte count must fail. This does not verify decode
  pixels, HDR/3D profile, asset quality or bandwidth. [ASTC specification v8](https://registry.khronos.org/OpenGL/extensions/KHR/KHR_texture_compression_astc_hdr.txt).
- **Protected content:** requires the protected context, resource and platform
  path to be independently established. Never copy protected data to an
  unprotected fallback. No protected transfer is attempted in the host harness.
  [EXT_protected_content v13](https://registry.khronos.org/EGL/extensions/EXT/EGL_EXT_protected_content.txt).

`priority-boundaries.json` records official revision/date/URL and observation
date. Full specification texts are not copied; these are revision-metadata
bindings, not claims of immutable vendored-document hashes.

## Actual probes and tests

```
python3 benchmarks/coverage/extensions/run_priority.py --config DRIVER_JSON --output REPORT_JSON
python3 -m unittest discover -s benchmarks/coverage/extensions -p test_priority_boundaries.py -v
```

The runtime reuses the actual EGL lifecycle demo for sync/image results, then
creates a new GLES context for reset-query and ASTC probes. Both Mesa and ANGLE
actually pass these four scoped probes. ASTC is upload-only; reset query does
not inject a GPU fault. MSRTT is not advertised on the two tested contexts and
is NOT_SUPPORTED; its guarded implementation is not claimed executed. Protected
secure-path evidence is absent and remains NOT_SUPPORTED regardless of string
advertisement. Runtime status HOST_PROBES_PASS_WITH_UNSUPPORTED is not full
extension coverage. Actual supported-probe failure remains FAIL, never disguised
as an unsupported route. Fourteen tests cover positive assumptions plus missing
probe, failed probe, entrypoint/dependency/parameter and secure-fallback negatives.

Multiview, framebuffer-fetch/PLS, VRS and AHardwareBuffer/native import have no
reviewed specialized adapter here and remain explicit gaps. Special reset
injection and platform protected presentation remain device/platform work.
Public evidence excludes raw environment identifiers and local paths. Only
source hashes, scoped results and explicit support boundaries are published.

Default CI runs the same CLI without suppression flags. A missing advertised
reset/MSRTT entrypoint, invalid queried MSRTT limit, actual probe failure or
incomplete/duplicate family set returnsFAIL and nonzero. NOT_SUPPORTED is
reserved for absent reviewed capability or explicitly unverified protected
platform path; it never converts an executed failing probe into success.
