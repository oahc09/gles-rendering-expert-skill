# Device Capability & Regression Lab

The existing EGL harness is reused for actual correctness. `probe.cpp` additionally queries GLSL, fragment precision ranges, UBO alignment, binary-format count, sample limits, exact extension tokens/function pointers and actual RGBA8/RGBA16F framebuffer completeness. Availability of a pointer alone **does not enable** an extension or AHardwareBuffer import. Import/display probes unavailable here remain null.

```sh
GLES_SDK_ROOT=/path/to/extracted/usr python benchmarks/device_lab/lab.py --platform host --backend software --adapter '["python3","benchmarks/device_lab/host_adapter.py"]' --output /tmp/new-software-capture --repeat 2
python benchmarks/device_lab/lab.py --platform Android --backend native --output /tmp/new-device-blocked
python benchmarks/device_lab/compare.py native/0.json angle/0.json --output comparison.json
python -m unittest discover -s benchmarks/device_lab -p 'test_*.py' -v
```

The supplied adapter creates **host software** EGL only; its result is SOFTWARE_CORRECTNESS_ONLY. The second command exits 3 / BLOCKED_BY_HARDWARE. Android, Windows ANGLE and EmbeddedLinux GBM operators implement the same JSON stdin request/stdout capture contract shown in `host_adapter.py`; no setting/device is modified by the lab itself. Adapter commands are explicit argv arrays, never shell-interpolated. Failed compilation/crashes/empty correctness events are failures, not skipped PASS. Capture directories must be new; stdout/stderr and repeated fingerprints are retained. Backend identity comes from controlled creation or implementation query, never renderer substring feature inference.

## Native vs ANGLE protocol (not executed on a device here)

1. Obtain permission for the selected physical device/package and save current ANGLE settings. Follow [official ANGLE Android setup](https://github.com/google/angle/blob/main/doc/DevSetupAndroid.md) for its Android version, package and installed driver. Do not apply global developer settings to all apps.
2. Run the same build/seed/scene/size/refresh configuration under native and explicitly selected ANGLE Vulkan, at least twice per backend. Record setting/creation evidence, GL/EGL strings, driver fingerprint and crash logs. Restore the saved package settings afterwards, including failure cleanup.
3. Exercise launch, surface resize/recreation, foreground/background, controlled context rebuild, FBO/MSAA, sRGB, binary restore, external-image/fence paths and cross-context visibility. Mark absent HDR/AHB hardware as NOT_RUN, not false or unsupported without a probe.
4. Compare visual golden with declared tolerances, correctness event IDs and capability differences. Thermal/power-controlled performance remains in `benchmarks/gpu/capture.py` and actual scene runner; a snapshot does not prove speedup.
5. Never silently label software/other-backend fallback as native/ANGLE. Log actual fallback and rerun compatibility decisions. `compare.py` never awards full acceptance automatically, even for an operator-declared physical pair.

[Android Vulkan/ANGLE policy](https://developer.android.com/games/develop/vulkan/overview) is historical platform context, not a new GLES feature. Windows-on-Arm does not identify a GPU vendor. Embedded Linux needs an actual GBM/surface adapter and its driver/DRM permissions; a host pbuffer is not that test.
