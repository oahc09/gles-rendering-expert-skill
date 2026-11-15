# Precision admission is not free

`precision_policy.choose` requires an explicit target (`original_unorm` or
`linear`), independent per-format quality results, advertised color/blend
capabilities, the actual renderbuffer dimension limit, and separate logical
allocation/transfer budgets. It chooses the cheapest eligible format, not the
widest float format. Unknown quality, failed quality, missing capability or
insufficient budget cannot silently select a failed RGBA8 fallback.

For a 64×64 single-sample, 48-layer scene:

| Route | logical live attachment bytes | full-frame per-layer logical transfer upper model |
|---|---:|---:|
| RGBA8 | 16,384 | 1,572,864 |
| RGBA16F + RGBA8 conversion output | 49,152 | 3,194,880 |
| RGBA32F + RGBA8 conversion output | 81,920 | 6,373,376 |

Thus the float32 route allocates **5×** the baseline attachment bytes with the
conversion output, and this declared transfer model is over **4×** the baseline.
This is not measured physical residency, bandwidth, traffic or time. Tile
retention, compression, cache and transaction behavior remain unknown. No lower
bound or speedup is inferred. Samples are fixed to one; MSAA/alias/subresources
are outside this contract.

RGBA16F requires an advertised applicable color-buffer extension. RGBA32F also
requires explicit float-blend support. These checks do not replace successful
FBO completeness, compile/link, GL-error and readback checks. A runtime failure
must fail closed, not become a supported/accepted route. The policy itself has
no authority to switch an application's rendering target or waive its original
image contract; linear and per-layer UNORM results are not interchangeable.
