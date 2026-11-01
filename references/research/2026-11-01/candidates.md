# Candidate queue

| Candidate | What / evidence | GLES impact / device | Decision / next test |
|---|---|---|---|
| ANGLE `1ef82576` | Oct26 metadata says termination deadlock fixed; original commit URL in E12 | EGL shutdown, affected backend needs diff confirmation | UNVERIFIED applicability; inspect diff, reproduce C04 thread shutdown, then review |
| ANGLE `34394cfe` | Oct29 metadata says Vulkan backend EGL-image self-copy crash fixed; see radar URL | Image aliasing/backend-specific behavior | Do not invent workaround from title; inspect source + C09 minimal repro |
| Perfetto v59.1 | E11 official release notes | Diagnostics, device-dependent trace support | Verify actual capture format/counters and overhead on phone before adopting |
| Filament 1.78.1 | Original release metadata archived | Engine-specific implementation | Inspect backend diff, retain only GLES-relevant findings; no new core rule yet |
| X | No original, dated, cross-verified source retained | Unknown | UNVERIFIED / not entered as evidence or MUST |

Every candidate must eventually record what happened, original date/source, impact, target devices, rule decision and regression ID. Unreviewed metadata rows remain candidates, never silently promoted.
