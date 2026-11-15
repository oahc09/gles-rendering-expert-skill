# Advanced GLES mechanism controls

```
python3 benchmarks/shader_ab/advanced.py --config DRIVER_JSON --output REPORT_JSON
python3 -m unittest discover -s benchmarks/shader_ab -p test_advanced.py
```

The runner reuses `differential.Host`, compiles/links actual shaders, creates RGBA8 + depth attachments, issues real draws and reads 4×4 RGBA8 pixels. It never exports Host metadata. Source hashes, diagnostic logs and pixels are the evidence; performance remains NOT_MEASURED.

Six baselines and six deterministic wrong variants:

- GLES 3.0 constant reference versus std140 UBO component access.
- GLES 3.1 std430 SSBO fragment reads versus the same constant reference.
- GLES 3.1 compute writes vec4 to SSBO, GL_SHADER_STORAGE_BARRIER_BIT, fragment reads and draw, versus reference. Wrong channel selection is an actual failing output control.
- Fragment discard preserves the cleared left half; removing discard fails.
- Depth LESS against cleared depth 0.25 rejects fragments at 0.5; disabling depth fails.
- Constant shader wrong-channel output control.

A missing compute→fragment barrier is explicitly rejected as unsafe, not executed or claimed to produce a deterministic image failure. Undefined visibility can appear correct on software/hardware and therefore cannot be a reliable negative image oracle.

Local run: six baseline PASS, six wrong-output FAIL, zero GL errors; 9 infrastructure unit tests PASS. This is finite software-host correctness, not device speed, register/traffic savings or a general shader-equivalence proof. Actual GLES 3.1 unavailable is reported SKIP_UNSUPPORTED and the overall run is not HOST_PASS. Each driver should run in a separate process. Physical/mobile and cross-vendor performance remain unmeasured.
