# Preserve live attachment contents before ranking experiments

`gpu_decision_v111.py` accepts the same file and stdin request forms. An old
positive `discard-dead-attachment` Boolean is not sufficient on its own; the
reply stays `PROBE_REQUIRED` and the fallback is to retain the original store.
This behavior is deliberately stricter without breaking request parsing.

The optional `workload.discard_scope` provides an existing baseline lifecycle
(`attachments` and `lifecycle` in the finite attachment model), the attachment ID,
zero-based `end_event` at which it is stored, and `complete` (a caller
declaration, not device evidence). The advisor first checks the baseline, then
replays the same modeled events replacing only that store with discard. If a
later load or consume needs the same contents the candidate is blocked; a full
clear and subsequent store can define new contents. Show later sample,
readback, presentation and cross-pass uses as consumers; put in-pass resolves
at their actual position. If a dependency cannot be expressed in this finite
model (including external ownership or unresolved aliases), mark the trace
incomplete and preserve contents. A separate correctness probe is still
required: no sample or readback of undefined contents is executed.

`MODEL_NO_CONSUMER` means only the declared graph was replayed, not that a trace,
driver, physical device or speedup was verified. It permits an experiment only;
it never executes or applies changes. The new policy revision changes the
decision hash.
