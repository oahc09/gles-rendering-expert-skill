# v1.0.5 annotated Agent corpus — not a model evaluation

`cases-v1.0.5.json` appends A089–A112 to the **unchanged** 88-case v1.0.4
prefix. The previous corpus and its original 64-case source are not rewritten.
`build_v105_cases.py` checks the frozen predecessor SHA256 before generating the
new file; updating that baseline requires explicit review, not silent migration.

| New IDs | Topic | Modes |
|---|---|---|
| A089–A092 | Thermal degradation versus transient pressure | Generate, Review, Diagnose, Optimize |
| A093–A096 | Adaptive-quality hysteresis and recovery | Same four modes |
| A097–A100 | Precision and color correctness | Same four modes |
| A101–A104 | Residency estimates, uploads and context generations | Same four modes |
| A105–A108 | Trace SQL missing fields and attribution | Same four modes |
| A109–A112 | Visual acceptance versus performance claims | Same four modes |

Every new task has expected findings, legal controls for false-positive scoring,
forbidden advice, capability assumptions, fallback and primary-source references.
Hypothetical input data are explicitly not measured device evidence. Annotations
remain **REVIEW_REQUIRED_BEFORE_RELEASE**; no response, compile score, device
measurement, accuracy gain or false-positive improvement is fabricated.

Use the existing runner and scorer, not another framework:

```sh
python benchmarks/agent/build_v105_cases.py
python -m unittest discover -s benchmarks/agent -p test_v105_cases.py -v
python benchmarks/agent/run.py --cases benchmarks/agent/cases-v1.0.5.json \
  --output /tmp/new-gles105-paired-run
```

Without an explicitly configured authorized provider adapter, the last command
exits **2 / BLOCKED_BY_PROVIDER** and records zero responses. A real paired run must
record actual provider/model configuration and be independently adjudicated using
the existing score workflow. Ground-truth labels, controls and rubric are withheld
from model requests. Infrastructure tests do not measure model quality.

`baseline-status/v1.0.5/summary.json` records the actual no-provider invocation:
112 selected cases, zero model calls/results, `model_quality=NOT_EVALUATED`.
The v1.0.5 labels add visual safety to the rubric; scoring a release still needs
human evidence that the model respected independently defined visual limits rather
than merely mentioning them.

The existing scorer now aggregates optional independent review booleans
`root_cause_hit`, `evidence_sufficient`, `visual_safe`, `wrong_advice` with separate
reviewed denominators and null when unreviewed. The last three require individual
rationales; visual safety also needs an independently defined
`visual_criteria_reference`. This is human-adjudicated correctness, not automatic
keyword truth or device-image validation. The CLI still binds corpus/response
hashes and actual compile/regression artifacts. Arithmetic unit fixtures are not
paired model-quality evidence.
