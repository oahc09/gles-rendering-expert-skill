# Thermal, power and sustained frame stability

Use [LongRunCapture](../../benchmarks/longrun/README.md), keeping physical/device
telemetry distinct from synthetic fixture clocks and host software iteration time.
Temperature rise alone does not identify a GPU bottleneck; correlate thermal
status/frequency with stable workload, CPU submit, GPU work and independent
bandwidth counters, then perform a controlled A/B that can reject the hypothesis.
Power requires an actual source-identified instrument or platform measurement;
frequency/utilization cannot be converted into exact milliwatts or saving percent.

Android official boundaries:
- [Thermal API](https://developer.android.com/games/optimize/adpf/thermal): Java and
  NDK availability differ. Check OS/API and handle unavailable/NaN headroom rather
  than requiring private vendor counters. Respect query cadence and OS protection.
- [Performance Hint API](https://developer.android.com/reference/android/os/PerformanceHintManager):
  creates workload sessions where available; it is a scheduling hint, not a promise
  of frequency, private GPU counters or an application-controlled thermal override.
- [AChoreographer](https://developer.android.com/ndk/reference/group/choreographer):
  schedules frame callbacks; callback timing is not proof of compositor presentation.
- [Swappy](https://developer.android.com/games/sdk/frame-pacing): frame pacing and
  presentation synchronization are separate from thermal/headroom policy. Use its
  GLES integration for GLES, not Vulkan handles/API names pasted into GLES code.

Cold versus steady-state captures need matched device/driver/backend, power mode,
refresh, scene SHA, resolution and quality. Do not compare native and ANGLE records
as interchangeable. Real Mali/Adreno/PowerVR cold/steady 10/30-minute acceptance in
this candidate remains BLOCKED_BY_HARDWARE.
