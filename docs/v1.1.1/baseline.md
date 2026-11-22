# v1.1.1 W0 baseline (2026-11-21)

Scope: the existing GLES Rendering Expert Skill, not a new renderer or a release. The 2026-11-14 taskbook specifies one final v1.1.1 with W0–W14. This inventory supersedes its preliminary observations, not any requirement or gate.

| Item | Observed baseline |
|---|---|
| Default branch | [`8799c15faa38dafdee466ccaf01c45d5d911b073`](https://github.com/oahc09/gles-rendering-expert-skill/commit/8799c15faa38dafdee466ccaf01c45d5d911b073) |
| Predecessor candidate | [PR #8](https://github.com/oahc09/gles-rendering-expert-skill/pull/8), closed and merged into that main commit; prior base `b1bf915e1f33404888b89174ad2857ffa78b6f2a`, head `852e6184db27cc43ae0c110508f53f82e96d660c` |
| Inventory worktree | Initially clean, shallow checkout at the candidate head; main merge tree and candidate tree are identical (`881a623c532cdc8c6b4ec0b94a634c004b7fe7c9`), so inspected source bytes match the pinned main |
| Active PRs and version | GitHub open PR list empty at start; remote tag list only `1.0.0`; `SKILL.md` metadata remains `1.0.2`; v1.1.0 is merged candidate content, not a published v1.1.0 |
| Exact-head CI | [43752975965](https://github.com/oahc09/gles-rendering-expert-skill/actions/runs/43752975965) succeeded on `852e6184` (pull request validation), not on a v1.1.1 head. A green evidence-contract job does not turn recorded feature FAIL/BLOCKED/NOT_RUN into PASS. |
| Scope freeze | GLES Core 2.0/3.0/3.1/3.2; GLSL ES 1.00/3.00/3.10/3.20; EGL 1.4/1.5 (earlier cumulative EGL entries included by the index); GLES 1.x is migration-only; desktop GL excluded. Extensions are indexed comprehensively within the frozen registry and validated in layers. |

Observe status at both dimensions: **existence** (`existing` / `absent`) and **verification** (`verified_bounded` / `unverified` / `not_applicable`). Existence is about this repository tree; evidence is scoped to named checks. See [coverage-gap.csv](coverage-gap.csv) for reusable implementation, test, receipt and remaining work; see [preceding-gates.md](preceding-gates.md) for predecessor release decisions.

## W1 reuse, not duplicated catalogs

Use `docs/v1.1.0/coverage-scope.yaml`, `references/coverage/source-manifest.json`, packed catalogs and `tools/coverage/check_coverage.py`. The recorded result `INDEX_COMPLETE_NOT_SEMANTIC` uses exact frozen membership: GLES 3.2 = 358 commands and 1,001 enums; EGL 1.5 = 44 commands and 165 enums; the extension denominator spans 326 modern GLES, 24 legacy-only and 167 EGL entries (union 517). Registry indexing is not runtime support, a device extension claim or semantic acceptance. The existing semantic link contract has 24 rows / 18 API names; separately, eight bounded archived software runtime rows link six API names. Those are useful positive and negative seeds, not complete high-risk coverage. Preserve source hash and licensing controls; `gl.xml` is an explicit non-vendored public dependency, so a fresh source fetch or matching local source is required for full structural revalidation.

Keep `SKILL.md` triggers/version routing, CLI/schema/case IDs, license, source pins and established regression expectations intact. Unrecognized hardware stays unknown. Re-run exact evidence checks where prerequisites exist, record any stale or blocked receipt, and never backfill a release PASS.
