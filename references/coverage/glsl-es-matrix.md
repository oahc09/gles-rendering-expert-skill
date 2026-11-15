# GLSL ES finite compiler-backed closure matrix

Sources: [Khronos GLSL ES specifications](https://registry.khronos.org/OpenGL/index_es.php), language versions1.00/3.00/3.10/3.20. Authored fixtures are not copied CTS or exhaustive language proofs.

`tools/coverage/verify_glsl.py` runs installed glslang's actual `-l` compilation/link, then optionally actual GLES driver compile/link. It never uses regex to accept shader language. `benchmarks/coverage/glsl/corpus.py` deterministically generates32 fixtures, one positive/negative per16 families:

migration100; lexical/preprocessor; precision; types/arrays/matrices; control flow;
uniform/std140; output layout; texture/derivatives; compute/SSBO/std430;
atomics/barriers; image store/access qualifier; extension gating; varying/link
interface; interpolation; geometry/version; tessellation/version.

Explicit3.0→3.1 compute boundary and3.1→3.2 geometry/tessellation boundary are
compiler-tested. A legal100 OES_standard_derivatives require path and invalid
required extension are tested. Unsupported-special extensions are not assumed
legal merely because an entry point exists. Varying mismatch is a real linker
negative, not a compile-only assertion. Compute/barrier fixtures establish
language acceptance, not synchronization correctness at runtime.

Mesa:32/32 expected compiler+driver outcomes. ANGLE:32 compiler outcomes,28
expected driver outcomes and4 explicit NOT_SUPPORTED_GLES32 records. ANGLE's
created context does not support3.2, so geometry/tessellation are never falsely
marked runtime-tested. Overall ANGLE result isPARTIAL and CLI exits nonzero;
Mesa isHOST_PASS. This does not claim all language features/extensions tested.
No model/provider/device performance evidence is produced.

Run with a trusted installed compiler and existing driver config:

```
python3 tools/coverage/verify_glsl.py --config DRIVER_JSON --output REPORT_JSON
python3 -m unittest discover -s benchmarks/coverage/glsl -v
```

Optional omission of config executes compiler only and clearly reports runtime
NOT_RUN. Reports contain source hashes/results, no raw environment identities or
compiler paths. Fixture/input mutation is caught by source-hash tests. Remaining
scope: broader literal/overload/precision edge domains, special extension legal
paths, compiler-fuzz/CTS differential breadth and physical3.2 platform execution.

CI can explicitly use `--require-contract-only` for the ANGLE run. The persisted
report remainsPARTIAL. This mode accepts only the exact geometry/tessellation
four-row unsupported set when the actual context capability query is below3.2;
all other unexpected compiler/link results, wrong identities, stale source hashes
or fake unsupported families fail. It is not equivalent to ignoring CLI errors.
Mesa uses default full-pass mode. Eleven fixture/evidence/contract tests include
fake unsupported and false3.2 capability negative controls.
