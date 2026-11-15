# Center-camera intermediate stage diagnosis

`far_stage_probe.py --config DRIVER --output REPORT` subclasses the existing
bilinear reconstruction host without replacing any shader or draw. Two blocking
readbacks are inserted: far32 before switching FBO; resolve64 before foreground
blend. The existing final readback is retained. Deterministic ZIP stores all three
actual and all three independent CPU images. Tests confirm final pixels exactly
match the already retained non-instrumented run for both tested drivers.

At zero-based bottom-up(29,24), no foreground contributes. The four actual
far32 alpha samples differ in one place: Mesa(15,12)=14; CPU and ANGLE=13.
Other alpha samples are6,6,15. Weights3/16,1/16,9/16,3/16 produce CPU/ANGLE12.375
but Mesa12.5625. Actual resolve then gives12 versus13, unchanged by foreground.
Thus the extra threshold crossing already has a sufficient explanation in the
far32 blend output in this captured run; it is not necessary to invent a
resolve-only error. The stage probe does not identify which individual blend
operation or implementation precision choice produced that intermediate code.

CPU reference derives low pixels analytically and performs explicit weighted
interpolation, independent of actual low pixels. A separate stage-consistency
check interpolates actual low bytes: that is a pipeline diagnostic, **not** the
independent visual golden. Across the full output its discrepancy must be≤1;
at the diagnosed point the predicted byte must match actual resolve exactly,
and foreground must preserve it. HOST_PASS only denotes these diagnostic checks.
Original silhouette budget2, alpha threshold>12 and visual acceptance are unchanged.

Three readbacks introduce synchronization and are not performance measurements.
These are software observations, not a vendor-wide conclusion. Normalized
conversion and blend arithmetic need not be uniquely modeled by our CPU half-up
rounding; this result alone does not establish a specification violation.
