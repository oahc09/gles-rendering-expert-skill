# Shared texture → EGLImage → external sampler

```sh
python3 benchmarks/coverage/external-image/run.py --config DRIVER.json --output REPORT.json
python3 benchmarks/coverage/external-image/run.py --config DRIVER.json --output DISABLED.json --disable-external
python3 -m unittest discover -s benchmarks/coverage/external-image -p 'test_*.py' -v
```

W4 finite actual GLES3/ESSL3 contract. Both Mesa and ANGLE software hosts advertised the required five extensions; actual KHR image creation, OES image binding and shader compile/link succeeded. Non-symmetric 4×4 RGBA8 source uses R=17+31x+7y, G=23+11x+43y, B=31+19x+13y, A=97+17x+23y. Independent CPU expected bytes are compared exactly for sampler2D fallback, external sampling before image destruction, and existing external sibling after destruction: all three readbacks error0 on both hosts. Each normal run executes 3 draws/3 full readbacks; each disabled run 1 draw/1 full readback. Four CLI runs exited0 and 8 tests passed.

Creation uses EGL_GL_TEXTURE_2D_KHR, level0, current source context and EGL_IMAGE_PRESERVED_KHR=true; glFinish before import provides conservative same-context completion, not a nonblocking synchronization solution. No EGL source or sampled external texture is simultaneously a render attachment. External sampling uses ESSL3 require directive, nearest/clamp, and pbuffer output. eglDestroyImageKHR removes the image handle but leaves already-created sibling storage usable. No further API is called with the destroyed handle. Textures/programs/VAO are deleted before context teardown.

Mipmap min filter and GenerateMipmap external both correctly return INVALID_ENUM. Repeat wrap depends on **EXT_EGL_image_external_wrap_modes**, which ANGLE advertises: it is legal there, INVALID_ENUM under base OES restrictions on Mesa. Restore clamp before final sample. The initial run incorrectly expected repeat rejection universally; original source and actual ANGLE FAIL are retained in initial-attempt, not relabeled. Fixed official EXT text was read before correcting the capability-dependent oracle.

Forced disabled path performs actual sampler2D fallback with zero external-image calls. It is not evidence unsupported hardware exists; unsupported capability uses same branch but both current hosts support all prerequisites. Advertised entrypoint or actual creation/compile failure fails closed rather than silently relabeling fallback success.

Scope exclusions: no AHardwareBuffer/native camera import, YUV conversion, protected content, multisample source, shared-context producer/consumer synchronization, mutation/orphan behavior, external sampler arrays, physical hardware or performance measurements. Pixel identity here is a finite normalized RGBA source result, not a guarantee for all native external formats. No full specification text redistributed; pinned sources/hashes in sources.json. No private driver strings/paths are archived. Hashes bind source drift, not third-party execution authentication.

The varying-alpha asymmetric oracle explicitly rejects combined transpose+R/G swap and forced-opaque corruption. These CPU oracle-negative controls are not injected GPU corruption. Requiring GL_OES_EGL_image in addition to external extensions is a conservative five-extension experiment domain, not the external specification’s minimal dependencies.
