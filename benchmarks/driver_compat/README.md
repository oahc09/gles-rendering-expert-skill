# Conditional driver compatibility, W4

`compat.py` reuses DeviceLab `lab.validate` and its full snapshot/fingerprint. Do
not replace that snapshot with a phone model or a renderer substring. All five
identity fields (GL vendor, renderer, complete GL version/driver string, OS build,
backend) match exact allowlists; required/absent extension tokens are checked.
Wildcard renderer and contradictory predicates fail. Expired entries cannot apply.

`issue.schema.json` is the storage contract; `validate_issue` also requires a
reproducer, regression IDs, source, withdrawal condition, and before/after/raw hash
receipts for a confirmed entry. The evaluator **never automatically enables** an
entry. Even a confirmed match is only eligible for operator review. On a fixed
driver or failing counterfactual regression, withdraw the workaround, rerun the
original repro, and retain both captures rather than widening a blacklist.

`known-issues.json` intentionally has **zero newly confirmed driver bugs**. The
provided `test_compat.py` records are plainly synthetic identity/expiry tests, not
claims that Mali/Adreno/PowerVR/Vivante/ANGLE have a particular bug. Missing devices
remain BLOCKED/NOT_RUN. `software-probe.json` is an actual host llvmpipe EGL snapshot
and correctness run from the existing DeviceLab adapter, not a mobile result.

Reproduce:

```sh
GLES_SDK_ROOT=/path/to/sdk/usr python benchmarks/device_lab/host_adapter.py \
  <<<'{"platform":"host","backend":"software"}' > /tmp/software-probe.json
python -m unittest discover -s benchmarks/driver_compat -p 'test_*.py' -v
```

Before adding a real issue, keep a minimal executable reproducer under this
folder, exact failure criteria, source URL (vendor/upstream), matching raw capture
and fixed/fallback capture, hashes, regression command, expiration and explicit
withdrawal conditions. Device evidence is operator supplied, not attested; hash
presence does not prove the measurement's truth. No credentials are collected.
