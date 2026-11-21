# Bounded framebuffer-fetch fault diagnosis

Original `framebuffer-fetch` evidence is unchanged. This independent minimal
probe uses the existing working EGL Host but removes the texture sampler binding,
changes mutable allocation to immutable storage, narrows to one draw and uses
exact ctypes GLboolean bytes for `glColorMask`. It checks complete RGBA8 FBO,
compile/link and GL errors before the failing draw. No core dumps, driver changes,
system settings or SDK agreements are involved.

## Observed six processes

| Host | Attachment | Shader | Result |
|---|---|---|---|
| Mesa | texture | ordinary output | 16 pixel RGBA readback PASS |
| Mesa | texture | coherent fetch | signal 11; last checkpoint before draw |
| Mesa | renderbuffer | coherent fetch | signal 11; last checkpoint before draw |
| ANGLE | texture | ordinary output | 16 pixel RGBA readback PASS |
| ANGLE | texture | coherent fetch | 16 pixel RGBA readback PASS |
| ANGLE | renderbuffer | coherent fetch | 16 pixel RGBA readback PASS |

All pre-draw GL checks were zero and compile/link/FBO checks passed. Expected
one-step rotation from clear (.25,.5,.75,1) is [191,64,128,255], tolerance 1.
The observed failure is not specific to the earlier texture sampler binding,
GLboolean ABI declaration, multiple sequential draws or a texture-vs-renderbuffer
choice. This narrows suspicion to the installed Mesa fetch execution path; it
**does not prove a specific driver defect or exclude every application/platform
interaction**. No successful native fetch correction was found. Current safe
choice is the independently tested separate-source/destination ping-pong path in
`framebuffer-fetch`, or an independently verified implementation, not automatic
permission based on an extension string.

The ping-pong route requires a second RGBA8 attachment and explicit texture read:
for 4×4 that is 64 additional logical attachment bytes, not measured DRAM or GPU
speed. It retains two transform draws in the original two-step experiment.

## Official references and limits

- EXT_shader_framebuffer_fetch revision 8, 2018-09-06, pinned registry source:
  https://github.com/KhronosGroup/OpenGL-Registry/blob/1cdd228e34966dd6b95bd203e9f84faba0f371a1/extensions/EXT/EXT_shader_framebuffer_fetch.txt
- Official Mesa 26.0.4 notes list a color framebuffer-fetch fix:
  https://docs.mesa3d.org/relnotes/26.0.4.html
- Official 21.3.0 notes list an older fetch plus gl_FragDepth crash fix:
  https://docs.mesa3d.org/relnotes/21.3.0.html

The latter is not the same repro (our shader never writes depth). Neither note
proves the installed fault has the same cause or that an upgrade fixes it.
Installed version was checked privately, but no full environment/driver fingerprint
is published. No patched/new Mesa A/B was run. No specification/full third-party
source is vendored. This diagnostic remains FAIL and root_cause_proven=false.

`probe.py` was executed by a bounded private launcher. `suite.py` reproduces the
same six commands but was not rerun solely to cause two more crashes. Public
`evidence.json` states that provenance rather than claiming a suite hash match.

```sh
python3 benchmarks/coverage/fetch-diagnosis/suite.py \
 --mesa MESA.json --angle ANGLE.json --output REPORT.json
```

Each child has a 20-second timeout. Failure/signal/timeout stays failure; an
incomplete checkpoint file cannot count as a completed pixel validation.

A bounded source review also inspected the upstream-tagged `lp_state_fs.c`
(`source-review.json`). Its fetch helper distinguishes color/depth attachments and
uses fragment-loop state, and its extra per-sample rule is conditional on MSAA.
This narrows useful future debugging locations but is **not** a stack trace or
proof of the crashing instruction. The distribution binary may carry patches;
source-version inspection does not establish exact binary equivalence. No source
or library was modified, and no sensitive core dump was read.
