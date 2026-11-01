# Structured GLES rule contracts

`python tools/validate_rules.py --output reports/rules.json`

30 rules / 112 distinct positive and negative inputs. These tests exercise an explicit
**normalized-facts decision layer**, not a C++ parser or shader compiler. A passing
case means the predicate matched its annotated expectation; it does not establish
source-code correctness, driver conformance, or model quality. Actual compilation
and software-renderer tests are in `examples/validation/`; Agent tests are separate.

## Scope and schema

`catalog.json` maps each rule to version, extension, platform/vendor assumptions,
severity, normative source, positive/negative case IDs, fallback and source file.
`cases.json` gives normalized input and independently annotated expected decision.
Each predicate checks only its stated condition. For example R003 checks the chosen
RGBA8/UNSIGNED_BYTE upload path, not the entire GLES texture format table; R016
checks named color attachment indices against the supplied limit;
R023 contrasts two actual window events with invented context-loss commands, not
an exhaustive native_app_glue command parser. Other API preconditions still apply.

MUST means API/defined-behavior requirement **within that rule's scoped operation**.
CONDITIONAL warns against an unsupported performance conclusion, not an illegal GL
call. R009 describes the demonstrated asynchronous fence protocol, not a ban on
correct alternative CPU-blocking synchronization. R022 is the recovery policy for
the two modeled EGL errors, not all possible EGL error handling.

To add a rule: give a primary source, explicit input fields, at least one legal and
one illegal/counterexample case, then implement its predicate. The runner rejects
duplicate IDs/inputs, missing mappings and missing fields. Do not count copied
cases toward coverage. Update actual compile/runtime fixtures when the claim is
about code or driver behavior, and record unsupported platforms separately.
