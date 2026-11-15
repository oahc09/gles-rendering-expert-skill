# Finite OVR multiview2 execution boundary

Official sources are pinned in `benchmarks/coverage/multiview/sources.json` to
OpenGL-Registry commit `6af574a14089ccfee87efe230ebcdd8742859813`.
OVR_multiview is revision 6 (2018-10-19); OVR_multiview2 author revision 0.5
(2018-10-19). The latter document's own status is **Incomplete**, retained here
rather than relabeled as final. Only original summaries and source hashes are
stored, not specification text. These extension documents are not implementation
code licensed for arbitrary copying; no blanket repository license is assumed.

## Actual tested contract

GLES3 context, both OVR extension strings, exact
`glFramebufferTextureMultiviewOVR` entrypoint, and queried MAX_VIEWS_OVR >=2 are
required. Advertising alone is not acceptance. Both Mesa and ANGLE executed:

- Two-layer immutable RGBA8 texture array, 4×4 per layer.
- Ordinary sequential fallback: attach each layer separately and draw red/green.
- Clear both layers to a blue sentinel, then attach both views together and issue
  **one actual multiview draw**. Vertex `gl_ViewID_OVR` controls a flat fragment
  input under multiview2. Each layer is subsequently attached to a separate
  single-view read framebuffer and independently read back; all 16 pixels must
  equal exact red or green. Prior fallback data cannot make a no-op pass.
- Four independent specification-defined errors: zero view count, count above
  MAX_VIEWS_OVR, negative base view index (INVALID_VALUE), and non-array texture
  (INVALID_OPERATION). No undefined behavior is used as a negative oracle.

Both drivers: HOST_PASS, 4 layer readbacks, 3 positive draw calls total, 4 error
checks. No stereo scene, projection matrices, MSAA multiview, view-dependent
texture sampling, maximum-view stress, GPU timings or physical-device coverage
is claimed. Fewer draw calls is a measured call count, **not** a performance win.

The vertex shader uses explicit `uint(gl_ViewID_OVR)` conversion. Initial Mesa
compilation rejected implicit assignment to the uint varying while ANGLE did
not; the explicit legal conversion compiled on both. This is a portability
observation, not a claim of a fully isolated driver specification bug.

## Fallback and failure

The sequential per-layer route is actually executed and checked even when the
multiview capability is absent. Missing capability yields NOT_SUPPORTED and
nonzero default CLI status, never fake multiview success. Advertised route with
missing pointer, invalid limit, failed compile/FBO, GL error or wrong pixels
is FAIL. A caller may use only a separately verified sequential fallback, not
silently claim the unavailable multiview route passed. Current CLI's archive
validator requires the complete six-row positive/negative result set.

```sh
python3 tools/coverage/multiview.py --config DRIVER.json --output REPORT.json
python3 -m unittest discover -s benchmarks/coverage/multiview -p 'test*.py'
```

Seven tests check dependency gates, exact independent layer outputs, sentinel
no-op rejection, missing negative errors, incomplete reports and unsupported
not being PASS. Stored reports bind runner and shared Host source hashes and
contain only relevant advertised capability facts, not a full device fingerprint.
