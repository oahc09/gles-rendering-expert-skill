# Representative scenario coverage

No claim that every algorithm is required for API index completeness. Partial and DEPENDENCY rows remain explicit gaps.

| Category | Status | Actual scope |
|---|---|---|
| 2D UI / SDF | PARTIAL | Finite alpha UI integrated pipeline; SDF/MSDF representative not executed |
| 3D PBR / Forward+ | PARTIAL | Finite forwardplus engineering shader, not full production PBR |
| Shadows / water | PARTIAL | Bounded shadowwater reference; no full fluid simulation |
| Postprocessing | SOFTWARE_RUNTIME | Three-stage CPU image oracle |
| HDR | PARTIAL | Software transfer math only; physical WCG/HDR calibration blocked |
| Transparency / OIT | PARTIAL | Ordered alpha and failures preserved; full OIT representative absent |
| Particles | SOFTWARE_RUNTIME | Finite actual draw controls; no million-particle claim |
| Fluid / sand | PARTIAL | Bounded simulation, not all fluid algorithms |
| Glass / refraction | PARTIAL | Layered Snell proxy, not recursive optical transport |
| Compute | SOFTWARE_RUNTIME | Bounded SSBO/image controls; ES3.0 CPU alternative needed per workload |
| Animation / skinning | SOFTWARE_RUNTIME | Two translation poses, actual UBO skinning/TF/image oracle and CPU VBO fallback; not full skeletal animation |
| 3DGS high overlap | PARTIAL | Authored covariance splats; original high-layer failures inherited |
| Texture streaming | SOFTWARE_RUNTIME | Actual KTX transcode/cache/budget/upload readback |
| Video fusion | BLOCKED_BY_HARDWARE | Android/AHB build/install and external media device evidence absent |
| Multiview | SOFTWARE_RUNTIME | Two-layer actual draw/readback and sequential fallback on both software hosts; no device acceptance |
