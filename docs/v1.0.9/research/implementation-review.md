# v1.0.9 selected implementation review

AI source review, **not independent human review**. Four selected commits were read through their actual GitHub commit API patches, including implementation hunks and added tests where present. Titles were used only to select candidates. No upstream build or exact upstream regression was executed in this review.

Corpus: 1,319 metadata candidates; **4 commit source-reviewed here, 1,315 not covered by this file**. ANGLE: 2 / 856; Filament commits: 2 / 442. The other 21 candidates and vendor/X review are not covered by this file; separate release reviews may cover some of them. Existing release-source receipts are not counted as implementation review.

Patch SHA256 values and fetched commit-response hashes are recorded in `implementation-review.json`; hashes identify public source content, not environment fingerprints.

## ANGLE_STORAGE_REBINDS

Source: [2f5d7a4dbcad](https://github.com/google/angle/commit/2f5d7a4dbcad89f1b228ff264f365aa9a56523b5), 2026-10-28T16:40:36Z.

**Observed source change.** ANGLE Vulkan now propagates explicit deferred memory-barrier bits through storage buffer/image access helpers. Buffer read/write tracking bypasses event-only shortcuts when an explicit barrier requires a pipeline dependency; image writes select Pipeline instead of Event for relevant bits.

**Patch/test inspection.** The added StorageBarrierAcrossSequentialRebinds and ImageBarrierAcrossSequentialRebinds tests prime the first resource differently, write four rebound resources, issue one barrier, then overwrite and verify all four. This is a mixed-history ordering bug, not evidence that every draw needs a global barrier.

**Current experiment linkage.** `benchmarks/shader_ab/advanced.py`, `benchmarks/shader_ab/test_advanced.py`.

**Gap.** Our single SSBO compute-to-fragment positive control covers only a simpler ordering edge. Mixed event/pipeline resource histories and sequential image rebinds are NOT_REPRODUCED locally.

**Decision / non-promotion.** Add a candidate multi-resource rebind regression; preserve API consumer-specific barrier semantics. Do not promote a new mandatory global-barrier rule or infer a speedup.

## ANGLE_BLEND_ATTACHMENT_TRANSITIONS

Source: [035f8885dea7](https://github.com/google/angle/commit/035f8885dea7122f51ef9cd0a07db1568a974573), 2026-11-09T21:06:27Z.

**Observed source change.** ANGLE Vulkan consolidates framebuffer-change blend function/equation updates around previous/new color attachment masks and resetBlendFuncsAndEquations; FramebufferVk invokes the new transition-specific helper.

**Patch/test inspection.** The new AttachmentFormatWithEnabledBlend test uses sparse draw buffers at attachment 1 and 3, changes one attachment from RGBA8 to RGBA32UI and back while blending stays enabled, and verifies float accumulation separately from integer output. It explicitly probes GL_OES_draw_buffers_indexed; an Intel OpenGL expectation is skipped, not a passing portability result.

**Current experiment linkage.** `benchmarks/overlap_scenes/advanced.py`, `tools/rendergraph_optimizer.py`, `tools/test_rendergraph_optimizer.py`.

**Gap.** Current transparency controls exercise compositing but not this sparse-MRT integer/normalized attachment transition. The exact upstream regression remains NOT_REPRODUCED.

**Decision / non-promotion.** Require attachment format/state transition coverage when considering FBO reuse. Do not assume blend-state omission is legal or claim reduced CPU/GPU time from this patch.

## FILAMENT_GL_FREE_ASYNC_FLUSH

Source: [95c94d089ab2](https://github.com/google/filament/commit/95c94d089ab2c4cc630c4d238c1e5ba2d8edd127), 2026-10-22T01:53:40Z.

**Observed source change.** Filament removes flushIfSharedContext only from two queued worker jobs: createTextureViewSwizzleAsyncR and importTextureAsyncR. Both queue push and scheduled completion callback remain; code comments state these jobs issue no GL commands on the worker.

**Patch/test inspection.** The source distinguishes unnecessary GL flushing from necessary job ordering: swizzle views rely on an earlier async texture-create job filling src->gl. Removing the queue itself would change the dependency even though these two flush calls disappear.

**Current experiment linkage.** `tools/rendergraph_optimizer.py`, `tools/test_rendergraph_optimizer.py`, `benchmarks/agent/cases-v1.0.9.json`.

**Gap.** The graph advisor refuses unreviewed synchronization and only proposes candidates; no shared-context asynchronous Filament job/callback harness exists here. No before/after timing is established.

**Decision / non-promotion.** Keep as a bounded optimization hypothesis for demonstrably GL-free jobs. Reject any universal remove-glFlush advice or callback reordering; exact job ordering and shared-context visibility need a new runtime experiment.

## FILAMENT_PACKING_PRECISION

Source: [e8669b688a93](https://github.com/google/filament/commit/e8669b688a9381beb4f7470df828e1932d78efa6), 2026-11-07T00:01:42Z.

**Observed source change.** Filament packing polyfills now first assign each converted channel to a highp uint before shifting in packUnorm4x8/packSnorm4x8; unpackSnorm4x8 sign-extension intermediates become explicit highp int in both code blocks.

**Patch/test inspection.** The patch moves shifts out of initializer expressions and onto highp operands, and fixes unpack temporary precision. A highp destination alone did not express high precision for every intermediate operation in the old source.

**Current experiment linkage.** `benchmarks/shader_ab/run.py`, `benchmarks/shader_ab/build_cases.py`, `benchmarks/agent/cases-v1.0.9.json`.

**Gap.** Current precision/quality controls do not reproduce every UNORM/SNORM byte-packing edge on an implementation with actual 16-bit mediump integers. Physical precision distribution remains BLOCKED_BY_HARDWARE.

**Decision / non-promotion.** Add bounded signed/unsigned pack/unpack boundary tests and inspect intermediate precision. Do not change all shaders to highp, infer universal mediump width, or report an unmeasured performance effect.

## Acceptance boundary

All four are SOURCE_CONFIRMED engineering references only. No new mandatory rule, measured gain, vendor-wide fix, exact regression reproduction or release-gate completion is claimed. Preserved inherited hardware/provider gates remain unchanged.


## Source-informed packing experiment added

`benchmarks/shader_ab/packing.py` and `test_packing.py` add eight bounded
signed/unsigned pack/unpack cases. Each runs a fixed highp-intermediate variant,
a deterministic wrong-channel negative, and a legacy-expression diagnostic.
CPU goldens include UNORM endpoints/byte boundaries/clamping and SNORM signs,
negative 128 clamping, and byte ordering. No half-tie rounding claim is needed.

Both software implementations: 8 fixed PASS, 8 wrong variants FAIL, 24 actual
4×4 draw/readbacks each. Thirteen host unit tests pass, including invalid-pixel and compile/link gates. Mesa legacy packing fails
four case groups while ANGLE legacy variants pass all eight. Both expose the
same minimum precision query ranges; those reported guarantees are NOT a proof
of actual execution width for every expression. This difference is diagnostic,
not a claim of reproducing the original Filament/device bug or proving a vendor
fix. Specific upstream and physical precision acceptance remain unverified.

Safe pixel/source-hash reports: `benchmarks/shader_ab/evidence/packing-mesa.json`
and `packing-angle.json`. Performance remains NOT_MEASURED. Separately reviewed
six release records are not counted as commit implementation reviews here;
combined coverage is ten distinct sources, not four, with independent human
review still unavailable.


### Attachment source-to-experiment follow-up

`benchmarks/attachment_controls/run.py` now exercises actual normalized→integer→
normalized FBO transitions plus sparse indexed mixed-format MRT on both software
drivers, with independent CPU pixels and deliberate blend/value failures. Each
executes seven draws/eight readbacks. This narrows the local coverage gap; it does
not recreate all upstream states, regress the upstream revision or prove the
particular ANGLE fix. Read its README for exact API feature selection.
