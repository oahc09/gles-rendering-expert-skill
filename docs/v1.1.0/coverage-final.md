# Layered coverage report

The structural report is `coverage-report.json`, rebuilt from fixed licensed Registry XML. It reports INDEX_COMPLETE_NOT_SEMANTIC: exact frozen command/enum/extension membership, not proof every API is semantically reviewed or tested.

- Indexed: frozen GLES2.0–3.2 and cumulative EGL1.4/1.5 snapshots; migration-only GLES1 extension entries are not modern runtime capabilities.
- Semantic: explicit 24 positive/negative links for 18 distinct APIs plus narrow capability adapters. Remaining Registry entries stay INDEXED_ONLY.
- Compiled: 16 language-family pairs via actual glslang link and GLES compiler/linker; compile failure controls count as expected negatives, not runtime successes.
- Runtime: software EGL lifecycle and 48 GL interaction checks, plus inherited bounded software scenes. A locally built pinned official GLES3 CTS executable ran the 578-case FBO completeness subset; all case records passed. CI validates its archived evidence, not a fresh CTS run. ANGLE GLES3.2 unavailable stages are PARTIAL, not PASS.
- Device: BLOCKED_BY_HARDWARE; Android SDK components and unresolved SDK agreement acceptance remain separate build blockers; verified Gradle alone is not an APK.
- Provider: BLOCKED_BY_PROVIDER; evaluator tests do not establish model scores.

Read the acceptance matrix before describing completeness. Public evidence omits private machine fingerprints and does not substitute hashes for independently authenticated measurements.

Offline distribution is PARTIAL: four packed artifacts restore exactly; gl.xml is an explicit non-vendored public dependency. A prior supplied-source successful check is not proof that clean offline checkout is complete.

Bounded extension increment: multiview two-layer draw/fallback and robust readback/canary boundaries pass on both software backends. ANGLE ordered framebuffer fetch passes. Mesa fetch draw crashes remain FAIL; separate-attachment ping-pong passes. Advertisement is not route acceptance, and archived-failure contract tests are not feature-pass results.
