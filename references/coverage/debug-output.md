# Bounded GLES core / KHR debug-output semantics

Primary source actually read: [fixed KHR_debug specification](https://raw.githubusercontent.com/KhronosGroup/OpenGL-Registry/1cdd228e34966dd6b95bd203e9f84faba0f371a1/extensions/KHR/KHR_debug.txt), ES entrypoint naming, callback/log behavior, message filtering, groups and labels. Source revision/hash is retained in `benchmarks/coverage/debug-output/source.json`; full specification prose is not vendored. Core naming is admitted only at queried GLES3.2, not because a pointer happens to exist.

## Actual bounded path

- Mesa queried GLES3.2 and uses **only unsuffixed core** debug entrypoints. ANGLE queried GLES3.1 with GL_KHR_debug and uses **only KHR-suffixed** debug entrypoints, including GetPointervKHR. Every exact route entrypoint must resolve or the test fails; aliases are not silently substituted.
- Disable DEBUG_OUTPUT and disable **all** message categories before registering callback. Enable only DEBUG_SOURCE_APPLICATION messages. Enable synchronous output, then explicitly insert known experiment messages. No driver/system/compiler category is enabled or harvested.
- Callback/user token are strongly retained Python objects until unregister. Callback does not call GL/window-system functions. It reads message bytes only if source is APPLICATION, ID is from the experiment allowlist, and length matches the known expected text; only exact matching text is archived. Other content is discarded without publication.
- A known inserted message is observed before the insertion returns, validating the synchronous path. Function/user pointer queries are checked for equality and published only as booleans, never addresses.
- Disable one application ID and independently disable HIGH severity. Those insertions do not reach callback; LOW does. Push group creates an application group message; disable LOW within the group, verify suppression, pop restores the inherited filter state, and LOW insertion is delivered again. Stack-depth query is1→2→1.
- Label a real bound buffer with the experiment-owned string; full query returns19 characters. A6-byte destination truncates to5 characters and terminates with NUL. No uninitialized object or invalid pointer is used.
- Finish, explicitly unregister callback and user token, verify both queried pointers are NULL, and insert another known message without invoking callback. Then disable debug output/categories, delete the owned buffer and destroy the context. This checks normal cleanup, not crash/reentrancy/context-loss behavior.

Exactly5 application callbacks per driver were observed in order:901,904,905(push),905(pop),907. Filtered902/903/906 and post-unregister908 do not appear.

## Defined error controls

Both actual drivers returned the specified errors:

| Operation | Error |
|---|---|
| ID filter with wildcard source | INVALID_OPERATION |
| Debug insertion with API source instead of application/third-party | INVALID_ENUM |
| Pop initial group | STACK_UNDERFLOW |
| Object label unknown identifier | INVALID_ENUM |
| Object-label query negative buffer size with valid backing memory | INVALID_VALUE |

No undefined invalid pointer, deliberate crash or real context reset is used. API-source error messages remain filtered; only glGetError numeric codes are archived.

## No-extension fallback and evidence limits

A capability decision with neither GLES3.2 nor GL_KHR_debug returns no route. The same fallback is actually exercised on both hosts through explicit `--disable-debug`: it makes **zero debug-function calls**, renders/readbacks a known red RGBA8 image and checks GL errors. These forced-off runs do not pretend the hosts lack their advertised extension. A genuinely unsupported target remains untested.

Both normal CLIs exit0 `HOST_PASS`; both forced-off CLIs exit0 `SAFE_FALLBACK_PASS`. Eight tests validate exact callback sequence, filtering, group queries, label truncation, error controls, unregister semantics, capability gates, all four actual reports and sanitization.

Contexts are not requested as debug contexts. Automatic driver diagnostics are not guaranteed there and are **not** acceptance requirements. This experiment tests explicitly inserted application messages and group/label API semantics, not driver log completeness. No full log retrieval, driver strings, shader compilation diagnostics, OS fingerprints or callback addresses are published. Multi-thread asynchronous callbacks, concurrent contexts, driver-generated errors, robust-reset lifetime and physical-device behavior remain NOT_RUN.

```sh
python3 benchmarks/coverage/debug-output/run.py --config DRIVER_CONFIG.json --output REPORT.json
python3 benchmarks/coverage/debug-output/run.py --config DRIVER_CONFIG.json --output DISABLED_REPORT.json --disable-debug
python3 -m unittest discover -s benchmarks/coverage/debug-output -p 'test_*.py' -v
```

This adds a finite W4 semantic representative; it does not convert indexed extension coverage into full validation, change global release gates, accept SDK terms or claim performance benefit.
