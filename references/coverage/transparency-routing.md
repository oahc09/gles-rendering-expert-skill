# Finite transparency diagnostic routing integration

This is W7 host-representative integration using existing collectors, and W8-style evidence binding. It is **not** a generic production renderer, complete scene matrix, or Registry semantic closure. No old failed evidence or global release status is changed.

## What actually executes

`benchmarks/coverage/transparency-routing/run.py` freezes the existing weighted-OIT, exact sorted replay, exact-order policy and depth-peeling sources by SHA256, plus the shared differential Host and its direct repository imports (shader_fuzz, pipeline runtime and reducer). This is a bounded source-drift check, not a complete runtime or driver-binary attestation. It launches the three collectors in separate processes using one explicitly provided driver config, captures fresh complete reports, exit codes, raw artifact hashes and canonical JSON-body hashes, then performs routing. There is no input-provided executable command and no network or SDK step.

Because existing collectors execute their full fixed suites, **all** diagnostic costs are counted: each Mesa/ANGLE integration run performed278 draws,65 readbacks and38 occlusion queries. It does not claim to lazily render only the selected case. Inputs are a closed five-scene registry (constant, sloped, crossing2, crossing3, ties); changed plane/color/ID data or arbitrary meshes are not silently mapped to another scene's pixels.

## Decision chain

1. Validate exact request schema, registered full geometry, layer budget1–3 and quality bound0–2bytes. Requests allowing approximation are explicitly unsupported, not permission to substitute an unvalidated approximation.
2. Consume fresh weighted-OIT evidence as a rejected/limited candidate audit. **Its two original workloads differ from this routing registry**. They are marked NOT_APPLICABLE_DIFFERENT_REGISTERED_INPUTS; their pixels are never reused for a crossing or sorted request. This step preserves the prior approximation failures; it is not a new same-input OIT benchmark.
3. Apply existing exact-order policy to complete derived per-pixel depths. If global ordering is valid, require a matching actual sorted replay scene, exact plane/color/depth arrays and far-to-near draw order, then independently compare captured pixels.
4. For crossing only, require existing dyadic depth-domain validation, matching complete depth-peeling input layers, an actually captured budget and intended input order. Inspect the real K+1 query results and reject residual layers. Unknown budgets are unavailable rather than fabricating a shorter/longer run.
5. Independently compute per-pixel analytic OVER in the adapter and apply the user's requested byte threshold to full64-byte readback. A stricter0-byte request rejects the observed1-byte peel result. Ties, failed capability execution, wrong source/hash/body/input/budget and missing capture never trigger approximate fallback.

## Actual results

Both software drivers produced:

| Request | Result |
|---|---|
| constant/sloped, budget2, tolerance2 | SORTED_ALPHA; error0 |
| crossing2,budget2 / crossing3,budget3,tolerance2 | DEPTH_PEELING; error1 |
| crossing3,budget2 | UNAVAILABLE; actual extra-pass overflow |
| crossing2,budget1 | UNAVAILABLE; that budget was not captured |
| crossing3,budget3,tolerance0 | UNAVAILABLE; quality not met |
| ties | UNAVAILABLE; ambiguous order |

Each collector exited0; each integrated default-suite CLI exited0 with `HOST_ROUTING_PASS` only after checking the four required accepted routes and four required rejections. An accidental all-UNAVAILABLE regression fails this separate contract and exits nonzero. Custom requests instead receive `EXECUTED_FINITE_ROUTING` with per-request outcomes, not default-suite acceptance. Neither status means all requested inputs are accepted. Archived files in `mesa-final/` and `angle-final/` retain all collector results and binding receipts. Local `read_bundle()` verifies path containment and original file/body hashes before replaying a decision. Hashes establish consistency with the local capture, not cryptographic authentication against an attacker who can rewrite both artifacts and trusted receipts.

## Scope and remaining boundaries

Only fixed full-coverage4×4 analytic planes, independent straight RGBA, transparent-black background and supported software GLES paths are covered. Complete depths come from this trusted fixture definition, not arbitrary scene capture. No claim of universal mesh/provenance verification, mobile bandwidth win, dynamic-scene correctness, device/provider acceptance or complete W7/W8 closure. Existing sorted fallback remains unavailable for ties/crossings unless the separately validated peel path and actual budget meet the request.

```sh
python3 benchmarks/coverage/transparency-routing/run.py --config DRIVER_CONFIG.json --output NEW_RESULT_DIRECTORY
# Optional --requests JSON must contain only supported registered request objects.
python3 -m unittest discover -s benchmarks/coverage/transparency-routing -p 'test_*.py' -v
```

Seventeen tests cover actual route results, geometry/schema/budget/quality mutations, hash/body/file drift, frozen source drift, collector failure, unsupported peel, and prohibition on relabeling weighted inputs. Malformed receipts/bundles fail safely; tests additionally reject all-UNAVAILABLE default-suite regressions. No old collector was changed to obtain these outcomes.
