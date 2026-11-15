# Representative scenario coverage

No claim that every algorithm is required for API index completeness. Partial and DEPENDENCY rows remain explicit gaps.

| Category | Status | Actual scope |
|---|---|---|
| 2D UI / SDF | SOFTWARE_RUNTIME_WITH_FALLBACK | Authored rectangle SDF/MSDF decoder at two sizes; Mesa SDF32 exceeds fixed budget and uses actually sampled alpha fallback. Not full glyph generation/layout. |
| 3D PBR / Forward+ | PARTIAL | Finite forwardplus engineering shader, not full production PBR |
| Shadows / water | PARTIAL | Bounded shadowwater reference; no full fluid simulation |
| Postprocessing | SOFTWARE_RUNTIME | Three-stage CPU image oracle |
| HDR | PARTIAL | Software transfer math only; physical WCG/HDR calibration blocked |
| Transparency / OIT | SOFTWARE_RUNTIME_WITH_REJECTED_CANDIDATE | Weighted two-pass accum/reveal + resolve matches half-float CPU oracle, but both scenes exceed sorted-alpha quality budget; approximation rejected, sorted baseline selected. |
| Particles | SOFTWARE_RUNTIME | Finite actual draw controls; no million-particle claim |
| Fluid / sand | PARTIAL | Bounded simulation, not all fluid algorithms |
| Glass / refraction | PARTIAL | Layered Snell proxy, not recursive optical transport |
| Compute | SOFTWARE_RUNTIME | Bounded SSBO/image controls; ES3.0 CPU alternative needed per workload |
| Animation / skinning | SOFTWARE_RUNTIME | Two translation poses, two-bone std140 UBO, four normalized influences: actual transform feedback and exact RGBA8 goldens vs CPU VBO fallback; wrong matrix/weights/stall rejected. Not full skeletal animation. |
| 3DGS high overlap | PARTIAL | Authored covariance splats; original high-layer failures inherited |
| Texture streaming | SOFTWARE_RUNTIME | Actual KTX transcode/cache/budget/upload readback |
| Video fusion | BLOCKED_BY_HARDWARE | Android/AHB build/install and external media device evidence absent |
| Multiview | SOFTWARE_RUNTIME | One draw writes two array layers, actual readback on Mesa/ANGLE with blue sentinel; sequential fallback and four specified API negatives. Not multiview device acceptance. |
