# v1.0.8 recovery validation, 2026-11-14

Candidate remains DRAFT / NOT RELEASE READY. Base recovery d38cde1 is authentic
remote work (five commits). This increment reconstructs W6, starts W7, adds W8
bookkeeping and manual CI, without claiming lost batch 6/7 was recovered.

## Current evidence
- 26 unittest directories discovered: 505 tests passed, zero skips; resource
  pressure setup initially failed before executing tests due missing headers.
  The local-toolchain retry passes all 12 resource tests (resource-retry.log).
  Total across suites + retry + gate tests: 522 passed, zero skips. Five additional v108
  gate tests pass, including rejecting false release-ready and waivers.
- Fuzz now runs 11/11 including real compiler tests, zero skipped. Official Debian
  trixie glslang 15.1.0 and SPIRV tools were downloaded from deb.debian.org, checked
  against SHA256 in official Packages.xz, extracted locally. Package filenames,
  versions and hashes: recovery-evidence/toolchain-packages.json. No system
  permissions/settings changed; initial apt installation was unavailable.
- W6: real Mesa llvmpipe EGL scene captures versus CPU golden: highp maximum
  RGBA8 code difference 0 (limit 1), mediump 1 (limit 3). See film.json. This is
  numerical validation of a stated approximation, not mobile/PBR fidelity.
- W7: 36 structured fixtures and 12 infrastructure tests. Full source-edit,
  minimize, run/differential pipeline remains incomplete. No real model scores.
- All predecessor bookkeeping gates run and remain enforced. --require-release
  exits 2 intentionally. Metadata stays 1.0.2; no tag/release/merge performed.

## Still blocking completion
- Fresh dual software-driver replay needs the pinned ANGLE bundle. Historical
  differential reports are not this run. CI deliberately fails closed when
  locked bundle is absent, producing BLOCKED_BY_TOOLCHAIN, not fake green.
- Real mobile/hardware validation and authorized provider pairing remain blocked.
- W7 full patch pipeline and metric completeness, W8 complete regression/runtime
  matrix and research revalidation remain incomplete. Manual CI has not run here.
- Forced MESA_GLES_VERSION_OVERRIDE=3.0 replay also passes both precision paths
  (film-es30.json); mobile precision coverage still remains pending.

## Follow-up: locked loader and W7 runtime pipeline

Restored official Playwright revision1194; four historical library hashes matched.
ANGLE initialization first failed because the old lock omitted the bundled
libvulkan.so.1, loaded alongside ANGLE; locking/extracting that fifth file fixed
it. Fresh Mesa llvmpipe + ANGLE SwiftShader differential now passes 47/47 cases
(recovery-evidence/dual-driver). This supersedes the missing-bundle blocker above,
not the hardware/provider blockers.

W7 adds a bounded ES310 arithmetic-source patch pipeline: compile/link, preserve
original diagnostic during ddmin, reproduce failure 3 times, independently execute
positive control, broken and fixed shader in both drivers with SSBO numeric CPU
oracles. Four arithmetic cases HOST_PASS with one-minimal reductions. A wrong
patch compiles on both drivers but correctly FAILs the numeric oracle. These
are authored patches, not model scores; no general source/image equivalence is
claimed. W7 complete metrics and provider coverage remain incomplete.

PR workflow run [43608344642](https://github.com/oahc09/gles-rendering-expert-skill/actions/runs/43608344642) passed on c9bd35b, including pinned driver provisioning and dual-driver tests. This historical CI result does not cover later commits. Local replay ran 22 validation steps: the v107 audit initially lacked the tarball recovery git history; fetching real history and repeating the audit passed (180 files, zero findings).

## Paired-review metric increment

Added strict score_v3 diagnosis accuracy/recall, false repair and false-positive
metrics, minimization fidelity/coverage, evidence completeness and condition
deltas. Evidence bytes must match supplied SHA256; unknown fields, missing
pairs and unmeasured-as-PASS records fail closed. Hashes do not authenticate
provider/reviewer identity. No real provider score produced.

Fresh complete unittest directory sweep: **555 passed, zero skipped, 26 suites**
(final-unit-summary.json). v108 repair tests: 41 passed including 21 new metric
boundary tests. Hosted CI on **fe88d6d** passed, including four actual dual-driver
repair controls and wrong-repair rejection: https://github.com/oahc09/gles-rendering-expert-skill/actions/runs/43608796300 .
This run precedes the review-metric increment; its new head requires separate CI.
