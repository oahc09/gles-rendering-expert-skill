# Finite EXT timer query semantics

```sh
python3 benchmarks/coverage/timer-query/run.py --config DRIVER.json --output REPORT.json
python3 benchmarks/coverage/timer-query/run.py --config DRIVER.json --output DISABLED.json --disable-timer
python3 -m unittest discover -s benchmarks/coverage/timer-query -p 'test_*.py' -v
```

Mesa and ANGLE software hosts both advertised EXT_disjoint_timer_query, reported elapsed/timestamp counter widths 64, and passed actual query lifecycle + six specification-defined negative calls. Four captured CLI runs exited 0, eight tests passed. Exact EXT entrypoints only: no core-alias guessing.

Create four names, timestamp-before, elapsed begin around bounded red FBO clear/readback, elapsed end, timestamp-after. Three actual query results are read through ui64 only after availability TRUE (at most 100 polling attempts at 1 ms intervals; glFlush and driver calls themselves are not wall-clock bounded). The first availability probe and the final available_at_result_read admission are recorded separately. Available-after-result and query deletion are verified. This is a correctness diagnostic, not a nonblocking production collector. A zero-bit counter is legal but not useful and takes safe fallback. Although nonzero timer widths of at least 30 bits are specification-legal, this combined experiment accepts only the tested 64-bit domain. Widths 30–63 take safe fallback because elapsed overflow leaves results undefined and requires an additional bounded-duration proof. Even 64-bit admission is a finite short-workload assumption, not a general overflow guarantee.

GPU_DISJOINT is read before and after, covering events since its preceding read. Either true or unknown rejects timing interpretation conservatively. Current actual runs were false/false. Injected true/unknown cases are **pure policy simulations**, not induced GPU events. Raw elapsed/timestamp values stay in process and are not archived; no CPU/GPU ratio, elapsed-vs-timestamp equality or performance improvement is inferred. Timestamp nondecreasing is checked only for accepted short finite samples, not wraparound-proof general scheduling. Physical timing/thermal stability remains NOT_RUN.

Negative cases: nested active same target, result access while active, QueryCounter on active object, ending inactive target, invalid counter target, zero Begin id. All six return the specified errors. Reading an ended but not-yet-available result is **not** treated as illegal; it may block, so this collector waits first.

Disabled fallback performs actual FBO pixel verification with zero timer entrypoint calls; it is a policy-off test, not evidence a runtime lacks the extension. Unsupported extension uses the same fallback branch but neither current driver lacked it. Missing advertised entrypoints fail closed. No extension strings, system logs, raw timing values, paths, driver/library fingerprint, or device claim are published. Source hashes establish drift checks, not trustworthy third-party execution authentication.

See source.json for pinned primary specification and references/coverage/timer-query.md for review mapping. No full spec text redistributed.

The collector uses glFlush rather than glFinish before availability polling. Elapsed must be uint64 and not saturated UINT64_MAX, or interpretation is rejected. This is not a sufficient overflow proof: overflow may wrap or be undefined without saturation. Acceptance is named API_DISJOINT_CHECKS_PASS_OVERFLOW_NOT_PROVEN and remains limited to this short workload; no reliable general timer or physical measurement guarantee.
