# Bounded robustness and failure isolation

35 executable unit cases exercise texture dimensions, integer/type/overflow
checks, 1 MiB total owned-resource quota, 64 KiB shader input cap, strict UTF-8
and NUL rejection, dispatch workgroup quota (4096 groups, each dimension <=64),
raw RGBA size/decode validation, cancellation, release idempotence, cleanup on
quota failure/exception/timeout, and controlled retry (maximum three attempts).
These are conservative harness admission limits, not queried device limits.
They do not prove arbitrary shader termination or safe physical GPU stress.

Actual subprocess timeout/exit/signal cases test classification; a terminated
Python child is not a driver crash. The cooperative worker has bounded event wait
and join. No unbounded GL allocation, dispatch, shader loop or glFinish loop runs.
Resource accounting is an executable CPU ownership model, not a GPU-memory meter.
Reset recovery is simulated and explicitly labeled, never physical device reset.

`policy.py` exposes EXPECTED_ERROR, UNDEFINED, IMPLEMENTATION_DEPENDENT,
TEST_TIMEOUT, HARNESS_FAILURE, DRIVER_FAILURE, UNSUPPORTED and CANCELLED.
DRIVER_FAILURE requires a signal plus separately established driver evidence;
normal test failures/timeouts cannot establish it. Driver evidence is a caller
assertion and must be supported by a reviewed crash artifact, not merely an exit
code. No current fixture is evidence of a real driver fault.

```
python -m unittest discover -s benchmarks/robustness -v
python benchmarks/robustness/run.py --output /tmp/gles-w23 --gles-library /path/to/libGLESv2.so.2
```

Runner writes JSON and Markdown, source hashes, per-case results and actual driver
identity/extensions. `--no-host` preserves UNSUPPORTED and INCOMPLETE, never PASS.
Host process wall budget is 30 seconds. The shared W1 runner kills its process
group on every exit (success, failure and timeout) and reaps the leader.
Children inherit CPU, address-space and file-size quotas; logs are file-backed
and bounded to 64 KiB. Policy default memory is 512 MiB, host Mesa gets 4 GiB.
Descendant marker regressions cover all exits, and output/memory quota tests
exercise actual subprocesses. These limits are not a hostile-code sandbox; a
malicious process can escape its process group, and quotas are per-process.
The parent reuses the existing v1.0.6 reducer and adds no competing reducer.
Current host evidence is Mesa llvmpipe only; hardware reset/recovery acceptance
remains BLOCKED_BY_HARDWARE and is not authorized by these scripts.
