# Build / runtime / target matrix

| Target | Build | Runtime | Evidence / gap |
|---|---|---|---|
| Linux software EGL | Actual C++17 compile | 48 new GL interactions executed | state-machine/evidence.json; no target performance |
| Linux ANGLE software | Separate shader/EGL probes | Pending current probe report | Never relabel as Windows x64/ARM64 |
| Android Java+JNI arm64 | BLOCKED_BY_TOOLCHAIN | NOT_RUN | Existing examples/system_android needs Gradle, Android35, NDK27 and CMake3.22.1; preflight lists actual missing tools |
| Windows ANGLE x64/ARM64 | NOT_RUN | BLOCKED_BY_HARDWARE | No Windows target/compiler execution evidence |
| Embedded GBM/Wayland/X11 | NOT_RUN | BLOCKED_BY_HARDWARE | Surfaceless software host does not validate these window-system targets |
| Mali / Adreno / PowerVR | NOT_RUN | BLOCKED_BY_HARDWARE | No target installation, thermal trace or before/after counters |
| CTS subset | NOT_RUN | NOT_RUN | Requested pattern and expected-list protocol in benchmarks/coverage/platforms/cts-config.json; parser tests are synthetic fixtures only |

`tools/coverage/platform_preflight.py --build-android --output REPORT` checks required pinned project toolchain and runs the existing Gradle project only when available. It never silently installs/accepts licenses, changes credentials or claims an APK from a config file. Missing SDK is a local build dependency, distinct from unavailable physical hardware.

For CTS: use a licensed pinned checkout, enumerate exact cases from that build, freeze the expected list, capture complete QPA and process exit status, then run `cts_results.py`. Missing/truncated/unknown/extra cases are not PASS; warnings and unsupported cases are not successes. No certification claim is made.
