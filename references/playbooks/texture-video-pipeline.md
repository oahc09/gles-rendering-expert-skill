# W7: one Basis resource, explicit runtime formats and video boundaries

## Implemented texture path

`examples/texture_pipeline/transcode.cpp` loads KTX2 through official libktx,
checks topology, requires an **LDR UASTC RGB/RGBA** Basis payload, and actually calls
`ktxTexture2_TranscodeBasis`. A container is not a GPU format. Target policy:

1. Exact `GL_KHR_texture_compression_astc_ldr` token → ASTC 4x4 RGBA.
2. GLES >=3 → ETC2 RGBA8 (core GLES 3.0 format), unless explicitly denied by a
   separately reviewed compatibility decision.
3. Otherwise RGBA8 fallback; if every path is denied, stop. Corrupt input or failed
   transcode must not be uploaded. Do not pick by phone brand/vendor label.

`load_texture.py` combines this policy with an explicit DeviceLab snapshot and
invokes the compiled runtime. The owned GL context must still perform upload/error
checking; `sample.cpp` demonstrates actual libktx GL upload, nearest sampling into
RGBA8 and readback for the **unprotected synthetic fixture only**. It reuses the
existing EGL harness. Desktop software support is not mobile format coverage.

The example intentionally accepts GLES major 2 or 3 only, exact string extension
tokens and enumerated deny targets. Its file budget is 16 MiB; image extents must
be 1..2048 per axis. It accepts UASTC LDR with linear/sRGB transfer only, three or
four source components; ETC1S, HDR/PQ/HLG, other DFD models and grayscale/RG are
rejected rather than silently interpreted as RGBA8. It checks actual output
VkFormat, block payload size, decoded RGBA8 component size, offset and data length
before writing raw pixels. Negative tests include mutated HDR/topology metadata
and a real encoded synthetic grayscale resource. No real HDR capture is claimed.

The example accepts one 2D image/one mip; arrays/cubemaps/streaming
mips and arbitrary orientation metadata are rejected or outside this fixture.
Production asset ingestion must validate dimensions, DFD transfer function,
orientation, levels and allocation budget before selecting a matching sized GL
format. Do not confuse sRGB encoding with linear-light ALU or use the sample's
linear test pixels to certify an sRGB asset pipeline.

```sh
python benchmarks/texture_pipeline/run.py --ktx-root /path/to/KTX-Software \
  --gles-sdk /path/to/extracted/usr --output /tmp/texture-evidence
python -m unittest discover -s benchmarks/texture_pipeline -p 'test_*.py' -v
```

The external KTX runtime/tool is not vendored. `tool-receipt.json` records official
asset digest verification; v4.4.2 was published **2025-10-04**, historical rather
than a new October 2026 feature. The input is an original deterministic 32x32
linear gradient encoded UASTC. Reports include actual payload bytes, host load and
transcode wall time, process peak RSS, CPU ASTC decode quality and software GL
readback errors for ASTC/ETC2/RGBA. RSS includes library/decode overhead and is not
isolated allocation; payload bytes are not actual driver VRAM. One host timing is
not a mobile speed/power claim. No codec binary or copyrighted media is shipped.

## External video vs explicit YUV planes

Reuse `examples/android_cases/surfacevideo/.../ExternalSurfaceActivity.java`:
it already owns SurfaceTexture update/acquire, external texture clamp/linear
parameters and the producer transform. The same package's `VideoInputGuard.java`
is now **wired into that Activity**: capability selection precedes consumer
creation; frame acquisition applies its checked producer/extra-rotation transform.
The current Canvas source declares RGB/full/SDR, never pretending to be YUV.
A protected intent request exits before either producer or AHB setup. Future
camera/codec sources must pass their actual metadata, not copy those Canvas
constants. All SurfaceVideo Java sources compile against API35; real video
playback, APK deployment and display validation remain **NOT_RUN** here.

* ESSL300 `samplerExternalOES` requires both external OES and essl3 extension
  tokens. Missing token → stop/visible placeholder, never an illegal shader.
* External sampler returns converted RGB; do **not** apply a manual YUV matrix
  again. Producer dataspace/matrix/range must be known and independently checked.
* For accessible, unprotected **8-bit planar** CPU data only, `yuv_planes.frag`
  implements explicit BT.601/709/2020 coefficients and full/limited code ranges.
  Output is nonlinear SDR RGB; linearize before lighting/blending where required.
  Plane stride/subsampling/chroma siting must be resolved by the caller. P010,
  HDR/PQ/HLG are not supported by this example and explicitly blocked by policy.
* Always refresh SurfaceTexture's producer matrix after acquiring the image.
  Additional rotation is allowed only when not already baked into that transform;
  otherwise reject to prevent double rotation/crop. No Android runtime claim is
  made from a Java compile or Python coordinate test.

## Protected content: fail closed

`video_path`/`VideoInputGuard.select` **reject all protected inputs** because a
trusted protected producer/context/surface/import/output chain is not implemented.
They never offer CPU staging/readback/plaintext export as a fallback. The separate
`protectedContextAndSurface` EGL query is diagnostic, not permission to consume or
read content; texture/image protection and the system's DRM trust requirements
remain additional checks. Even extension presence does not certify DRM support.

Official references:
[KTX](https://github.com/KhronosGroup/KTX-Software),
[external OES](https://registry.khronos.org/OpenGL/extensions/OES/OES_EGL_image_external.txt),
[EGL protected content](https://registry.khronos.org/EGL/extensions/EXT/EGL_EXT_protected_content.txt),
[GL protected textures](https://registry.khronos.org/OpenGL/extensions/EXT/EXT_protected_textures.txt),
[SurfaceTexture](https://developer.android.com/reference/android/graphics/SurfaceTexture).
