# v1.1.1 inherited gates

This summarizes the predecessor gate files at W0's pinned tree. All eight report `release_ready: false`; no approval or waiver is inferred from a merge, exact-head CI success, a schema dry run, a software result, or this inventory.

| Version | Authoritative gate | Non-pass packages at baseline |
|---|---|---|
| 1.0.3 | [Gate](../release-gates.json) | Partial W1/W5/W7; hardware W2–W4; provider W6. |
| 1.0.4 | [Gate](../v1.0.4-release-gates.json) | Partial W2–W4/W7; hardware W1/W5; provider W6. |
| 1.0.5 | [Gate](../v1.0.5/release-gates.json) | Partial W2/W3/W5–W7; hardware W1/W4; provider W8. |
| 1.0.6 | [Gate](../v1.0.6/release-gates.json) | Partial W4; hardware W1–W3/W5–W8; provider W10. |
| 1.0.7 | [Gate](../v1.0.7-release-gates.json) | Partial W4/W9; hardware W3/W5/W6; provider W8. |
| 1.0.8 | [Gate](../v1.0.8/release-gates.json) | Partial W0–W6/W8; provider W7. |
| 1.0.9 | [Gate](../v1.0.9/release-gates.json) | Partial W0–W7/W10; hardware W8; provider W9. |
| 1.1.0 | [Gate](../v1.1.0/release-gates.json) | W0 host audit complete, W1 index complete; bounded W2/W3/W5/W6/W8; W4 partial with driver failure; W7 partial; W9 partial host CTS / target blocked; W10 provider blocked; W11 partial; W12 acceptance blocked. |

Use the linked files for exact work-package meaning, limits and evidence. For 1.1.0, [coverage](../v1.1.0/coverage-final.md) reports Mesa framebuffer fetch draw failure and separate passing alternatives; do not substitute those alternatives into the original acceptance claim. The pinned 578 FBO CTS cases cover a subset, not full CTS, and the CI validates that archive rather than rerunning all CTS. Committed evidence separates Android tooling/build, actual device behavior and provider scores.

For v1.1.1: keep every unresolved predecessor gate open until exact evidence exists or an authorized reviewer explicitly accepts a non-core platform limitation. Record commands, commit, device/toolchain, raw artifacts and scope. Hardware, secure isolated Agent execution, representative blind real-model evaluation, and final release authorization cannot be replaced by fixtures or this document.
