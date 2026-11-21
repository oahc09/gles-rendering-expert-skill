# Android arm64 APK build investigation

Current result: **BLOCKED_BY_LICENSE_AND_MISSING_SDK**, not merely missing hardware.

- Official Google repository metadata, add-on metadata and AGP8.7.3 POM returned HTTP200 in `source-probes.json`. An older AGP-resolution failure does not establish the current network state.
- Official Gradle8.9 binary was downloaded, matched its officially published SHA256, extracted within the current workspace, and `gradle --version` exited0. `gradle.json` records the source and result. Gradle distribution is not vendored.
- `source-plan.json` freezes selected SDK35 revision2, NDK27.0.12077973, build-tools35.0.0, CMake3.22.1 and stable platform-tools metadata URLs/sizes/published SHA1. These are metadata observations, not verified downloaded archives. Google metadata SHA256 pins the actual source used.
- All selected packages reference `android-sdk-license`. The retrieved terms expressly identify a Google SDK agreement. No established acceptance was found in the selected local SDK configuration; no license acceptance, license-hash insertion, SDK package download or installation was performed. See [official terms](https://developer.android.com/studio/terms). License authorization must be resolved before provisioning and using these packages. This is not a claim the licensing forbids the user's intended work.
- `/tmp` free capacity was smaller than the NDK archive. The same execution environment's workspace has enough space; changing environments is unnecessary. No security, credential or proxy settings were changed.

## Guarded executable build

`tools/coverage/android_build.py` accepts explicit existing SDK and Gradle locations. It does not download packages, run sdkmanager, accept agreements or install to a device. It checks exact declared platform/NDK/CMake/build-tools paths; Gradle automatic SDK downloads are disabled. Actual build requires `--execute` and all prerequisites. Only exit0 and a resulting ZIP containing classes.dex, manifest and arm64 JNI library can establish APK build PASS; install/runtime remain NOT_RUN.

```sh
python3 tools/coverage/android_build.py --sdk /approved/preprovisioned/sdk --gradle /official/gradle-8.9/bin/gradle --output /tmp/android-build-result --execute
python3 -m unittest discover -s benchmarks/coverage/android-build -p 'test_*.py' -v
```

The actual local gate invocation exited2 with `evidence/report.json`: Java and newly installed Gradle present, SDK35/NDK27/CMake3.22.1/build-tools35 absent, no APK. Five tests passed (missing SDK never builds, log path sanitization, no implicit installation/acceptance, nonempty and internally consistent archived JSON). These tests are infrastructure checks, not Java/JNI build or target acceptance.

After authorized SDK provisioning, the command above must actually compile, package and verify output; additional Gradle plugin/transitive dependency failures remain possible despite a reachable POM. Then physical `adb install` and Activity/native execution are separate still-NOT_RUN W9 requirements. No simulator is used as device or bandwidth proof.

Archive correction: `source-probes.json` was discovered empty and restored from the earlier actual tool output, not a new network check. Its provenance explicitly records this recovery; observation timestamp remains unknown. Writes use a validated temporary JSON followed by replacement. Archive tests reject empty/malformed reports and mismatched Gradle checksum metadata.
