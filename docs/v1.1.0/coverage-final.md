# Layered coverage report

The structural report is `coverage-report.json`, rebuilt from fixed licensed Registry XML. It reports INDEX_COMPLETE_NOT_SEMANTIC: exact frozen command/enum/extension membership, not proof every API is semantically reviewed or tested.

- Indexed: frozen GLES2.0–3.2 and cumulative EGL1.4/1.5 snapshots; migration-only GLES1 extension entries are not modern runtime capabilities.
- Semantic: explicit 24 positive/negative links for 18 distinct APIs plus narrow capability adapters. Remaining Registry entries stay INDEXED_ONLY.
- Compiled: 16 language-family pairs via actual glslang link and GLES compiler/linker; compile failure controls count as expected negatives, not runtime successes.
- Runtime: software EGL lifecycle and 48 GL interaction checks, plus inherited bounded software scenes. ANGLE GLES3.2 unavailable stages are PARTIAL, not PASS.
- Device: BLOCKED_BY_HARDWARE; Android build dependencies separately identified as BLOCKED_BY_TOOLCHAIN.
- Provider: BLOCKED_BY_PROVIDER; evaluator tests do not establish model scores.

Read the acceptance matrix before describing completeness. Public evidence omits private machine fingerprints and does not substitute hashes for independently authenticated measurements.

Offline distribution is PARTIAL: four packed artifacts restore exactly; gl.xml is an explicit non-vendored public dependency. A prior supplied-source successful check is not proof that clean offline checkout is complete.
