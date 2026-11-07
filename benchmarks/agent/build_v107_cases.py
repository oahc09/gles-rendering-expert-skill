#!/usr/bin/env python3
"""Append thirty independently authored pipeline tasks; never model results."""
import copy
import hashlib
import json
from pathlib import Path

HERE = Path(__file__).parent
BASELINE_SHA256 = 'a97cfd868270c8af905127105f80599f02db012b56382163e640410347fd2277'
SPEC = 'https://registry.khronos.org/OpenGL/specs/es/3.2/es_spec_3.2.pdf'
GROUPS = [
 ('variant_governance', [
  ('Generate', 'Build a GLES 3.0/3.1/3.2 material pipeline with normal-map, skinning and compute flags, mutually exclusive alpha modes and a 24-program budget. Emit only legal reachable variants, source-stage hashes and an explicit non-compute fallback.', ['constraint-before-compilation','bounded-reachable-variants','fallback-program-pair']),
  ('Review', 'A variant generator emits every boolean combination, injects layout(binding=0) into GLSL ES 3.00, and labels every compiler rejection a driver bug. Review its pipeline manifest and provide negative controls for version and extension boundaries.', ['essl300-binding-boundary','reject-illegal-combinations','compiler-not-driver-proof']),
  ('Optimize', 'Two depth-only material variants differ only in unused color macros. Decide when to share their program without changing vertex displacement, alpha discard or custom depth. Compare code-size and cold-start evidence independently from GPU frame time.', ['semantic-depth-equivalence','displacement-and-discard-control','separate-size-startup-gpu'])]),
 ('binary_cache', [
  ('Generate', 'Implement a bounded GLES program-binary cache for a multi-material renderer. Include preprocessed stage sources, macro values, options, material ABI, backend, driver and extension identity; validate format and link status, then rebind uniforms or fall back to source compilation.', ['complete-cache-identity','binary-format-and-link-check','restore-bindings-after-load']),
  ('Diagnose', 'A cached program links but the normal map samples unit zero after an application update. Source compilation works. Trace sampler assignments and ABI signatures after glProgramBinary; distinguish valid binary load from restored application bindings.', ['binary-load-not-binding-restore','abi-signature-invalidation','source-path-comparison']),
  ('Review', 'Review a cache that trusts a file-supplied binary size, stores only GL_RENDERER, and uses a Vulkan SPIR-V blob with glProgramBinary. Give corrupt/truncated/unsupported-format tests and a bounded source fallback.', ['bound-untrusted-cache-size','full-driver-source-key','no-portable-spirv-binary'])]),
 ('material_layout', [
  ('Generate', 'Create two PBR variants sharing a C++17 std140 block with vec3, float, mat3 and a float array. Generate offsets/strides, static_asserts and runtime reflection checks; reject an incompatible second variant before drawing.', ['std140-offset-stride-contract','cross-variant-abi-signature','runtime-reflection-before-draw']),
  ('Review', 'A host struct packs a mat3 into 36 bytes and a float[3] into 12 bytes in std140, while an SSBO std430 manifest is enabled on GLES 3.0. Diagnose each member, give corrected layouts and a 3.0 UBO fallback.', ['matrix-column-stride','std140-array-stride','ssbo-version-fallback']),
  ('Diagnose', 'A roughness field moves when a variant removes an active uniform. The engine compares only block byte size and claims ABI compatibility. Show how active-member names, offsets, types and strides expose the mismatch without assuming inactive members must reflect.', ['active-interface-validation','equal-size-not-equal-layout','inactive-member-policy'])]),
 ('binding_namespaces', [
  ('Review', 'A GLES material uses UBO binding zero and sampler unit zero. A validator rejects that as a duplicate Vulkan descriptor. Another material aliases sampler2D and samplerCube on one active unit. Classify the legal and illegal cases independently.', ['gles-separate-binding-namespaces','incompatible-active-sampler-alias','no-vulkan-set-import']),
  ('Generate', 'Build a transparent PBR material binding table with texture targets, numeric classes, samplers and bounded units. Validate linked-program activity and per-stage limits before the draw; keep a shared identical sampler binding as a legal control.', ['texture-target-and-numeric-class','active-unit-and-stage-limits','compatible-alias-legal-control']),
  ('Diagnose', 'After material switching, one shader samples an integer texture with sampler2D and another retains the previous material sampler object. Provide a per-draw snapshot and minimal binding regression with named parameters.', ['sampler-format-class-mismatch','sampler-state-ownership','named-binding-regression'])]),
 ('rendergraph', [
  ('Generate', 'Design particle scene → bright extraction → two blur passes → bloom composite → tone mapping as a standalone GLES graph. Describe imported history, discarded depth, resource lifetimes and format/sample constraints; produce a stable executable ordering.', ['explicit-pass-resource-contract','defined-import-and-store','stable-topology-lifetimes']),
  ('Review', 'A rendergraph aliases two equal-sized attachments whose lifetimes overlap and invalidates the bloom source before composite. Detect both defects, include a dependency-cycle path and propose reuse only after last use.', ['overlap-prevents-alias','discard-before-last-read','cycle-diagnostic-path']),
  ('Optimize', 'A graph planner promises transient attachments eliminate DRAM traffic on every TBDR GPU. Preserve its logical lifetime recommendation but design a same-driver A/B with tile counters, visual equivalence and a no-gain control.', ['logical-not-physical-pass','same-device-counter-ablation','no-gain-and-image-control'])]),
 ('synchronization', [
  ('Generate', 'Implement compute-generated particle vertices and indirect draw arguments on ES3.1, then bloom them. Select barriers by consumer operation, bound counts, and provide explicit CPU vertex generation on ES3.0.', ['vertex-and-command-barrier','bounded-indirect-data','es30-cpu-path']),
  ('Review', 'A hazard checker requires glMemoryBarrier after every normal FBO render→texture sample, but accepts sampling an attached output during the same draw. Fix both classifications without assuming texture-barrier extensions exist.', ['ordered-fbo-sampling-legal','feedback-not-barrier-fixable','extension-probe-boundary']),
  ('Diagnose', 'Two shared EGL contexts hand a compute-written texture between threads. Producer inserts a fence but does not flush; consumer waits without binding the shared object. Separate submission, execution wait, visibility and container ownership.', ['producer-flush-before-wait','context-state-rebind','visibility-and-completion-distinct'])]),
 ('msaa_pipeline', [
  ('Generate', 'Build MSAA opaque geometry → matching single-sample resolve → HDR tone mapping. Probe format/sample support and FBO completeness; resolve with legal rectangles/filter, then scale in a later shader pass.', ['sample-format-probe','resolve-rectangle-filter-contract','separate-scale-tonemap']),
  ('Review', 'A GLES MSAA resolve scales 1920x1080 to 960x540 with GL_LINEAR and converts RGBA16F directly to RGBA8, then samples the multisample renderbuffer using sampler2D. Give separate fixes and a no-MSAA fallback.', ['resolve-not-scale-or-convert','renderbuffer-not-texture-sampler','single-sample-fallback']),
  ('Diagnose', 'Only alpha edges fail the image threshold after 4x MSAA. Compare coverage and premultiply convention in linear space before blaming resolve. Preserve region-specific tolerances and record sample support per backend.', ['coverage-vs-alpha-convention','edge-region-threshold','backend-sample-evidence'])]),
 ('color_materials', [
  ('Generate', 'Create six material scenes covering sRGB base color, linear normal/roughness maps, layered premultiplied glass, particles, HDR bloom and PBR. Use independent references and error budgets per transfer/alpha/FP16 axis.', ['color-vs-data-texture','single-alpha-transfer','axis-specific-oracle-thresholds']),
  ('Diagnose', 'A bloom scene is dark on opaque objects but transparent particle edges glow. The input is sRGB, lighting is linear, and both the final shader and output conversion encode gamma. Isolate double transfer and repeated premultiplication with separate controls.', ['single-output-encoding','separate-alpha-fault','controlled-reference-capture']),
  ('Review', 'A report equates llvmpipe screenshots with calibrated HDR display output and applies exact RGB8 equality to all FP16 backends. Replace this with numeric GPU readback, backend tolerances and explicit display NOT_RUN.', ['software-not-display-evidence','backend-quantization-tolerance','separate-display-gate'])]),
 ('shader_risks', [
  ('Optimize', 'Analyze a varying-dependent branch with many texture reads and four MRT outputs in a PBR pass. Report source-stage-line risks, then compare a branchless variant, including a slower candidate and stable thermal/device controls.', ['source-located-risk-not-timing','branchless-can-regress','matched-thermal-ablation']),
  ('Review', 'A regex tool sees texture() in a comment, estimates register count from variable names, and declares a 40% gain without captures. Make it a bounded advisory analyzer with false-positive controls and null unmeasured metrics.', ['ignore-comment-tokens','register-pressure-hypothesis','no-invented-speedup']),
  ('Diagnose', 'First frame stalls while later frames are fast. Distinguish CPU source compilation, driver linking, cache I/O and first-use GPU work; do not identify GPU time from wall-clock shader calls. Retain cold/warm/corrupt-cache traces.', ['separate-startup-phases','cpu-wall-not-gpu-timer','cold-warm-failure-controls'])]),
 ('pipeline_evidence', [
  ('Generate', 'Specify blinded no-skill/with-skill evaluation for a camera-external-texture + multi-material 3D + bloom renderer. Record API, compile, first-run, numeric, visual and regression results independently, with raw artifacts and provider cost availability.', ['blinded-paired-artifact-evaluation','first-run-not-compile','provider-cost-unknown-not-zero']),
  ('Review', 'A generated pipeline passes ten fixture checks but no provider has run. Its report claims model gains and removes prior hardware gates to publish v1.0.7. Correct the result and preserve candidate-versus-release status.', ['fixtures-not-model-results','recursive-gate-preservation','no-release-from-merge']),
  ('Optimize', 'A material binding validation idea comes from a dated Filament commit, while a Vulkan-only optimization claims 0.6ms. Build source→rule→example→test traceability and reject transferring that performance claim into GLES.', ['review-source-diff','api-specific-scope','reject-cross-api-performance-transfer'])])]

def build():
    raw = (HERE / 'cases-v1.0.6.json').read_bytes()
    if hashlib.sha256(raw).hexdigest() != BASELINE_SHA256:
        raise ValueError('Frozen v1.0.6 corpus changed')
    baseline = json.loads(raw)
    cases = copy.deepcopy(baseline['cases'])
    if len(cases) != 142:
        raise ValueError('Expected 142 preserved cases')
    for topic, rows in GROUPS:
        for mode, prompt, findings in rows:
            case = copy.deepcopy(cases[0])
            case.update(case_id=f'A{len(cases)+1:03d}', mode=mode, prompt=prompt,
                        core_case='C10', severity='high', expected_findings=findings,
                        legal_controls=['An explicitly capability-gated fallback or NOT_RUN result is valid.',
                                        'Ordinary same-context FBO writes followed by later texture sampling need no shader-memory barrier.'],
                        forbidden_advice=['Invent hardware, provider or performance results.',
                                          'Treat Vulkan descriptors/barriers as GLES core APIs.',
                                          'Override predecessor release gates from a candidate merge.'],
                        fallback='Keep the verified source-compiled baseline or return unsupported with the missing capability.',
                        evidence_sources=[SPEC, 'references/pipeline/'],
                        compile_evidence={'required': mode == 'Generate', 'artifact': None, 'status': 'NOT_RUN'},
                        v107={'topic': topic, 'model_calls': 0, 'annotation_status': 'REVIEW_REQUIRED_BEFORE_RELEASE',
                              'origin': 'authored independent pipeline task, not a measured model response'})
            version = '3.1' if topic == 'synchronization' else '3.0'
            case['device_capabilities'].update(gles_version=version, glsl_version='310 es' if version == '3.1' else '300 es',
                                              platform='GLES native or ANGLE only with a captured backend identity',
                                              hardware_evidence_available=False)
            case['rubric']['pipeline'] = 'Judge first_run, numeric and visual independently from compile; require actual command/artifact/log hashes and environment. Null unmeasured metrics. Blind condition labels before review.'
            cases.append(case)
    return {'schema_version': 1, 'annotation_status': 'REVIEW_REQUIRED_BEFORE_RELEASE', 'cases': cases,
            'baseline_file': 'cases-v1.0.6.json', 'baseline_sha256': BASELINE_SHA256,
            'baseline_case_count': 142, 'new_case_count': 30, 'new_case_range': ['A143', 'A172'],
            'model_calls': 0, 'paired_model_evaluation': 'BLOCKED_BY_PROVIDER'}

if __name__ == '__main__':
    (HERE / 'cases-v1.0.7.json').write_text(json.dumps(build(), indent=2, ensure_ascii=False) + '\n')
