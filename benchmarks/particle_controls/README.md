# S04 compute → particle draw controls

```sh
python3 -m unittest discover -s benchmarks/particle_controls -v
python3 benchmarks/particle_controls/run.py --config DRIVER_JSON --output REPORT_JSON
```

This finite GLES 3.1 pipeline dispatches four compute invocations that write four vec4 particle records to an std430 SSBO. A vertex shader consumes that same SSBO directly and draws four 3×3 point sprites into a 32×32 RGBA8 target. Position depends on frame 0, 1 or 2. The CPU independently generates expected binary-exact positions and colored square coverage at pixel centres.

After dispatch, the harness issues **GL_SHADER_STORAGE_BARRIER_BIT** for the vertex shader SSBO consumer and **GL_BUFFER_UPDATE_BARRIER_BIT** for subsequent CPU mapping. No test intentionally removes a barrier, submits invalid indices, races a writer or relies on undefined behavior. A missing-barrier run that happens to look correct would not be valid evidence.

Two deterministic negatives per frame use valid programs and resources: compute the wrong frame's positions, or draw all vertices using record zero rather than their own index. The wrong-frame buffer must differ from the requested-frame golden; the wrong-index buffer remains correct while rendered image fails. All access remains inside the four-record allocation.

## Actual results

Mesa and ANGLE each completed 9 compute dispatches, 9 draw calls, 9 RGBA8 image readbacks and 9 SSBO mappings. Three positive image outputs match the CPU golden exactly; six negative outputs are rejected. Correct-frame SSBO values match exactly, while all wrong-frame controls differ as intended. Both implementations report HOST_PASS. Fifteen unit tests passed. `evidence/mesa.json` and `evidence/angle.json` retain complete actual pixels, SSBO floats and CPU image goldens with shader source hashes, but no machine metadata.

A driver lacking GLES 3.1 compute or a vertex SSBO slot reports UNSUPPORTED, not pass. The tested draw count is four particles and three fixed frames. This is not a throughput benchmark, complete particle simulator, indirect-draw/transform-feedback validation, CPU/GPU asynchronous synchronization test, or proof of all barrier paths. Physical-device performance/power, timing and lifecycle recovery remain unmeasured. These controls do not waive inherited device gates.
