#!/usr/bin/env python3
"""Deterministically materialize the reviewed scenario annotations; not model output."""
import json
from pathlib import Path

# prompt, expected finding IDs, legal controls (must not be reported as defects),
# fallback, core case, API, platform. Each row is a different task, not an execution.
SCENARIOS = {
'Generate': [
('Write GLES 3.0 code to read color attachment 1 of a complete named FBO into RGBA8 CPU memory.', ['select-read-attachment','pack-state','readback-synchronization'], ['glReadBuffer on GLES 3.0'], 'Read attachment 0 when only one exists.', 'C01','3.0','portable'),
('Allocate a 64x64 GL_RGBA8 texture from RGBA unsigned-byte data with glTexImage2D.', ['legal-format-type','unpack-alignment'], ['sized GL_RGBA8 internal format'], 'Use the same legal normalized format; do not substitute integer format.', 'C02','3.0','portable'),
('Generate shared-context texture upload handoff between producer and renderer threads.', ['producer-fence-flush','consumer-wait','ownership-lifetime'], ['shared texture objects'], 'Upload on rendering context if sharing unavailable.', 'C03','3.0','EGL'),
('Write an EGL swap failure handler that distinguishes lost surface and lost context.', ['get-egl-error-on-failure','surface-recreate','context-resource-recreate'], ['APP_CMD_TERM_WINDOW'], 'Suspend rendering until a valid native window exists.', 'C04','3.0','Android'),
('Generate a GLSL ES 3.10 compute shader and dispatch with SSBO results consumed as vertex attributes.', ['version-310','compute-capability','vertex-attrib-barrier'], ['compute in GLES 3.1'], 'CPU update or transform feedback on GLES 3.0.', 'C05','3.1','portable'),
('Write depth-only FBO setup with completeness validation and end-of-pass invalidation.', ['complete-depth-fbo','invalidate-after-last-use'], ['depth-only framebuffer'], 'Retain depth if a later pass samples it.', 'C06','3.0','portable'),
('Generate alpha-cutout foliage shader and propose two measurable depth strategies.', ['discard-needed-for-cutout','measure-depth-strategies'], ['discard with functional alpha cutout'], 'Keep single-pass foliage when prepass regresses.', 'C07','3.0','portable'),
('Write an explicit GLES 3.0 multisample renderbuffer FBO resolve to single-sample texture.', ['matching-resolve-bounds-and-formats','read-draw-fbo','filter-rules-by-format-and-mask'], ['glBlitFramebuffer in GLES 3.0'], 'Single-sample rendering if samples unsupported.', 'C08','3.0','portable'),
('Generate Android AHardwareBuffer import scaffolding into EGLImage with checked extension entry points.', ['android-api-gate','egl-image-extension-gate','buffer-image-lifetime','external-sync'], ['AHardwareBuffer on supported Android'], 'CPU copy into ordinary GL_TEXTURE_2D.', 'C09','3.0','Android'),
('Generate a capability snapshot that distinguishes ANGLE from the application GL API without guessing backend.', ['gl-egl-strings','extensions-limits','backend-unknown-if-unproven'], ['ANGLE may expose GLES'], 'Retain backend unknown until reliable evidence.', 'C10','3.0','Windows-on-Arm'),
('Generate a std140 UBO containing a mat3 and float plus matching C++ layout validation.', ['std140-column-stride','query-offsets','cpu-layout-check'], ['std140 blocks'], 'Explicit padding or queried offsets.', 'C11','3.0','portable'),
('Write a benchmark comparing a uniform branch versus mix of two texture samples.', ['both-samples-cost','same-output','timing-thermal-counters'], ['uniform branch can be efficient'], 'Retain original branch if slower.', 'C12','3.0','portable'),
('Generate GLES 3.2 geometry-shader setup with explicit capability rejection on GLES 3.0.', ['geometry-version-gate','link-log'], ['geometry shaders in GLES 3.2'], 'CPU expansion or instanced vertex rendering.', 'C05','3.2','portable'),
('Generate asynchronous PBO texture-streaming ring with reuse synchronization and unpack state.', ['pbo-offset-not-host-pointer','reuse-fence','pixel-store'], ['pixel unpack buffers'], 'Direct upload with measured stall budget.', 'C02','3.0','portable'),
('Generate HDR window-surface selection with an SDR fallback and explicit display validation.', ['egl-colorspace-gate','window-display-support','tone-map-output'], ['HDR is not guaranteed by GLES version'], 'SDR sRGB output and tone mapping.', 'C10','3.0','Android'),
('Generate shader program cache loading with binary-format detection and source fallback.', ['binary-format-check','link-status-after-load','driver-cache-key'], ['program binaries in GLES 3.0'], 'Compile and link original shaders.', 'C05','3.0','portable'),
],
'Review': [
('Review: default framebuffer is bound and glReadBuffer(GL_COLOR_ATTACHMENT0) is called.', ['default-readbuffer-enum'], ['glReadBuffer(GL_BACK) on default framebuffer'], 'Use GL_BACK for default framebuffer.', 'C01','3.0','portable'),
('Review: glTexImage2D(..., GL_RGBA8UI, ..., GL_RGBA, GL_UNSIGNED_BYTE, data).', ['integer-format-mismatch'], ['GL_RGBA8 with GL_RGBA and unsigned byte'], 'Use GL_RGBA_INTEGER for integer texture data.', 'C02','3.0','portable'),
('Review producer glFenceSync then consumer glWaitSync without any producer flush.', ['producer-not-submitted'], ['server-side consumer wait'], 'Flush producer after fence, manage shared fence lifetime.', 'C03','3.0','EGL'),
('Review Android code handling APP_CMD_CONTEXT_LOST in native_app_glue.', ['invented-app-command'], ['APP_CMD_INIT_WINDOW and APP_CMD_TERM_WINDOW'], 'Use real lifecycle commands and EGL_CONTEXT_LOST error.', 'C04','3.0','Android'),
('Review a #version 300 es shader declaring layout(local_size_x=64) in;', ['compute-in-300'], ['compute shader with version 310 es'], 'Use GLES 3.1 shader or CPU path.', 'C05','3.0','portable'),
('Review invalidation of color attachment before a later postprocess samples that color texture.', ['invalidate-before-last-use'], ['invalidating unused depth after pass'], 'Preserve color until final consumer.', 'C06','3.0','portable'),
('Review a rule claiming all PowerVR scenes must add a depth prepass even when HSR already removes opaque overdraw.', ['unconditional-prepass'], ['vendor-specific profiling'], 'Compare single-pass and prepass on target hardware.', 'C07','3.0','PowerVR'),
('Review a GLES 3.0 color-only RGBA8 multisample-to-single-sample resolve that scales the source rectangle and uses GL_LINEAR.', ['msaa-resolve-identical-bounds-required','normalized-color-filter-not-generic-error'], ['GL_LINEAR for normalized-color resolve with identical bounds and formats'], 'Resolve with identical rectangle bounds and formats before a separate scale pass; integer color or depth/stencil requires GL_NEAREST.', 'C08','3.0','portable'),
('Review AHardwareBuffer release immediately after asynchronous GPU consumer use, with no completion ownership.', ['external-buffer-premature-release'], ['reference-counted lifetime'], 'Retain buffer through consumer completion.', 'C09','3.0','Android'),
('Review Windows-on-Arm renderer routing that selects Adreno solely from OS architecture.', ['os-implies-gpu'], ['Windows on Arm may use translation layers'], 'Probe actual vendor, renderer, version and extensions.', 'C10','3.0','Windows-on-Arm'),
('Review two GLSL ES 3.00 programs: A shares uniform uColor as highp in vertex and mediump in fragment; B has highp vertex output paired with mediump fragment input of the same type.', ['shared-uniform-precision-mismatch','varying-precision-difference-legal'], ['different vertex-output/fragment-input precision with matching types'], 'Match shared uniform precision; do not falsely reject legal varying precision differences.', 'C11','3.0','portable'),
('Review advice that mix(texture(a), texture(b), flag) always beats a uniform branch.', ['unconditional-branchless'], ['mix has valid semantics when both evaluated'], 'Measure sample/bandwidth and retain cheaper branch.', 'C12','3.0','portable'),
('Review legal glReadBuffer(GL_COLOR_ATTACHMENT1) on complete named FBO; a linter bans the API as desktop-only.', ['linter-false-positive'], ['named framebuffer color attachment read'], 'Correct linter boundary rather than removing legal API.', 'C01','3.0','portable'),
('Review legal glTexImage2D GL_RGBA8/GL_RGBA/GL_UNSIGNED_BYTE; a reviewer rejects every sized internal format.', ['sized-format-false-positive'], ['legal sized normalized format'], 'Use specification format table, not blanket ban.', 'C02','3.0','portable'),
('Review ES 3.0 extension PLS shader compiled without checking advertised extension or function availability.', ['pls-extension-gate'], ['PLS when supported and declared'], 'MRT or multipass baseline.', 'C06','3.0','Mali'),
('Review an application requiring Vulkan semaphores directly as GLES core entry points.', ['cross-api-feature-confusion'], ['separate Vulkan renderer backend'], 'Use GLES sync or explicitly supported interop extension.', 'C10','3.2','portable'),
],
'Diagnose': [
('Readback is black only on the default framebuffer after selecting COLOR_ATTACHMENT0. Give a falsifiable diagnosis.', ['readbuffer-enum-check','gl-error-check','readback-source-check'], ['default framebuffer GL_BACK'], 'Correct read buffer then reproduce.', 'C01','3.0','portable'),
('Uploading an integer texture yields GL_INVALID_OPERATION. Internal format is RGBA8UI, external format RGBA.', ['integer-format-table','minimal-upload-repro'], ['RGBA_INTEGER transfer'], 'Correct external format and integer sampling.', 'C02','3.0','portable'),
('Shared texture is intermittently stale; producer issues a fence but never flushes. Diagnose without global glFinish.', ['fence-submission','consumer-wait','lifetime-check'], ['targeted sync'], 'Single-context reproduction before reintroducing sharing.', 'C03','3.0','EGL'),
('eglSwapBuffers returns EGL_BAD_SURFACE after Android window replacement, while context remains valid.', ['bad-surface-not-context-loss','recreate-window-surface','make-current-check'], ['retain valid context objects'], 'Pause frames and recreate surface.', 'C04','3.0','Android'),
('An ES 3.0 device rejects #version 320 es geometry stage. Separate API support from shader syntax.', ['context-version','shader-version','compile-log'], ['ES 3.2 geometry source on supported context'], 'Use 3.0-compatible vertex path.', 'C05','3.0','portable'),
('FBO becomes incomplete after changing color multisample storage but not depth sample count. Diagnose with attachment queries.', ['attachment-snapshot','completeness-status','match-sample-counts'], ['matching supported attachment sample counts'], 'Rebuild FBO consistently and recheck.', 'C06','3.0','portable'),
('Adding alpha discard unexpectedly raises GPU time on one Mali device. Propose measurements, not a universal ban.', ['overdraw-and-early-tests','shader-cost','same-visual-output'], ['discard may be required'], 'Keep correct cutout and select measured strategy.', 'C07','3.0','Mali'),
('An MSAA image is correct before resize and black after; sample count and attachment dimensions may differ.', ['sample-count-query','attachment-dimensions','resolve-errors'], ['supported equal-sample attachments'], 'Single-sample known-good comparison.', 'C08','3.1','portable'),
('Camera EGLImage import works on one Android device but fails on another. Identify capability and format evidence.', ['extension-entrypoint-format','native-buffer-usage','lifetime-sync'], ['device-specific import support'], 'CPU conversion/upload.', 'C09','3.0','Android'),
('ANGLE Vulkan backend is slower than native GLES on one phone. Is this proof ANGLE is always slower?', ['backend-driver-snapshot','controlled-benchmark','no-generalization'], ['backend-dependent tradeoffs'], 'Select measured compatible backend per device.', 'C10','3.0','Android'),
('Animated matrices from a UBO are corrupted but scalar uniforms work. Inspect std140 mat3 stride.', ['ubo-layout-query','cpu-offset-stride','binding-range-check'], ['padded mat3 columns'], 'Correct packing and add known matrix regression.', 'C11','3.0','portable'),
('Replacing a branch with two texture samples doubled bandwidth. Explain an experiment that isolates it.', ['texture-fetch-count','uniformity','bandwidth-raw-trace'], ['branchless can regress'], 'Restore conditional sampling.', 'C12','3.0','Adreno'),
('Black frame after true EGL_CONTEXT_LOST; old texture names remain cached in application objects.', ['recreate-sharegroup-resources','invalidate-cached-names','reload-cpu-assets'], ['logical resource handles independent of GL names'], 'Rebuild context and resource graph.', 'C04','3.0','Android'),
('Frame times rise after ten minutes with unchanged draw count. Device temperature and clocks are missing.', ['thermal-frequency-evidence','repeat-steady-state','cpu-gpu-separation'], ['thermal throttling as hypothesis not fact'], 'Reduce workload only after controlled thermal measurements.', 'C12','3.1','Android'),
('PBO texture uploads stall periodically when ring wraps. Diagnose buffer reuse and map flags.', ['reuse-fence','ring-depth','upload-timeline'], ['PBO does not guarantee zero stalls'], 'Wait safely or increase bounded ring after measurement.', 'C02','3.0','portable'),
('Transparent particles flicker after sorting front-to-back with blending enabled.', ['blend-order-dependence','opaque-transparent-separation','depth-write-policy'], ['opaque front-to-back candidate'], 'Use correct back-to-front transparent ordering.', 'C07','3.0','portable'),
],
'Optimize': [
('Optimize frequent synchronous readbacks while preserving exact CPU results; specify latency contract.', ['readback-pipeline','fence-polling','latency-budget'], ['PBO readback can remain bandwidth-bound'], 'Synchronous path for rare latency-critical reads.', 'C01','3.0','portable'),
('Optimize dynamic texture uploads on mobile with dirty regions and PBO alternatives.', ['upload-bytes','alignment-stride','reuse-sync','benchmark'], ['direct upload may win small updates'], 'Measured direct subimage upload.', 'C02','3.0','portable'),
('Reduce stalls in cross-context texture loading without replacing every wait with glFinish.', ['producer-flush','targeted-fences','bounded-inflight'], ['fences do not eliminate real dependencies'], 'Single-context upload scheduling.', 'C03','3.0','EGL'),
('Reduce Android background/foreground recovery latency without assuming context is always lost.', ['surface-context-distinction','cpu-asset-cache','recovery-measurement'], ['valid contexts may survive'], 'Full resource rebuild on actual loss.', 'C04','3.0','Android'),
('Choose compute or transform feedback for a particle update targeting both GLES 3.0 and 3.1.', ['version-capabilities','workload-measurement','fallback-path'], ['transform feedback on GLES 3.0'], 'Transform feedback or CPU simulation.', 'C05','3.1','portable'),
('Optimize TBDR bandwidth in a postprocess chain where only final color survives.', ['attachment-liveness','discard-unused-depth','minimize-pass-switches','counters'], ['retain intermediates that are sampled'], 'Keep correctness baseline when counters unavailable.', 'C06','3.0','Mali'),
('Optimize opaque overdraw on PowerVR while considering HSR and depth-prepass cost.', ['hsr-conditions','prepass-counterexample','target-counters'], ['front-to-back not universal requirement'], 'Single-pass measured HSR-friendly path.', 'C07','3.0','PowerVR'),
('Compare 4x MSAA explicit resolve with supported multisampled-render-to-texture extension.', ['extension-gate','quality-equivalence','resolve-bandwidth','memory-cost'], ['extension path is conditional'], 'Core explicit resolve or lower sample count.', 'C08','3.0','Adreno'),
('Optimize camera display copies using AHardwareBuffer only where formats and fences are supported.', ['interop-capability','copy-count','fence-overhead','lifetime'], ['zero-copy claim needs measurement'], 'CPU copy/conversion path.', 'C09','3.0','Android'),
('Choose native GLES, ANGLE, or Vulkan for an Embedded Linux product with etnaviv.', ['driver-device-specific','api-coverage','deployment-cost','measured-backend'], ['vendor name does not guarantee certification'], 'Known compatible GLES path.', 'C10','3.0','EmbeddedLinux'),
('Optimize mediump use in a large-world shader without sacrificing visible stability.', ['range-error-analysis','visual-reference','selective-highp','timing'], ['highp required for some calculations'], 'Retain highp for sensitive coordinates.', 'C11','3.0','Mali'),
('Optimize a texture-selection shader where choice is uniform per draw; compare branch and dual sample.', ['uniformity','sample-count','gpu-bandwidth','negative-result'], ['branch can skip texture work'], 'Retain whichever passes visual and timing tests.', 'C12','3.0','Adreno'),
('Reduce frame pacing variance when CPU and GPU times are below display period.', ['present-timeline','queue-depth','refresh-rate','frame-pacing-integration'], ['low average GPU time does not prove smooth presentation'], 'Stable pacing before resolution changes.', 'C10','3.0','Android'),
('Reduce first-use shader hitching without assuming program binaries are portable across drivers.', ['warmup','binary-cache-key','compile-link-fallback','hitch-distribution'], ['binary cache may be rejected'], 'Source compile outside critical path.', 'C05','3.0','portable'),
('Optimize bloom for a thermal-constrained mobile game with HDR targets.', ['downsample-chain','format-support','bandwidth-quality','thermal-steady-state'], ['HDR renderability requires checks'], 'SDR bloom or fewer levels.', 'C06','3.1','Android'),
('Reduce CPU submit overhead with instancing while preserving transparent ordering and culling.', ['cpu-profile','batch-material-state','instance-visibility','blend-order'], ['larger batches may increase GPU work'], 'Smaller correctly ordered batches.', 'C07','3.0','portable'),
]}

SOURCES = {'gles':'https://registry.khronos.org/OpenGL/specs/es/3.2/es_spec_3.2.pdf',
'egl':'https://registry.khronos.org/EGL/specs/eglspec.1.5.pdf',
'glsl':'https://registry.khronos.org/OpenGL/specs/es/3.20/GLSL_ES_Specification_3.20.pdf',
'android':'https://developer.android.com/ndk/reference/group/a-hardware-buffer'}

def build():
    cases=[]
    for mode, rows in SCENARIOS.items():
        for prompt, expected, allowed, fallback, core, version, platform in rows:
            identifier=f'A{len(cases)+1:03d}'
            cases.append({'case_id':identifier, 'mode':mode, 'prompt':prompt,
                'device_capabilities':{'gles_version':version,'glsl_version':{'3.0':'300 es','3.1':'310 es','3.2':'320 es'}[version], 'platform':platform,'extensions':'unknown: must probe','renderer':'unspecified: do not infer','hardware_evidence_available':False},
                'core_case':core, 'severity':'high' if mode in ('Generate','Review','Diagnose') else 'medium',
                'expected_findings':expected, 'legal_controls':allowed,
                'forbidden_advice':['Invent supported extensions or device measurements.', 'Claim universal performance wins without before/after evidence.'],
                'fallback':fallback, 'evidence_sources':list(SOURCES.values()) + (['https://registry.khronos.org/OpenGL/specs/es/3.0/es_spec_3.0.pdf#page=210'] if core=='C08' else []),
                'compile_evidence':{'required':mode=='Generate','artifact':None,'status':'NOT_RUN'},
                'rubric':{'accuracy':'Human reviewer maps justified findings to expected_findings; count TP/FN and unsupported findings as FP.', 'false_positive':'Any legal_controls rejected without additional evidence count as false positives.', 'debug_steps':'For Diagnose, require symptom, capability snapshot, minimal reproduction, falsifiable causes, minimal fix and regression.', 'performance':'For Optimize, require baseline, device/driver/backend, repeated stable-thermal timing, raw trace/counters where available, negative result and rollback.'}})
    return {'schema_version':1,'annotation_status':'REVIEW_REQUIRED_BEFORE_RELEASE','cases':cases}

if __name__=='__main__':
    Path(__file__).with_name('cases.json').write_text(json.dumps(build(),ensure_ascii=False,indent=2)+'\n')
