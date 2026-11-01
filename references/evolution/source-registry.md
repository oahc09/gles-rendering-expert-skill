# Source registry and promotion policy

| Source | Track | Scope / verification |
|---|---|---|
| [Khronos GLES registry](https://registry.khronos.org/OpenGL/index_es.php) | Core and GLSL specifications, extension revision | Normative API contracts; record exact version/section, not index crawl date |
| [EGL registry](https://registry.khronos.org/EGL/) | EGL core and platform/image/sync extensions | Normative lifetime, error, extension dependencies |
| [Conformance records](https://www.khronos.org/conformance/adopters/conformant-products/opengles) | Product submission date and exact implementation | Certification evidence only for submitted configuration, not all devices with similar GPU |
| [VK-GL-CTS](https://github.com/KhronosGroup/VK-GL-CTS/releases) | Separate GLES and Vulkan tags | Reference test implementation, not a new API specification |
| [ANGLE](https://chromium.googlesource.com/angle/angle/) | Commit/CL/issue history | Backend behavior tied to exact revision; mirror main is not a stable product release |
| [Android graphics](https://developer.android.com/games/guidelines) | Platform requirements and API docs | Separate OS policy, device capability, app architecture |
| [Filament](https://github.com/google/filament/releases) | Release date, backend/source scope | Engine implementation ideas; no automatic GLES core promotion |
| [AGI](https://github.com/google/agi/releases), [Perfetto](https://github.com/google/perfetto/releases), [RenderDoc](https://github.com/baldurk/renderdoc/releases) | Version and supported target devices/APIs | Profiler coverage must be checked on actual target |
| [Arm guidance](https://developer.arm.com/documentation/102643/latest/), [Qualcomm docs](https://docs.qualcomm.com/), [PowerVR guide](https://docs.imgtec.com/performance-guides/graphics-recommendations/html/index.html) | GPU generation / tool counter definitions | Performance hypothesis, conditional until reproduced; no blanket percentage |
| [Mesa](https://gitlab.freedesktop.org/mesa/mesa) | Driver-specific changes (etnaviv/Panfrost/Freedreno) | Commit + affected GPU/repro; do not equate driver families |
| X original author posts | Author, original timestamp, code/demo and independent primary corroboration | Candidate only until evidence supports claim; no verified first-window item retained |

Evidence level is source quality; claim status is the outcome. `OFFICIAL_SPEC`, `OFFICIAL_IMPLEMENTATION`, `REPRODUCED` may support reviewed requirements, but implementation behavior alone must not be mislabeled a normative core requirement. `SECONDARY` and `UNVERIFIED` never justify a new MUST. Promotion: source/date → applicability → reproduction → rule/case diff → automated regression → independent review. Unknown publication dates stay null/unknown, never discovery date.
