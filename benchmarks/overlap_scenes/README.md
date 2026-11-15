# v1.0.9 W4 overlap controls (PARTIAL)

`../shader_ab/run.py` supplies four executable GLES scene proxies: Gaussian/sprite overlap (32 layers), glass (8), rain/particles (16), layered UI (12). All cover a 4×4 target using actual separate draw calls and source-alpha RGB/separate alpha blending. This finite control intentionally isolates ordering/alpha from geometry. Independent CPU compositing quantizes after every layer; Mesa maximum RGBA8 discrepancies were 0/0/1/1. Reversed layer order is an actual negative image control and fails all four comparisons.

These **are not Gaussian splat projection, glass refraction, volumetrics or production scene reproductions**. Uniform full-screen coverage means the heat map is constant: each of 16 pixels has N layers, giving 16*N analytical fragment coverage. This is geometry-estimated coverage, not measured GPU overdraw or DRAM traffic. Draw reduction does not imply pixel coverage reduction.

Replay using the shader_ab README command. `shader_ab/evidence/mesa.json` contains images (raw RGBA8 arrays), CPU error and source hashes for both ordering arms. Dynamic camera, silhouette, parallax, background LOD/merging and perceptual error budgets remain NOT_RUN. W4 remains partial until those tests and realistic geometry exist.
