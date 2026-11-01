# W0 baseline and authority audit — 2026-11-01

- Repository explicitly named in the user's linked OpenGL ES Expert Skills conversation and full taskbook: `oahc09/gles-rendering-expert-skill`.
- Authenticated repository metadata: `permissions.push=true`, `permissions.admin=true`.
- Clean shallow clone of `main`: `129ba8324f23fdfbd6206f005891896a5f0fb7bd`.
- Existing published metadata: `SKILL.md` version `1.0.2`; only remote tag observed: `1.0.0` → `02942f16a86bf04077ca116c8c77aa85a5251a0f`.
- Baseline had no `.github/workflows`, tests, build files or executable validation toolchain. `tests/` is ignored; new tracked suites use `benchmarks/` and `examples/validation/`.
- Existing inventory: 31 cards; core/vendor rules; 6 C++ examples and shader examples. Existing triggers, platform/vendor subtrees and license retained.
- No AGENTS.md found in repository. `.cursorrules` technical instructions were included in audit.
- Existing LICENSE SHA256: `f448691d44b165a34d79953400b2c8dd8ff313a9d88fec1bb00eb046eb2c1a13`.
- Exact task source: conversation `6a643902-4ec8-83ea-bf77-2f75d3c3e617`, Library `libfile_78f16e9be1f081918cc28f071300d1c3` / `file_000000000c6881fb877bd3d376f8412d`.
- Archived `docs/v1.0.3-development-plan.md` SHA256: `ad7eb14767e6837574b7f8c0580bd9b4b18b1a263dead2f6575f56504886560f` (22,070 bytes).

## Risk register

| Risk | Mitigation / evidence gate |
|---|---|
| Normative GLES bans contradict GLES3 core | Correct ReadBuffer and sized formats, compile and runtime negative controls |
| Invented Android lifecycle event | Actual glue commands + EGL return-code recovery; Android device still required |
| Cross-context visibility | Producer fence/flush then consumer wait and ownership; actual shared-context pixel test |
| Performance rules overgeneralized | Conditional vendor/driver evidence and counterexamples; never extrapolate Mesa software |
| 30-day claims drift | Independently inspect original dates; distinguish old/out-of-window and unverified claims |
| Token counts/static checks mistaken for model results | Separate paired live adapter runs, manual adjudication and structural fixtures |
| Cloud workspace loss | Early remote source checkpoint; final committed evidence and source hashes |
| Premature version release | Keep metadata 1.0.2 until all gates accepted; Draft PR, no tag/release/merge |
