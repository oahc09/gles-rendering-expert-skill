# Texture/video pipeline source

See [implementation contract, limits and reproduction](../../references/playbooks/texture-video-pipeline.md).
All source here is original MIT. libktx is an externally installed Apache-2.0
runtime; no third-party binary is committed. The generated gradient evidence is
original synthetic data, not captured customer video.

## Odd-sized 8-bit planar preview

`yuv_planes.frag` converts explicit 8-bit Y/U/V textures to nonlinear SDR RGB.
For untransformed image coordinates and a producer whose 4:2:0 format assigns
one U/V texel to each source-origin-aligned 2×2 luma block, set
`blockAligned420=true`. Bind complete level-zero `GL_R8` textures, with U and V
each sized `ceil(luma_width/2) × ceil(luma_height/2)`. The shader uses source
integer texel coordinates; an odd terminal row or column uses the last block
rather than moving the penultimate pixel into it. Validate the dimensions and
sampling policy before opting in; this is not a general chroma-siting or
resampling rule. Existing callers keep normalized filtering by default.

For padded byte-addressable planes, use the validated byte stride as
`GL_UNPACK_ROW_LENGTH` in texels for `GL_R8` (one byte per texel) with unpack
alignment one, or repack to tight rows. Restore the caller's pixel-store state.
Supply explicit matrix coefficients and range from the source metadata. This
path does not accept external OES images, protected buffers, P010, or HDR.

Run the separate [software product case](../../benchmarks/product_smoke/odd_video.py)
with the existing trusted software EGL environment:

```sh
GALLIUM_DRIVER=llvmpipe python3 benchmarks/product_smoke/odd_video.py \
  examples/texture_pipeline/yuv_planes.frag /tmp/gles-video-mesa-new
GLES_ANGLE_ROOT=/path/to/trusted-angle-software-libs \
  python3 benchmarks/product_smoke/odd_video.py \
  examples/texture_pipeline/yuv_planes.frag /tmp/gles-video-angle-new
```

The test uses actual software GLSL execution and readback for all 15 pixels
of an odd 5×3 BT.709 limited-range fixture, includes different per-plane row
strides and pixel canaries, compares tight repack, and tests a simulated stale
host-generation guard over two recreated EGL contexts. It is not evidence of
actual concurrent video delivery, forced context loss, physical GLES,
presentation, zero-copy video, or Android interoperability.
