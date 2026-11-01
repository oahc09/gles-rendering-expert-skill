# v1.0.5 baseline and dependency audit (2026-11-01 UTC)

Actual main: `e16ff0880d6c9f3d9435ca3f0027de9e92d6b5f1`.
PR #2 was already merged by the maintainer before this task; its tested head was
`adf875652a327282d08d8fc39259585d49c0f13e`. This task does not merge or publish.
Remote tags currently contain only `1.0.0` (`02942f16a86bf04077ca116c8c77aa85a5251a0f`).
Skill metadata remains **1.0.2**. Checkout was clean before adding this exact plan.
The taskbook's older observation that v1.0.4 was not present is superseded by these
verified source and PR facts, not silently treated as current.

Plan: Library `libfile_aaf9c6517388819191260f2b2d3bdb40`, 16,435 bytes,
SHA256 `49d294b08e0629b61646d37ffd0c6e9a19fe7eeeb2d60e32db7630418ba23661`.
Full source: [development-plan.md](development-plan.md).

| Existing area | Actual state and evidence | v1.0.5 use / dependency |
|---|---|---|
| 30 normalized rule contracts /112 cases;16 ESSL tests | IMPLEMENTED / TESTED_HOST | Reuse IDs, do not rename cases as rules |
| EGL harness and six legacy examples | TESTED_HOST + Android API26 arm64 compile/link; device UNVERIFIED | Reuse context/GL helpers and compiler runner |
| DeviceLab, native/ANGLE fingerprint contract | IMPLEMENTED / TESTED_HOST software only | Reuse capability identity; physical pair PREDECESSOR_BLOCKER |
| Eight actual GLES SceneLab workloads /goldens | IMPLEMENTED / TESTED_HOST; no physical performance | Reuse rendering/capture infrastructure; new precision/quality cases are delta |
| Vendor adapters /trace manifests | IMPLEMENTED conditioned hypotheses and synthetic fixtures | Reuse lineage/schema; add SQL/longrun rather than replace |
| Android AHB import and PQ output | IMPLEMENTED; Java/API35, NDK/API26 compiled, host policy tested | Device lifecycle/import/HDR UNVERIFIED; not a missing-source claim |
| Android APK | BLOCKED by actual Gradle JVM network path, no proxy bypass | PREDECESSOR_BLOCKER; do not claim APK from javac |
| Agent64 + repair24 =88 | IMPLEMENTED;24 authored repair executions TESTED_HOST | Append24 unique cases, preserve old88 unchanged; provider PREDECESSOR_BLOCKER |
| Live models/physical thermal-power measurements | BLOCKED / zero provider calls | L3/L4 remain separate from host/fixture tests |
| v1.0.3/v1.0.4 release gates | Both release_ready=false | Preserve and chain into v1.0.5; no waiver inferred |

New work is W1 longrun schema/diagnosis, W2 deterministic recommendations,
W3 numeric/color correctness, W4 estimated resource budgets/stress,
W5 Perfetto SQL evidence, W6 region/multiscale visual checks,
W7 date-grounded evidence ledger, W8 appended benchmark and integration.
No automatic CI, device settings, provider billing or production deployment is
inferred. Candidate source can be reviewed while physical/provider gates block.
