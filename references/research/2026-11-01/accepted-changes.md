# Accepted documentation changes (not release approval)

| Evidence | Change | Regression / reason |
|---|---|---|
| E01, E02 | Add exact embedded/WindowsArm compatibility targets; probe actual backend/vendor | C10; prevents OS-to-GPU hardcoding |
| E03 | Distinguish platform strategy from runtime GLES capability | C10; no policy-implied extension |
| E04–E06 | Keep Vulkan and GLES CTS tags separate and label dates | C05; no false GLES version advancement |
| E07, E08 | Record material/source/backend revision for cache decisions | W4 shader binary invalidation path; no engine API copying |
| E13, E14 | Explicit native-buffer/external ESSL3 dependency/fallback checks | C09; unsupported formats/extension absence |
| E15 | Require counter-conditioned depth-prepass/front-to-back choices | GPU05; preserve adverse result and fallback |

Only established spec semantics justify MUST. Research-based compatibility and performance guidance remains conditional. No physical performance claim has been accepted.
