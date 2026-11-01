# v1.0.6 research window: 2026-10-03 through 2026-11-01 UTC

`2026-11-01/radar.json` is a fresh fetch by the existing radar, not a new crawler.
It records source status, candidate event/published timestamps and normalized API
record hashes. Candidates are not automatically MUST rules or verified device
bugs. `source-ledger.json` narrows the review to explicit official primary sources,
with raw-response hashes, event/published dates (null rather than guessed), affected
work packages, tests and decisions. Hash domains are labeled; a canonical metadata
hash is not interchangeable with the original HTTP body's digest.

* KTX v4.4.2 is **2025-10-04**, outside the research window. It is a historical
  engineering dependency actually exercised for W7. Do not turn a GitHub UI
  month/day display or today's download date into an October 2026 release.
* Filament v1.79.0 and Perfetto v59.1 have in-window official release timestamps.
  Metadata existence is verified; no new driver capability is inferred. Perfetto
  was already exercised in v1.0.5 and is reused rather than counted as new work.
* GLES CTS opengl-es-cts-3.2.14.1 is historical and distinct from Vulkan CTS.
* Protected-content and external-image specifications are historical reference.
  Registry HTTP requests from Python failed; successful official Khronos GitHub
  mirrors provide the separately labeled raw hashes. Browser registry reads were
  also consulted. No undocumented driver or DRM capability is inferred.
* Filament Android platform source is pinned to v1.79.0. Its file publication date
  is not invented from the release timestamp; no Android runtime was available.
* No verified original X post/author/date was retrieved; the ledger explicitly
  excludes that candidate class from normative decisions.

No **new, reproduced device-specific workaround** was verified in this window.
This is not a claim that no upstream updates occurred. ANGLE/Mesa/vendor candidate
commits still need individual source diffs and same-device reproduction. Mali,
Adreno, PowerVR and Vivante hardware and target ANGLE execution remain blocked.
The software DeviceLab probe and libktx/GL host tests do not satisfy those gates.
