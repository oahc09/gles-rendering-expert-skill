# v1.1.0 candidate acceptance

**PARTIAL_CANDIDATE / ACCEPTANCE_BLOCKED**, not a completed release. See release-gates.json for authoritative statuses and immutable predecessor debt snapshots.

| Package | Status | Remaining boundary |
|---|---|---|
| W0 | HOST_AUDIT_COMPLETE | Historical failures remain preserved; no release waiver. |
| W1 | INDEX_COMPLETE | Structural index is complete for pinned snapshots, not complete semantic or runtime coverage. |
| W2 | HOST_BOUNDED | 16 authored families: Mesa32 probes, ANGLE28 plus four actual GLES3.2 capability gaps; special extension/whole grammar coverage not claimed. |
| W3 | HOST_BOUNDED | 27 software checks per driver; native Windows/Android/GBM windows, reset and native image paths not executed. |
| W4 | PARTIAL_WITH_DRIVER_FAILURE | Bounded two-layer multiview+sequential fallback and robust readback/canary boundaries pass on both software backends. ANGLE ordered coherent/noncoherent framebuffer fetch passes; Mesa fetch draw crashes despite advertisement, retained FAIL with working ping-pong fallback. Full multiview/Fetch semantics, PLS/VRS/AHB/native import and protected resources remain incomplete; reset query/readback are not reset recovery or device acceptance. ANGLE-specific PLS clear/store/load scopes and one explicit barrier pass with runtime-matched official ABI; Mesa only verifies fallback, not PLS. Minimal fetch diagnosis excludes several application-specific factors but has no proven root cause or native fix. |
| W5 | HOST_BOUNDED | 48 actual software legal/error interactions; existing hazards/lifecycle tests preserved, not target GPU performance. |
| W6 | HOST_KNOWLEDGE_BOUNDED | Counters/tool names and device workarounds require exact targets, trace, range and expiry; physical evidence absent. |
| W7 | PARTIAL | 15 categories indexed. Two-pose translation-only GPU skinning/CPU fallback and two-layer multiview now executed; SDF/MSDF and full OIT representatives remain absent, other finite scenarios retain original bounds. Video/target devices blocked; normals/DQ/rotation/asset rigs and performance not established. |
| W8 | HOST_INDEX_AND_LINK_CONTRACT | Offline reconstruction, pinned online source verification and explicit positive/negative linkage; no assertion of universal semantic acceptance. |
| W9 | PARTIAL_HOST_CTS_TARGET_BLOCKED | Official pinned software Mesa CTS FBO completeness subset: 578/578 Pass, not certification/full CTS/device coverage. ANGLE CTS initialization blocked before enumeration (0 cases). No Android APK/install; Gradle8.9 verified, SDK35/NDK27/CMake/build-tools and SDK agreement acceptance remain absent. Windows native and mobile target runs not performed. |
| W10 | BLOCKED_BY_PROVIDER | 100 authored frozen tasks, evaluator integrity and null-score no-provider execution delivered. Semantic deduplication, independent blind review and real paired model outputs unavailable. |
| W11 | PARTIAL | Review-only governance, no scheduling activation; original plan-window full review and independent acceptance remain incomplete. |
| W12 | ACCEPTANCE_BLOCKED | Original plan requires hardware/provider and inherited closure; no automatic release, version bump, tag or merge. |

No fixed quality budget was lowered, original failed images retained, no physical/provider score invented. A metadata index or parsed configuration is not a measured execution.

Distribution gap: clean offline checkout is INCOMPLETE because public gl.xml is intentionally not vendored after the large-object upload was rejected. Explicit pinned/hash-verified fetch is required; this gap is not waived.
