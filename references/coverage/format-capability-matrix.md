# Format and interaction boundaries

Separate texture allocation, filtering, renderability and blendability. A format name alone proves none of the other operations. Use actual version/extensions, framebuffer completeness and bounded draw/readback probes. Never use core promotion to assume an optional implementation format.

| Family | Required decision / fallback |
|---|---|
| RGBA8 UNORM | ES3 sized storage; immutable storage cannot be redefined. Fixed original oracle can still expose accumulated rounding differences. |
| Integer | Match integer format/type; nearest filtering and integer shader interfaces; normalized float upload is not interchangeable. |
| RGBA16F/32F | Color-buffer and blending permissions differ; probe each operation and budget attachment/copy costs. Reject unavailable route, preserve valid baseline. |
| Depth/stencil | Validate attachment support and dimensions/sample count; invalidate only dead data after final consumer. |
| Compressed | Exact advertised family and block/mip constraints, actual transcoder target and payload; RGBA8 fallback has explicit memory cost. |
| sRGB/HDR | Transfer function, attachment conversion and display calibration distinct; software RGB8 is not physical HDR. |
| MSAA | Query format-specific sample support; resolve restrictions and matching dimensions; don't replace numeric samples with global limit. |
| PBO/PixelStore | Alignment, row length, skip and offset share address calculation; unmap before transfer, preserve lifetime until completion. |

48 new actual positive/error interactions are in examples/closure/gles-runtime/state_interactions.cpp and benchmarks/coverage/state-machine/evidence.json. They exercise 24 distinct boundaries, not 48 independent API coverage families. Existing hazard/resource/state-cache/RAII and precision tests remain unchanged. No performance improvement follows from error-code checks.
