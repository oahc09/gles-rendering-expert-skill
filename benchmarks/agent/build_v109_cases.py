"""Append workload optimization tasks to preserved v1.0.7 paired-runner corpus."""
import copy
import json
from pathlib import Path
HERE=Path(__file__).parent
TASKS=[
('Diagnose','CPU and GPU intervals overlap: CPU submit 7ms, GPU 8ms, frame 10ms. Explain why summing them gives the wrong critical path.','overlap-not-additive'),
('Diagnose','GPU utilization is 99%, but no counters or stage traces are available. Classify bottleneck uncertainty and next capture.','utilization-not-root-cause'),
('Diagnose','CPU trace is CLOCK_MONOTONIC, GPU timestamps use an uncalibrated device clock. Align or refuse temporal correlation.','clock-domain-calibration'),
('Diagnose','Frame p95 grows during thermal throttling while draw count stays constant. Isolate frequency and temperature effects.','thermal-confounder'),
('Diagnose','Texture upload stalls coincide with CPU memcpy; GPU timer excludes upload. Design attribution instead of calling it fragment ALU.','upload-attribution'),
('Generate','Design interleaved shader A/B experiments with warmup, p50/p95, disjoint queries and stable temperature.','controlled-ab'),
('Generate','Emit a highp versus mediump GLES shader experiment with large world coordinates and overflow counterexample.','precision-quality-gate'),
('Generate','Build branch versus branchless shader controls where branchless evaluates both expensive paths.','branchless-negative-control'),
('Generate','Plan a GLES 3.0 UBO baseline and a GLES 3.1 SSBO comparison; keep unsupported hardware fallback explicit.','ssbo-version-boundary'),
('Generate','Build texture-fetch coalescing experiment with derivative-sensitive mip sampling as a negative control.','derivative-equivalence'),
('Review','A tile model assumes every mobile GPU has 16x16 tiles and claims calculated bytes are actual DRAM traffic. Correct it.','estimate-not-dram'),
('Review','A pass discards its color attachment before a later postprocess samples it. Review the optimization.','discard-after-last-use'),
('Review','A fusion candidate samples the same texture it currently writes. Explain feedback and preserve ping-pong.','reject-feedback'),
('Review','An MSAA resolve changes size and switches NEAREST to LINEAR. Validate resolve before comparing performance.','resolve-legality'),
('Review','A transient alias overlaps an asynchronous readback still in flight. State lifetime and fence requirements.','external-lifetime'),
('Optimize','Gaussian proxy LOD removes background splats but breaks foreground silhouettes during camera motion. Propose quality tests and reject current patch.','dynamic-silhouette'),
('Optimize','Sorting glass by material reduces draw calls but reverses alpha blending order. Preserve transparent compositing.','transparent-order'),
('Optimize','Particle batching halves draw count but leaves projected coverage unchanged. Separate CPU savings from overdraw hypotheses.','draw-not-coverage'),
('Optimize','Downsample volumetric proxy rendering: evaluate depth discontinuities and temporal ghosting before accepting.','volume-edge-temporal'),
('Optimize','UI layers contain premultiplied colors but optimized blend state assumes straight alpha. Supply regression and fallback.','premultiplied-alpha'),
('Diagnose','ASTC asset is smaller on disk but CPU transcode and upload increase frame p95. Evaluate end-to-end cost.','compression-not-runtime-gain'),
('Generate','Design atlas versus texture-array A/B with border bleeding, mip chain and GLES limits.','atlas-border-controls'),
('Review','PBO upload overwrites an in-flight buffer region. Specify synchronization and baseline fallback.','pbo-lifetime'),
('Optimize','Reducing texture resolution saves resident bytes but destroys thin normal-map highlights. Apply perceptual quality budget.','normal-quality-budget'),
('Review','Anisotropy extension is absent on target device. Reject unconditional extension use and compare legal mip fallback.','extension-probe'),
('Review','One Adreno driver improves a shader by 8%; report proposes all Mali/Adreno devices switch. Bound policy by exact identity.','no-family-generalization'),
('Diagnose','Optimized p50 improves but p95 and energy worsen. Explain the multi-objective regression and rollback decision.','negative-gain-rollback'),
('Generate','Create evidence manifest binding scene/build/source hashes to raw trace, device, driver, temperatures and image thresholds.','evidence-binding'),
('Review','A fixture response is labelled a real provider gain and missing power is filled with zero. Reject both claims.','fixtures-not-provider'),
('Optimize','A candidate passes compilation but has no numerical output or GPU capture. Choose experiment status, not verified improvement.','compile-not-acceptance')]


def build():
    payload=copy.deepcopy(json.loads((HERE/'cases-v1.0.7.json').read_text()))
    baseline=len(payload['cases'])
    for i,(mode,prompt,finding) in enumerate(TASKS,1):
        payload['cases'].append(dict(case_id=f'A{baseline+i:03}',mode=mode,prompt=prompt,
          device_capabilities=dict(gles_version='3.0',glsl_version='300 es',platform='Android/ANGLE/Embedded Linux',extensions=[],renderer=None,hardware_evidence_available=False),
          core_case=f'C{1+(i-1)%12:02}',severity='high',expected_findings=[finding],
          legal_controls=['unchanged legal baseline is permitted'],forbidden_advice=['Claim measured gain without matched raw device evidence'],
          fallback='Preserve original validated renderer; mark unknown measurements null.',
          evidence_sources=['docs/v1.0.9/development-plan.md'],compile_evidence=dict(required=False,artifact=None,status='NOT_RUN'),
          rubric=dict(accuracy='Independent reviewer checks expected finding against raw response',false_positive='Do not reject legal baseline',debug_steps='Reproducible diagnostic evidence required',performance='No prediction may substitute measured device A/B'),v109=True))
    payload['annotation_status']='REVIEW_REQUIRED_BEFORE_RELEASE'
    return payload

if __name__=='__main__':
    (HERE/'cases-v1.0.9.json').write_text(json.dumps(build(),indent=2)+'\n')
