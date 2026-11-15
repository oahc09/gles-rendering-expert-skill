# 32² half-float far target: fixed original-target verification

`python3 benchmarks/overlap_scenes/far_precision.py --config DRIVER_JSON --output REPORT_JSON`

This independent experiment retains the original64² RGBA8 baseline and CPU
quality target. Candidate far geometry actually renders into32² RGBA16F, is
four-fetch bilinearly reconstructed into64² RGBA8, then receives independently
rendered64² foreground. Alpha parameters are unchanged. No64² far compensation,
float32 expansion, camera-subset tuning or redefinition of target is used.

## Capability and explicit cost admission

RGBA16F requires advertised EXT_color_buffer_half_float or
EXT_color_buffer_float. EXT_float_blend is not imposed on this16F path. Actual
FBO completeness, compile/link success, blending, final readback and GL errors
are checked. Unsupported capability yields NOT_SUPPORTED without claiming a
validated baseline fallback. Direct Host.draw calls also enforce capability
and budget checks; advertised-but-broken execution is a hard failure.

Logical per-output allocation is24576 bytes (8192 half-float far +16384 final
RGBA8), versus32768 for baseline's two64² RGBA8 targets. Bilinear reconstruction
has up to16384 source-level fetches and147456 logical read/write bytes, larger
than the81920 byte bound for RGBA8 inputs. Fixed verifier gates are32768 bytes
of attachments and524288 logical-transfer upper bytes/output, including far
blend, copy and foreground blend. These exclude driver/shader/CPU allocations
and are not actual residency, cache/DRAM traffic or GPU performance guarantees.
Both arms still issue8 draws/view. Precision is not a free improvement.

## Independent references and observed failure

The mechanism-only CPU oracle rounds each far blend to IEEE half precision,
interpolates the half values, quantizes toRGBA8, then composites foreground.
Acceptance always uses original per-layer64² RGBA8 CPU reference and unchanged
4-code /2-silhouette /.1-pixel centroid and parallax limits. The half oracle is
not used to replace that target. Only final RGBA8 pixels are read back and
archived; raw intermediate half-float texels were not captured, so final-image
agreement does not prove exact equality at every intermediate half operation.

Both drivers actually execute21 readbacks: seven cameras, baseline/candidate/
foreground-drop negative. Original cameras(-.3,0,+.3) now pass, but the held-out
-.15,+.15,+.45 views have3,3,4 silhouette disagreements on both drivers. Thus
both reports remainFAIL and select one fixed validated baseline for all views.
Mechanism oracles pass and all negative controls are rejected. A baseline or
mechanism failure cannot produce an accepted fallback; no per-view switching.

The original-plus-holdout protocol prevents promoting a center-pixel precision
fix as a broadly accepted solution. Half precision addresses the previously
observed quantization-sensitive original-center result but does not eliminate
sampling/reconstruction differences at other views. It is not lossless with
respect to per-layer UNORM or a universal improvement.

Verified CLI: both drivers default exit1, contract-only exit0. Contract-only
checks complete unique camera/variant coverage, real readback, mechanism
correctness, negative rejection and global selection while keeping visual FAIL.
JSON and deterministic ZIP retain every actual/fixed-target/mechanism-reference
image, thresholds, costs, capability policy and source hashes. Extract beside
the report. Historical failures remain unchanged; physical-GPU performance is
NOT_MEASURED.
