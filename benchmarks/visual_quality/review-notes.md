# Visual review and limitations — 2026-11-01

The author inspected an eight-panel contact sheet of actual reference P6 captures.
Observed: animated multicolor accumulation pattern, smooth specular normal highlight,
water highlight grid, smooth gradient, HDR bloom-like lobe, overlapping transparency,
sRGB texture gradient, and the matching HDR signal used for format isolation.
No image was blank. This is author visual inspection, not independent art approval.

Known rejected candidates: P01 mediump accumulation and P03 mediump water; both
policy scales (.85/.7) also fail P03 water thresholds. Other scale candidates pass
this software reference only. All eight injected static errors and alternating
mid-frame flicker controls are detected. Independent device visual review is unrun.

Initial local development exposed (and fixed before frozen runs) output timestamp
rounding and a reversed smoothstep edge order. One interrupted development run
encountered a transient executable permission error while recompilation replaced
the binary; the launcher now links a temporary name and renames atomically.
These interrupted/failed development runs are not counted as final PASS.

Golden producer hash predates the optional exact-shader-source capture wrapper;
the wrapper does not alter shader contents. Final captures compare against those
frozen pixels, rather than silently replacing them after source instrumentation.
