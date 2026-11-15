# Real upstream GLES3 CTS subset (not certification)

Source: https://github.com/KhronosGroup/VK-GL-CTS at
`5bb4c7e83acea0fc73e3333625e4f20542e584d0`.
The upstream checkout retains LICENSE/NOTICE. No upstream source, registry XML,
executables or dependencies are vendored here.

## Reproduction

1. Check out the exact revision, retain its licenses, then run its official
   `python3 external/fetch_sources.py` (pinned dependencies in that revision).
2. Provide CMake >=3.24, C/C++ compiler, make, EGL/GLES headers and libraries.
   Set `CMAKE_PREFIX_PATH` and `PKG_CONFIG_PATH` for a non-system graphics SDK.
   Do not put unrelated old SPIRV headers into that graphics prefix: upstream's
   global include order can shadow the pinned dependency's public headers.
3. Run `python3 tools/coverage/cts_build.py --source CTS_SOURCE --build CTS_BUILD`.
   It validates the revision, requires 2 GiB free reserve, limits parallelism,
   and builds only the actual `deqp-gles3` target without changing CTS sources.
4. Enumerate actual paths from the built executable before executing the selected
   `dEQP-GLES3.functional.fbo.completeness.*` subset. Freeze those expected paths.
   A QPA parser fixture is not execution evidence.

The build helper does not upload anything or accept a certification claim.
Raw local build/environment output stays private. Any published QPA must remove
session-level host metadata explicitly and retain complete case results without
rewriting statuses; its hash must refer to the published redacted artifact, not
pretend to be the original log hash. Only independently enumerated cases may
count in the denominator. Software CTS does not complete Android/physical GPU,
thermal/bandwidth or Khronos conformance certification gates.

## Observed result

Mesa software host: **578 / 578 Pass**, execution exit 0. The expected set was
frozen from the same executable's `txt-caselist` before execution. This is a
finite FBO completeness result, not all GLES CTS and not certification.

ANGLE using this upstream surfaceless/default Vulkan display route failed
initialization before enumeration (`EGL_NOT_INITIALIZED`, Vulkan error -3).
Zero cases executed; see `evidence/angle/blocked.json`. Existing explicit-display
ANGLE benchmark results cannot replace this missing CTS run.

The build actually completed using upstream's fixed dependency manifest and an
isolated graphics SDK. Failed setup attempts were resolved: `/tmp` capacity by
using the same environment's workspace storage; CMake library discovery by a
graphics prefix; old unrelated SPIRV include shadowing by an EGL/GLES-only prefix;
missing `KHR/khrplatform.h` by the existing official SDK header. No CTS source
patches were needed. No raw host manifest or build console is published.

Build invocation also requires `--receipt BUILD_RECEIPT.json`. To execute:

```sh
python3 benchmarks/coverage/cts-real/run.py \
  --executable CTS_BUILD/modules/gles3/deqp-gles3 \
  --build-receipt BUILD_RECEIPT.json \
  --private-dir PRIVATE_LOG_DIRECTORY --output-dir RESULT_DIRECTORY
```

`build-receipt.json` binds source HEAD, clean tracked tree, observed dependency
revisions, configure/build exit 0 and executable content hash. The executable
hash identifies the tested artifact, not a portable compiler or device claim.
The runner checks this receipt before running. Case-only QPA is deterministically
gzipped; `gzip -dc evidence/mesa/cases.qpa.gz` restores complete case blocks.
The raw-QPA hash in report refers to these **redacted case-only bytes**, not the
unpublished original session. Original case duration fields are retained without
any timing/performance interpretation.

CI archive check (does **not** rebuild or rerun CTS):

```sh
python3 -m unittest discover -s benchmarks/coverage/cts-real -p 'test_*.py'
```

Six tests cover revision/dirty-source guards, case preservation/truncation and
archive integrity (578 enumerated cases, recomputed statuses, source/helper/runner/
receipt/expected/gzip and decompressed hashes). Future live execution requires
building the executable and providing its matching receipt; source strings
alone are not proof of a run.
