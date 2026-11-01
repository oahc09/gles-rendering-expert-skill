# Precision/color visual lab (W3 + W6)

This extends, rather than replaces, v1.0.4: `precision_lab.cpp` includes the existing scene source with its entry renamed, reusing Context, Target, shader/program and render-pass helpers. The comparator imports the existing strict P6 decoder. Existing eight scenes/goldens are untouched.

## Actual workloads

| ID | Reference | Injected fault |
|---|---|---|
| P01 | highp accumulation, large fixed clock | explicitly pack/unpack binary16 each addition |
| P02 | normalized normal, exponent-80 highlight | coarse normal quantization |
| P03 | animated water normal/highlight | quantized wave slope |
| P04 | smooth encoded gradient | eight-step banding |
| P05 | RGBA16F HDR then Reinhard + power encoding | clip instead of tonemap |
| P06 | eight real GL straight-alpha layers | ONE instead of SRC_ALPHA |
| P07 | actual SRGB8_ALPHA8 decode then shader sRGB encode | RGBA8 storage causes missing decode / double encoding |
| P08 | actual RGBA16F intermediate preserving >1 | actual RGBA8 intermediate clips HDR |

P05/P08 deliberately share a signal to isolate target format from tonemapping. They are not artistic scene variety claims. `mediump` mode independently measures qualifier changes for applicable generated shaders; fixed-function blend/format paths are unchanged controls, **not eight distinct mediump optimizations**. Numeric compute probe records highp, explicit binary16, mediump independently and compares the first two to Python binary32/binary16 oracles. Explicit packing measures a controlled loss of precision, not FP16 ALU performance.

## Reproduce

```sh
export GLES_SDK_ROOT=/tmp/gles-local-deps/root/usr
export LD_LIBRARY_PATH="$GLES_SDK_ROOT/lib/x86_64-linux-gnu"
export EGL_PLATFORM=surfaceless LIBGL_ALWAYS_SOFTWARE=1 MESA_SHADER_CACHE_DISABLE=true
examples/precision/run-host.sh P01 /tmp/P01.ppm 96 1 10000 baseline
python benchmarks/visual_quality/run.py --output /tmp/visual-check
python benchmarks/visual_quality/validate_shaders.py --glslang "$GLES_SDK_ROOT/bin/glslangValidator"
python -m unittest discover -s benchmarks/visual_quality -p 'test_*.py' -v
```

The CLI accepts `P01..P08 output.ppm output_size scale time_seconds mode`. Scale .25..1 resizes the actual intermediate FBO; final image size is unchanged. `run.py --scale .85 --scale .7` is the W2 policy interface; defaults match levels1/2. Report `policy_level_visual_approval[scene][level]` records **visual-only** approval; it cannot grant device/performance approval. Null means that scale was not tested. Level0 requires a matching reference baseline; callers must also inspect overall report PASS and source/config hashes.

Normal runs verify all frozen hashes and do not change references. `--accept-goldens` is an explicit initial/reviewed replacement, produces BASELINES_CREATED_NOT_VALIDATED, never PASS. Goldens are 24 actual captures (eight workloads x three fixed timestamps). Manifest records source/helper hash, renderer/version, time/seed, size, color contract and image hashes. Capture format P6 RGB8 is uncompressed, top-to-bottom; HDR signals are deliberately tonemapped to SDR, with no display color management or WCG certification.

## Metrics and interpretation

- Three scales (1,2,4) use box downsampling, RGB mean absolute error and local 8x8 SSIM on encoded Rec.709-weighted luma. Constants C1=6.5025, C2=58.5225; population covariance. This is an explicitly defined engineering SSIM variant, not a perceptual ΔE or HDR nits metric.
- Reference-derived masks: edge gradient >8 encoded luma; shadow <80; glow >190; P06 transparent central disk radius .4 normalized. Empty mask is NOT_APPLICABLE, not a zero-error pass. Each mask has independent MAE/channel-outlier/max-error limits.
- Heatmap maps maximum channel error x4 to red, exact match blue. Temporal metric compares consecutive-frame RGB deltas against reference deltas. Alternating injected fault at the middle timestamp must be detected separately from constant bias.
- All eight static faults must be detected. Candidate mediump/scale paths may be rejected; a successful regression harness means detection works, not that all optimization candidates are acceptable.
- Pareto records p95 time, power, memory and thermals as unknown when unmeasured. No FPS/power claims are made from host correctness runs. Numeric and visual gates cannot stand in for physical-device performance.

`software-validation.json` is actual host evidence; `shader-validation.json` validates exact dumped runtime shaders with glslang and retains each stage's exit/diagnostics. Actual GLES execution also compiles/links each used program. `infrastructure-tests.log` covers deliberate comparator faults, separate from rendering. Review `golden` contact sheet visually before accepting an intentional change; test hashes do not prove artistic correctness.

Limitations: only this software-driver reference was run; no vendor golden cross-certification, physical-device performance, HDR display output, WCG, or long-duration thermals. Three deterministic snapshots do not claim long-running simulation stability. Thresholds are conservative lab policy, not universal industry standards.
