# v1.1.0 implementation baseline

- Base main: `b1bf915e1f33404888b89174ad2857ffa78b6f2a`, merge of v1.0.9 PR #7; fetched 2026-11-15.
- Repository write permission verified through GitHub: push=true. User explicitly authorized this repository and PR submission, not merge/tag/release.
- Initial working tree was clean. Implementation branch is based on latest main, not the earlier local candidate commit.
- SKILL metadata remains 1.0.2. Merged candidates do not waive release gates.
- See feature-inventory.json (REUSE/EXTEND/MISSING/BLOCKED) and debt-ledger.json (all predecessor gate contents and hashes). Preserve failures, not just file links.
- No current physical Android/Mali/Adreno/PowerVR target or authenticated model provider is available. Software rendering is not device validation. No schedule is activated.
- Remote tags checked: only `1.0.0` at `02942f16a86bf04077ca116c8c77aa85a5251a0f` was returned. Do not invent a v1.0.9 release tag.

## Distribution and explicit dependency gap

Four large catalog/EGL artifacts are losslessly packed with decoded/packed hashes. Public Khronos `gl.xml` is NOT vendored: its attempted large upload was rejected by review and was not retried. The repository stores only its immutable official URL/commit/hash. A clean checkout offline is therefore INCOMPLETE, not offline-reproducible complete coverage.

Run `python3 tools/coverage/materialize.py --fetch-public` to explicitly read the pinned public XML dependency and verify its exact bytes; CI does this before validation. Without this flag, a missing dependency fails closed. Existing supplied XML is checked, never silently replaced. Neither the XML nor its rejected compressed object is uploaded as a CI artifact or repository object by this workflow.
