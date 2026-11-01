# Trace SQL diagnosis

Status: EVIDENCE_AVAILABLE

## Observed
- render_thread (query render_thread)
- shader_compile (query shader_compile)
- frame (query frame)

## Inferred hypotheses (not causes)
- shader_compile_hitch: Warm identical programs before replay; compare compile-event alignment with frame spikes.

## Unknown / excluded claims
- Private GPU bandwidth/GMEM percentages, watts and energy savings are not derived from these traces.

## Next experiment
Repeat matched workload with synchronized CPU/GPU/thermal capture and visual correctness; do not infer private counters or energy savings.
