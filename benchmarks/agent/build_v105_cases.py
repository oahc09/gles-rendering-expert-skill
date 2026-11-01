#!/usr/bin/env python3
"""Append annotated v1.0.5 tasks; never model responses or claimed executions."""
import copy
import hashlib
import json
from pathlib import Path
HERE=Path(__file__).resolve().parent
BASELINE_SHA256='ed0c31fc12b7523dd76433112ad4ea56705ee63e19dea268aa4942e8dc508fb8'
SOURCES={
 'thermal':'https://developer.android.com/games/optimize/adpf',
 'quality':'https://developer.android.com/games/optimize/adpf',
 'precision':'https://registry.khronos.org/OpenGL/specs/es/3.0/GLSL_ES_Specification_3.00.pdf',
 'resources':'https://registry.khronos.org/OpenGL/specs/es/3.0/es_spec_3.0.pdf',
 'trace_sql':'https://perfetto.dev/docs/analysis/trace-processor',
 'visual_tradeoff':'https://registry.khronos.org/OpenGL/specs/es/3.0/es_spec_3.0.pdf',
}
# Each topic contains Generate / Review / Diagnose / Optimize, not four paraphrases.
# Inputs explicitly describe hypothetical/synthetic scenarios, not measured device facts.
GROUPS={
 'thermal': [
 ('Generate','Design a reproducible 10-minute and 30-minute GLES LongRunCapture collector. Available inputs are frame timestamps and Android thermal status; calibrated power and GPU frequency are unavailable. Preserve missing measurements and distinguish cold versus steady-state runs.',
  ['monotonic-clock-and-window','frame-distribution-and-jank','thermal-metadata','missing-power-null'],
  ['A capture without a power meter can still report measured frame intervals.'],
  'Keep unavailable power/frequency null and collect a device trace before causal claims.','C10'),
 ('Review','Review this hypothetical report: average FPS fell after ten minutes; temperature was not captured; therefore thermal throttling is proven and our change saves 23% battery. The report contains no energy meter or repeated run.',
  ['unsupported-thermal-causation','unsupported-energy-percent','missing-repeat-and-clock-evidence'],
  ['Thermal throttling is a testable hypothesis, not a proven cause here.'],
  'Reclassify the cause as insufficient evidence and request temperature/frequency/timing measurements.','C10'),
 ('Diagnose','Synthetic classification exercise: capture A has one GPU-time spike after a texture burst and stable thermal/frequency tracks; capture B has sustained worsening frame p95 with rising thermal severity and falling clocks; CPU work stays similar. Give falsifiable classifications and missing confounders, without calling this real device evidence.',
  ['transient-burst-vs-sustained-pressure','thermal-clock-correlation-not-proof','timeline-and-confounders','synthetic-input-label'],
  ['A single upload spike need not be thermal throttling.'],
  'Use INSUFFICIENT_EVIDENCE when timing alignment or repeated controls are absent.','C10'),
 ('Optimize','Plan a device experiment for a game whose CPU and GPU timings are below frame budget but heat rises in a thirty-minute session. Compare ADPF hints, frame pacing and quality adjustments without asserting access to private vendor counters or precise power savings.',
  ['adpf-capability-gate','pacing-vs-workload-scope','steady-state-controlled-comparison','power-source-and-unknowns','rollback'],
  ['Lower average frame time alone does not establish lower energy consumption.'],
  'Keep the baseline policy disabled until measured stability and visual checks pass.','C10'),
 ],
 'quality': [
 ('Generate','Generate a deterministic quality-policy state machine NORMAL/PRESSURED/DEGRADED/RECOVERING using rolling frame p95, thermal input, hysteresis, minimum dwell, cooldown, user quality floor and an explicit disabled mode. Return recommendations, not driver-global switches.',
  ['deterministic-window-input','hysteresis-and-dwell','cooldown-and-rate-limit','quality-floor','disabled-no-change'],
  ['A public policy can recommend quality without directly changing GPU clocks.'],
  'Retain user-selected baseline and emit no changes when disabled or inputs are invalid.','C10'),
 ('Review','Review a synthetic dynamic-resolution controller that lowers scale whenever one frame exceeds 16.7 ms and raises it on the very next good frame, ignoring user minimum scale and thermal data. Suggest the minimal policy correction and a non-oscillation test.',
  ['single-frame-noise','missing-hysteresis-residency','quality-floor-violation','deterministic-replay'],
  ['A short load spike can be absorbed without permanent quality reduction.'],
  'Freeze the selected scale until a validated hysteresis window requests a supported change.','C10'),
 ('Diagnose','Synthetic replay: scale alternates 1.0/0.75 every two samples while p95 fluctuates near the threshold. Thermal input is unknown and the active scene changes midway. Identify which policy state and reset history must be logged before calling this GPU instability.',
  ['policy-oscillation-vs-driver','window-history-scene-boundary','unknown-thermal-not-zero','transition-timeline'],
  ['Unknown thermal data is not a cool-temperature observation.'],
  'Disable automatic transitions, replay the recorded inputs and compare with a fixed-quality baseline.','C10'),
 ('Optimize','Choose a recovery schedule after sustained pressure clears: possible controls are render scale, MSAA, shadow resolution and particle budget. Explain capability checks, staggered upgrades, visual acceptance and rollback rather than restoring all controls in one frame.',
  ['ordered-recovery-dwell','per-control-capability','visual-risk-and-floor','staggered-budget-validation','rollback'],
  ['An MSAA count is only usable when supported by the relevant format/render-target configuration.'],
  'Hold the last validated quality tier if any capability or visual gate fails.','C08'),
 ],
 'precision': [
 ('Generate','Generate a NumericErrorSpec and GLES test pair for long-running wave animation comparing a highp reference with a mediump candidate. Include fixed time samples, periodic phase strategy, numerical and temporal error tolerances, and actual shader precision queries; do not equate mediump with FP16 hardware.',
  ['range-and-time-error','reference-and-tolerance','temporal-sampling','precision-query-not-format-assumption'],
  ['A driver may implement mediump at higher precision than the minimum guarantee.'],
  'Keep highp for unstable phase calculations and validate any periodic phase reduction separately.','C11'),
 ('Review','Review this proposed rule: mediump always means IEEE binary16 and doubles shader speed on every GLES GPU; replacing every highp input is mandatory even for large world coordinates. No shader timing or visual reference is provided.',
  ['precision-minimum-not-fixed-format','universal-speedup-unsupported','large-range-error','measure-visual-and-time'],
  ['Selective highp is legal and may be necessary for range and stability.'],
  'Keep the reference precision until device-specific error and timing measurements justify selective reduction.','C11'),
 ('Diagnose','Synthetic color-regression case: a transparent layer matches its linear-light reference offscreen, but has incorrect brightness after display encoding is applied once in the shader and again by an sRGB output path. Trace encodings and blending order instead of changing the golden tolerance.',
  ['double-encoding-hypothesis','linear-blend-contract','attachment-and-display-colorspace','do-not-relax-golden'],
  ['An explicit shader encoding can be valid when the output path otherwise expects encoded values.'],
  'Use one documented encoding boundary and compare a known linear reference at each stage.','C11'),
 ('Optimize','A hypothetical water-normal optimization reduces arithmetic but causes highlight shimmer at selected animation times and banding in a smooth gradient. Propose selective precision recovery and numerical/temporal tests; no actual speed improvement has yet been measured.',
  ['temporal-artifact-rejection','selective-precision-recovery','gradient-and-highlight-masks','measure-before-speed-claim'],
  ['An arithmetic reduction is not proof of a mobile GPU speedup.'],
  'Restore the stable reference calculations for failing regions and retain the baseline until both gates pass.','C11'),
 ],
 'resources': [
 ('Generate','Generate an owner-thread, context-generation-tagged PBO transfer queue with bounded in-flight slots. A request can be canceled while its fence reports TIMEOUT_EXPIRED; show when publication is suppressed, when storage can be reused, and how WAIT_FAILED is handled.',
  ['cancel-not-gpu-undo','pending-slot-retention','owner-generation-check','bounded-inflight','wait-failed-not-complete'],
  ['A canceled already-submitted upload may still modify its target texture.'],
  'Stop new submissions and enter explicit recovery rather than recycling a slot with unknown completion.','C03'),
 ('Review','Review a synthetic resource report claiming zero real GPU VRAM usage and no driver leaks because application texture/FBO handle counts return to zero after 100 scene changes. Texture estimates ignore compression and alignment; no driver memory counters were captured.',
  ['owned-handles-not-driver-memory','estimate-not-residency','missing-driver-leak-evidence','scope-limited-pass'],
  ['Zero owned handles after cleanup is useful application-lifecycle evidence.'],
  'Report bounded owned-resource accounting and leave physical residency/driver leaks unmeasured.','C04'),
 ('Diagnose','After controlled context destruction/recreation, a logical texture still stores its old GLuint; the new context has reused that numeric name for another asset. Explain a generation-aware reproduction and CPU-descriptor rebuild without claiming Android EGL_CONTEXT_LOST was injected.',
  ['numeric-name-reuse','logical-handle-generation','cpu-descriptor-rebuild','controlled-not-device-loss'],
  ['Creating a new context is a valid recovery simulation, not proof of real Android loss handling.'],
  'Invalidate old-generation names and rebuild from retained descriptors on the owning context.','C04'),
 ('Optimize','Plan a low-memory response for an estimated texture budget with pinned essentials and LRU optional assets while PBO uploads remain in flight. The budget is full and no unpinned completed victim exists. Preserve correctness rather than pretending a portable free-VRAM query exists.',
  ['pinned-tier-and-lru','defer-or-reject-overbudget','inflight-consumer-lifetime','estimate-boundary','recovery-metadata'],
  ['Rejecting or deferring an optional upload is preferable to violating a hard engine estimate.'],
  'Drop optional requests and wait for safe retirement; keep pinned assets until a deliberate quality fallback is selected.','C03'),
 ],
 'trace_sql': [
 ('Generate','Generate a Perfetto Trace Processor SQL workflow that first inspects available tables/columns, then correlates render-thread scheduling with frame intervals. The input may omit GPU slices, temperature and frequency; output observations, missing fields and inference labels separately.',
  ['schema-discovery-before-query','clock-window-alignment','missing-columns-unknown','observed-inferred-separation'],
  ['A trace with CPU scheduling only can still support CPU observations.'],
  'Return UNKNOWN for unsupported attributions and preserve successful queries and raw rows.','C10'),
 ('Review','Review a synthetic SQL diagnosis that substitutes zero for a missing GMEM bandwidth column and concludes bandwidth dropped 25%. The trace has frame durations only. Specify a fail-closed correction and an assertion that prevents invented measurements.',
  ['missing-not-zero','unsupported-bandwidth-percent','query-provenance','insufficient-evidence-gate'],
  ['A measured frame-duration change can be reported without attributing it to bandwidth.'],
  'Keep bandwidth null/not-measurable and ask for a supported counter source before that attribution.','C10'),
 ('Diagnose','An offline trace-analysis CLI returns an empty result for both an honestly empty trace and a truncated/corrupt trace. Diagnose why returning PASS with zero jank is unsafe and define separate ingestion, SQL and coverage checks.',
  ['ingestion-error-vs-empty','no-samples-not-zero-jank','sql-exit-and-stderr','coverage-validation'],
  ['A valid empty dataset can be represented explicitly without fabricated performance metrics.'],
  'Fail malformed input; report insufficient evidence for valid traces without usable frame samples.','C10'),
 ('Optimize','Improve a synthetic Trace SQL report that joins every frame to all CPU-frequency rows, multiplying rows and exaggerating correlation. Propose time-window/interval joins, missing-coverage handling and validation against a hand-labeled fixture rather than asserting causation.',
  ['avoid-cartesian-duplication','interval-or-nearest-time-join','coverage-and-clock-validation','correlation-not-causation'],
  ['Temporal alignment may show association without proving a bottleneck cause.'],
  'Retain raw evidence and classify unknown when the trace cannot align the required intervals.','C10'),
 ],
 'visual_tradeoff': [
 ('Generate','Generate a golden-capture manifest and per-region comparison configuration for deterministic transparency, gradient, water highlight, HDR tonemap and scaled-rendering scenes. Record actual encoding, renderer, fixed seed/time and reference hashes; require both pixel error and structural checks.',
  ['golden-environment-metadata','fixed-seed-time','encoding-and-reference-hash','region-specific-thresholds','multiple-metrics'],
  ['Platform-specific tolerance may be justified when it is documented before observing a regression.'],
  'Keep the prior reference and require review rather than silently replacing a failing golden.','C07'),
 ('Review','Review a hypothetical visual gate: global SSIM exceeds 0.99, so a missing thin alpha edge and clipped highlights are accepted despite failing their region masks. The optimizer also edits the threshold to make its own result pass.',
  ['global-metric-hides-local-error','region-mask-gates','self-relaxed-threshold-invalid','reference-integrity'],
  ['High structural similarity does not guarantee all required pixels or temporal behavior are correct.'],
  'Reject the optimization and preserve independently specified tolerances/reference images.','C07'),
 ('Diagnose','Synthetic Pareto exercise: candidate A improves p95 but breaks a documented transparency-edge tolerance; candidate B preserves all visual limits but has overlapping timing distributions; power data are absent. Explain which conclusions are supportable without inventing a winner or energy saving.',
  ['visual-failure-veto','timing-uncertainty','power-unknown','pareto-not-single-fps'],
  ['An inconclusive timing comparison is not evidence of regression or improvement by itself.'],
  'Keep the baseline and repeat controlled timing while rejecting the visually invalid candidate.','C07'),
 ('Optimize','Design a safe acceptance procedure for a thermal-constrained bloom change using lower-resolution intermediate targets. Specify repeated steady-state frame distributions, highlight/gradient tolerances, allocation estimates, rollback and treatment of unavailable power measurements.',
  ['steady-state-repeated-timing','highlight-gradient-visual-floor','format-and-budget-check','unmeasured-power-null','rollback'],
  ['Lower-resolution intermediates can be a candidate, but are not automatically visually acceptable.'],
  'Restore baseline bloom when visual or stability thresholds fail, regardless of an isolated FPS gain.','C07'),
 ],
}

def build():
    path=HERE/'cases-v1.0.4.json'
    if hashlib.sha256(path.read_bytes()).hexdigest()!=BASELINE_SHA256:
        raise ValueError('Frozen v1.0.4 corpus changed; inspect/review baseline before rebuilding')
    baseline=json.loads(path.read_text());cases=copy.deepcopy(baseline['cases'])
    if len(cases)!=88 or [c['case_id'] for c in cases]!=[f'A{i:03d}' for i in range(1,89)]:
        raise ValueError('Expected exact A001–A088 predecessor corpus')
    template=baseline['cases'][0]
    for topic,rows in GROUPS.items():
        for mode,prompt,findings,controls,fallback,core in rows:
            case=copy.deepcopy(template)
            case.update(case_id=f'A{len(cases)+1:03d}',mode=mode,prompt=prompt,core_case=core,
                severity='high',expected_findings=findings,legal_controls=controls,fallback=fallback,
                evidence_sources=[SOURCES[topic]],
                compile_evidence={'required':mode=='Generate','artifact':None,'status':'NOT_RUN'},
                v105={'topic':topic,'annotation_status':'REVIEW_REQUIRED_BEFORE_RELEASE',
                      'prompt_origin':'authored scenario; hypothetical inputs are not device observations',
                      'model_calls':0,'model_quality':'NOT_EVALUATED',
                      'visual_safety_required':topic in ('quality','precision','visual_tradeoff')})
            case['device_capabilities']={'gles_version':'3.0','glsl_version':'300 es','platform':'Android / native GLES / ANGLE: actual backend must be supplied','extensions':'unknown: must probe','renderer':'unspecified: do not infer','hardware_evidence_available':False}
            case['forbidden_advice']+=['Treat synthetic input or host GL as measured mobile performance.','Turn missing power/memory/counter measurements into zero or fabricated percentages.','Relax visual acceptance criteria solely to pass an optimization.']
            case['rubric']['visual_safety']='Reject changes that fail independently specified visual limits; record unknowns and preserve baseline rollback.'
            cases.append(case)
    if len({c['prompt'] for c in cases})!=len(cases):raise ValueError('Duplicate prompt')
    return {'schema_version':1,'annotation_status':'REVIEW_REQUIRED_BEFORE_RELEASE','cases':cases,
            'baseline_case_count':88,'baseline_sha256':BASELINE_SHA256,'baseline_file':'cases-v1.0.4.json',
            'new_case_range':['A089','A112'],'new_case_count':24,'new_topics':list(GROUPS),
            'model_calls':0,'paired_model_evaluation':'NOT_RUN_PROVIDER'}

if __name__=='__main__':
    (HERE/'cases-v1.0.5.json').write_text(json.dumps(build(),ensure_ascii=False,indent=2)+'\n')
