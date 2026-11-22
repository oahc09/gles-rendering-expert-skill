# W2 / PR-02 device evidence adapter (first offline slice)

`benchmarks/device_lab/evidence_v112.py` reads raw stdout from a v1 device-lab
adapter (such as `0.stdout`, **not** the lab's derived `0.json` or a test
summary). It validates and preserves a relative evidence reference. It does
not invoke a collector or change the v1 lab, the Advisor, or any gate.

The versioned schemas below are intentionally limited to this device-lab
slice; the existing lab keeps its full precision, extension, format and
entry-point data in the original raw capture.

| Contract | Fields |
| --- | --- |
| `gles.device-evidence-ref/v1` | `schema`, relative raw capture `path`, byte `size`, lowercase raw `sha256`, `collector` (`device-lab`), `collector_version` (`1`), 40-hex `source_commit`, UTC `captured_at` (seconds plus Z), `origin` (`manual` or `runtime`), `platform`, `backend`, opaque host-assigned `device_id`, `scope` |
| `gles.device-evidence-expected/v1` | `schema`, expected `device_id`, `platform`, `backend`, `source_commit`, `scope`, `environment_sha256`, `max_age_seconds` (1 through 31 days), and `trusted_reference_sha256` (nullable) |
| `gles.device-profile/v1` | `schema`, `platform`, `backend`, `hardware_kind_reported`, `lab_fingerprint_sha256`, `environment_sha256`, `scope`, `build_binding`, `driver_version`, `abi`, `counter_measurements`, `performance_claim` |

`scope` is exactly `context_generation` and `surface_generation`, positive
integers or null (unknown). An opaque device ID identifies a lab assignment,
not a device identified by a renderer string. Compare expected device IDs,
capture scopes, source commits, and environment digests separately. For
example, the same renderer string with a different ID cannot pass as the
same assignment; a changed driver string or build component hash invalidates
the previous environmental match without deleting raw history.

`environment_sha256` hashes the stable legacy capability/environment fields
without the two generations, sorting exact extension tokens for order
stability. The original `lab_fingerprint_sha256` is kept separately without
changing legacy behavior. The collector does not provide an explicit ABI or
driver-version field; these are reported as `UNKNOWN`. A GL version string and
a callable function are not substitute evidence for a driver build or every
format/parameter combination. Counter telemetry is always `UNKNOWN` here.

## Run

```sh
python3 benchmarks/device_lab/evidence_v112.py \
  --root /path/to/evidence-dir --reference /path/to/reference.json \
  --expected /path/to/trusted-expectation.json
python3 -m unittest discover -s benchmarks/device_lab -v
```

The trusted host assembles expectations from an independently approved device,
environment and assignment log. For known runtime origin, the reference pin is
the SHA-256 from the existing `lab.digest(reference)` (sorted, compact JSON),
recorded separately from the supplied reference so origin, timestamp, scope,
source commit and raw byte hash cannot be relabeled later. Never derive a trust
pin from unreviewed input. The pin is a comparison value, not a signature,
physical attestation, proof of listed source bytes, or authorization.

A concrete simulated reference and expectation can be built with
`EvidenceTests.setUp` in `test_evidence_v112.py`; it includes an actual hashed
temporary capture and checks all admission fields. The POSIX verifier requires
no-follow, directory-relative file opens, and a trusted evidence-root parent.
Platforms lacking these capabilities fail closed. Capture files and metadata
are bounded; duplicate keys, nonfinite values, symlinks, hardlinks, invalid
paths, and mismatched size/hash are rejected. Keep raw storage host-controlled.

- `DECLARED_ONLY`: manual, or no separately trusted reference pin.
- `INSUFFICIENT_EVIDENCE`: pinned runtime, but backend/hardware/build/context
  evidence is unknown.
- `BOUND_SOFTWARE_CORRECTNESS`: bound, positive software capture; never physical.
- `BOUND_RUNTIME_REVIEW_REQUIRED`: bound and positive capture; requires
  independent runtime/hardware review. Even a physical label is unverified.
- `INVALID`: corrupt, expired, mismatched, failed or unavailable capture.

The public result never includes raw lab stdout, vendor/device strings, or
environment settings. It exposes the raw relative reference and digests for
reconciliation. Both physical acceptance and performance claims remain false
or unmeasured. W2 work still open: cross-platform collectors, standalone
driver and ABI capture, workload fingerprint, trace/runtime/quality/longrun
adapters, and integration with the decision layer.
