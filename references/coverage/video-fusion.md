# W7 finite video-plane fusion representative

The video matrix entry formerly had only Android/AHB dependencies and a compiled YUV plane shader. `benchmarks/coverage/video-fusion` supplies an explicit GLES3 CPU-authored NV12 plane path, actual RGBA shader fusion and independently calculated CPU oracle, without replacing the native-video blocker.

Numerical contract: BT709 Kr=.2126, Kb=.0722, limited 8-bit Y=(code−16)/219 and C=(code−128)/224. Expanded inverse coefficients are checked against endpoint and actual image tests. [ITU-R BT.709](https://www.itu.int/rec/R-REC-BT.709) is the primary colorimetry reference; [GLES3 specification](https://registry.khronos.org/OpenGL/specs/es/3.0/es_spec_3.0.pdf) defines normalized R8/RG8 sampling/pixel upload. This representative does not implement general multimedia color management: nonlinear-domain UI blending and nearest-block chroma replication are explicit design limitations.

Two actual wrong-metadata shader variants are rejected by unchanged2byte oracle threshold. Metadata/stride rejection tests are preflight, not hardware API error evidence. No physical/mobile bandwidth, native external sampler import, decoder, camera, Android installation or protected-content claim is made.
