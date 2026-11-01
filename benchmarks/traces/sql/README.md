# v1.0.5 Trace SQL adapter

Entry point: [`adapter.py`](adapter.py). Detailed usage and evidence boundaries:
[`references/playbooks/trace-sql.md`](../../../references/playbooks/trace-sql.md).

* `templates/*.sql` + `queries.json`: ten schema-probed observation templates.
* `fixtures/cases.json`: seventeen labeled normalized SQLite fixture definitions.
* `fixtures/build_native.py`: deterministic original TrackEvent protobuf builder.
* `fixtures/native-compile-hitch.pftrace`: synthetic native trace, MIT; no captured user data.
* `fixture-validation.json`: separate SQLite/native-processor outcomes and FP/FN/abstentions.
* `native-validation/`: actual v59.1 native parsing/SQL evidence and v1.0.4-compatible exported metrics.
* `perfetto-tool-receipt.json`: official release date, downloaded asset digest and executable identity.

No processor binary is committed. Do not call SQLite fixture results native trace processing,
and do not call native processing of synthetic packets a physical-device result. The repository
has no measured phone thermal/power/private-counter data from this work package.
