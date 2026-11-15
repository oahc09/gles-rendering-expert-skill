# Adversarial overlay on v1.0.7

`check.py` imports the existing graph/material/hazard/variant validators. It adds
24 graph and24 ABI mutations,10 producer/consumer barrier controls,explicit
cross-context synchronization proof and bounded graph reduction using v106 ddmin.
Alias requests form allocation-equivalence classes;every pair in a class must
have compatible storage and all uses ordered through explicit DAG reachability.
An arbitrary topological ordering alone cannot prove safe reuse.

`synchronization_proof` requires write→fence→producer flush→consumer wait→rebind→
read for the same object generation/fence and share group. This is a static
contract,not proof of runtime fence completion or intra-workgroup race freedom.
The existing hazard checker separately selects barriers for actual consumers.

`runtime.py` executes existing S03 baseline/injected paths,validates real linked
reflection and independent pixels,then applies authored ABI metadata deltas to
that captured baseline.24 replays are not24 distinct driver executions.

```
python3 benchmarks/pipeline/adversarial/check.py --output reports/adversarial
python3 -m unittest discover -s benchmarks/pipeline/adversarial -v
sh examples/pipeline/build.sh
python3 benchmarks/pipeline/adversarial/runtime.py --output reports/adversarial-runtime
```

Malformed/subrange/undefined accesses are rejected before GPU consumption.
Reduced graphs preserve an exact error rule within fixed-resource pass deletion;
one-minimal never means globally or semantically smallest.
