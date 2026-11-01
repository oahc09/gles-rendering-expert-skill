# Android source build evidence

Reproduce with a real JDK containing `javac` and Java 17 release symbols, an official
Android API 35 `android.jar`, and official Android NDK r27 (Linux x86-64 host):

```sh
python examples/android_cases/compile_sources.py \
  --jdk "$JAVA_HOME" \
  --android-jar "$ANDROID_SDK_ROOT/platforms/android-35/android.jar" \
  --ndk "$ANDROID_NDK_ROOT" \
  --output /tmp/gles-android-source-compile.json
```

The command performs Java `--release 17` compilation against the Android platform
API, strict C++17 arm64/API26 compilation and linking for the EGL harness and six
legacy examples, then invokes the AHB case's native shared-library cross-compile.
It records source/tool/output hashes, commands, logs and ELF headers. Temporary
class/ELF artifacts are removed; reports are retained. It never executes Android
binaries. Missing tools return **2 / BLOCKED_BY_TOOLCHAIN**, not success; actual
compile/link failures return **1**. `test_compile_sources.py` tests only those
infrastructure semantics, not target code correctness.

Android links GLES3 through `-lGLESv3`; the Linux host's `-lGLESv2` convention is
not interchangeable with NDK GLES3 linking. Initial host-style library selection
failed on actual NDK symbols; the final runner explicitly uses the correct target
library. Java deprecation diagnostics are retained and are not treated as runtime
failures. No stubs were generated to make compilation pass: the API jar is from
the official SDK archive, verified against Google's published repository checksum.

`source-compile.json` is **source compilation/link evidence only**. It is not APK
assembly, manifest/resource validation, device lifecycle testing, AHardwareBuffer
import/readback, native-fence timing, HDR/WCG visual validation, or Android GPU
performance evidence. Those gates remain separate.

`toolchain-provenance.json` records official downloads/checksums and the actual
Gradle assembly attempt outcome. All downloads, caches and build outputs stayed in
this existing execution environment, outside the repository. No SDK licence
acceptance file was created and no system packages were installed.
