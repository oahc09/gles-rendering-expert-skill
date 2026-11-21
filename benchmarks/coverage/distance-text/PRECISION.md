# Independent sampler precision intervention

`precision_probe.py` reuses the unchanged original Host draw/atlas/CPU oracle.
It intervenes only in shader source passed to compilation. Three arms:
original implicit sampler precision; explicit highp sampler with hardware linear
filtering; explicit highp sampler plus four clamped texelFetch calls and shader
bilinear interpolation. Original captures, run.py and budget3 remain unchanged.
Both sizes16/32 and SDF/MSDF run with all original wrong-channel, wrong-threshold,
wrong-outline controls and actual alpha-mask fallback. Each driver performs
54 ordinary draws plus48 diagnostic draws/readbacks, total102.

## Actual result

| Software path | Original SDF32 error | Highp hardware SDF32 | Four-tap SDF32 |
|---|---:|---:|---:|
| Mesa | 9 FAIL | 9 FAIL | 0 PASS |
| ANGLE | 0 PASS | 0 PASS | 0 PASS |

Four-tap all four size/atlas combinations error0 on both drivers. Negative
controls still fail, alpha fallback remains exact. This supports a bounded
four-tap correctness option, **not** a universal MSDF fix or performance win.
Simply specifying highp sampler does not eliminate the Mesa SDF32 discrepancy.

At bottom-up pixel (8,7) in SDF32, CPU ideal sample=.5042892156862745 and
coverage=.6022947433490886. Mesa original sample=.505859375 and
coverage=.63897705078125; highp hardware=.5058823823928833 and
.6395097374916077; four-tap=.5042892694473267 and .6022956371307373.
Across the image, Mesa original sample max error=.0026443781 and coverage max
error=.0366823074; highp hardware .0027573885/.0372149941; four-tap
6.26434e-8/8.93782e-7. ANGLE four-tap sample error6.26434e-8 and coverage
1.25141e-6. CPU uses ideal double-precision four-tap interpolation of normalized
RGBA8 texels and cubic coverage. It is a target model, not an exact normative
hardware filtering implementation. Observations locate an upstream sampling-path
difference amplified by the narrow coverage ramp; they do not identify an
internal driver implementation or establish a specification violation.

## Instrumentation and cost

Separate diagnostic shaders write each sampled RGB float and coverage float as
four byte channels via floatBitsToUint. Highp integer arithmetic is explicitly
required for bit packing. All packed values are finite and retained losslessly.
Requantized diagnostic coverage matches ordinary coverage outputs exactly on
both drivers (max error0), guarding against misleading instrumentation. Shader
source hashes accompany each diagnostic capture. These are diagnostic draws,
not timed frames; no GPU timing or physical device evidence exists.

The alternative has **four explicit texelFetch instructions plus interpolation**
versus one hardware-filtered texture instruction. This is source-level work,
not measured physical fetches, bandwidth or speed. CPU alpha-mask fallback
remains valid and unchanged, including its resolution-dependent storage cost.
No automatic performance acceptance is made.

## Reproduce

```
python benchmarks/coverage/distance-text/precision_probe.py --config DRIVER_JSON --output REPORT.json.gz
python -m unittest discover -s benchmarks/coverage/distance-text -v
```

`.gz` output is deterministic lossless JSON; `.json` output remains available.
Saved `evidence/precision-{mesa,angle}.json.gz` includes full ordinary pixels
and full packed-float diagnostic captures. No old evidence manifest is changed.

## Primary precision reference

[GLSL ES 3.00 specification](https://registry.khronos.org/OpenGL/specs/es/3.0/GLSL_ES_Specification_3.00.pdf), precision qualifiers/default precisions and texture functions:
sampler2D defaults to lowp and texture-result precision follows sampler
precision. That motivates the highp-only control; the measured result, not the
rule alone, shows it is insufficient here. No claim that four-tap sampling is
required by the specification. Original msdfgen source rationale, licensing and
synthetic-glyph limitations remain in README.md.

## Verified route selection

`--max-explicit-fetches` is an explicit **selected shader instruction** budget,
integer0..4, default1. It is not the number of internal memory accesses or the
number of offline test draws. Selection revalidates complete pixel evidence:
quality-passing highp hardware first; otherwise quality-passing four-tap only
when budget>=4; otherwise tested alpha-mask when budget>=1; else UNAVAILABLE.
Saved probe captures use `--max-explicit-fetches 4`: Mesa SDF32 selects four-tap;
other cases retain highp hardware. With default1 or budget3 the same captured
Mesa SDF32 evidence selects alpha fallback. Tests cover both rejection and
selection, missing/duplicate evidence and invalid budgets. All choices are
quality-only; none accepts a performance claim. Replay saved reports by adding
`--max-explicit-fetches 4` to the command above.

Instrumentation development: an initial diagnostic used default integer
precision for the 32-bit packing and failed its own coverage consistency check
on Mesa. The diagnostic now explicitly declares highp int. Both final drivers
were recollected after this correction; no original capture or shader budget
was modified, and invalid initial instrumentation is not treated as sample data.
