# v1.0.5 research window: 2026-10-02–2026-11-01 inclusive UTC

This extends the existing radar and v1.0.3/1.0.4 archive, not a new scheduler.
`source-ledger.json` carries the exact v1.0.5 taskbook fields, dates, source hashes,
engineering impact and test mapping. `radar.json` is fetched candidate metadata,
not accepted rules. No background job, Actions run or automatic MUST promotion is enabled.

## Verified release dates and scope

* **P59 — Perfetto v59.1:** original GitHub `published_at` is
  `2026-10-27T02:09:05Z`. Official notes describe CLI/agent-mode and persistent trace
  capabilities. The Linux asset SHA256 matched GitHub's digest; actual version and
  binary hash are in `benchmarks/traces/sql/perfetto-tool-receipt.json`. We executed
  real native protobuf/SQL tests, but gained no private GPU counter access.
* **F179 — Filament v1.79.0:** `2026-10-26T23:44:28Z`; engine/material implementation
  changes merit revision-aware validation, not relaxed GLES core or GLSL rules.
* **RD147 — RenderDoc v1.47:** `2026-10-31T15:49:28Z`; tool maintenance is a candidate
  validation aid, not proof that every GLES driver supports capture/debugging.
* **F1772, CTS, KTX — historical:** Filament1.77.2 is `2026-09-28T20:59:51Z`, GLES
  CTS3.2.14.1 is `2026-07-21T14:48:19Z`, and inspected KTX latest release has original
  publication in **2025**, not 2026. None are October2026 releases. A latest tag can
  be old; discovery time is not publication time.

The reused radar fetched CTS, Filament, AGI, Perfetto, RenderDoc, glslang, KTX releases
and ANGLE commit metadata. All eight source fetches completed: 337 in-window candidates.
Commit committer dates are event dates, **not** independently established publication
instants. Publication remains null for commits. Candidate hash is the canonical full
GitHub API record SHA256; ledger release response hash is the original HTTP response
bytes SHA256. These are explicitly different hash domains.

## Non-release material and gaps

ADPF and GPU vendor guidance are context, not claimed October announcements. No
precise power savings, shared thermal-budget percentages or GPU-family-wide rules
were inferred. Mesa Oct28 release notes were inspected as driver-specific candidates;
full individual driver-commit reproduction is not complete. Khronos certification
records only support the named configurations. Nullable publication/event times stay
null rather than being replaced with a crawl timestamp. A source-byte hash proves
what was fetched, not whether a dynamic error page is useful evidence.

Searches included `site:x.com Perfetto v59.1 October 2026`, Arm thermal/power October,
Qualcomm Adreno power and PowerVR thermal documentation. **No dated original X post
with verifiable author/source/device evidence was retained.** X remains UNVERIFIED,
not a manufactured citation. Arm dynamic documentation and Qualcomm document access
are conservatively unverified when contents/dates cannot be established. No private
vendor SDK or device state was altered.

## Promotion boundary

`validate_v105_evidence` rejects incomplete source fields, malformed hashes, invalid
UTC dates, historical events called in-window, and implementation/X material promoted
to normative MUST. Even a specification row is never applied automatically: existing
review/reproduction lifecycle gates still apply. Normalized record hashes help review
source edits, but legacy source/ID dedup intentionally does not treat every metadata
edit as a new technology release; reviewers must inspect changed-source candidates
before revising an accepted decision.

Reproduce radar collection with the existing `references/research/update_radar.py`
using explicit dates and a separate archive directory, then inspect original sources.
Old raw-response hashes may change if GitHub edits metadata; retained selected-source
snapshots have independent `snapshot_sha256` for local integrity. They deliberately
omit entire release-note bodies rather than republishing third-party prose.
