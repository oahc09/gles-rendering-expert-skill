# v1.1.2 PR-01 baseline

The parent tree is `cefb240d1793a4dc98174230aea15b6e0889905b` (merge of
v1.1.1 candidate PR #9). The checked-in v1.1.1 gate is PARTIAL_CANDIDATE, not
a release. This PR-01 slice does not change published metadata or historical
records. Existing workpack and follow-up snapshots remain byte-bound.
The v1.1.1 workpack mapping follows the v1.1.2 plan; older gates and follow-up
status entries are kept under W0/W8 for explicit closure review, not waived.

Run `python tools/check_v112_baseline.py` and
`python tools/validate_rules.py --v112`. The first checks preserved archives,
indexed obligations and original numeric targets. It does not close any
obligation. The second checks exact entry mappings and positive/negative
normalized rule behavior, not compiler, GPU, device, or model conformance.
The [rule index](rule-index.json) maps six F01 conflict families to primary
specifications and existing rule IDs; [cases](rule-cases.json) cover the
corresponding V112-R01–R06 concepts without replacing the prior test catalog.

## Closure contract (not yet enabled)

Future closure receipts must identify the obligation, exact candidate commit,
new run ID/time, collector version, environment and scope, raw artifact hashes
and independent reviewer disposition. The archive is not a new current-HEAD
run. A passing fallback or software run cannot close a hardware, driver, model,
or original-path obligation. The current validator rejects all attempted
closures and any release claim. Technical readiness and release authorization
remain separate.
