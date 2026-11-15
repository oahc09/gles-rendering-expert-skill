# Original-plan candidate contract index

`index.json.gz` is a deterministic, sorted normalized view of all 1,319 candidates
in the existing 2026-08-18–2026-11-15 radar archive. The original archive is unchanged.
`index.json.receipt.json` binds both compressed/decompressed index and source hashes.
`index-validation.json` is the result of actually running the validator.

Every candidate contains the original twelve required fields: source_url,
event_date, discovered_at, platform, gpu, driver, gles_version, evidence_class,
affected_rules, repro, decision, test_id. Unknown applicability/device/reproduction
fields are null, affected_rules empty, decision PENDING_REVIEW_NO_RULE_PROMOTION,
and evidence_class UNVERIFIED. Source binding additionally retains the upstream
source/id/revision/hash/event-time-kind. Metadata confirmation is not claim review.

The observed corpus fetched_at `2026-11-15T02:37:58.234611+00:00` is reused as
**this collection's discovery timestamp**, not an invented first-seen timestamp
for each upstream item. Event dates retain their original release/commit semantics.
No current time is substituted during regeneration.

All rows remain UNVERIFIED at this metadata-index layer. This neither revokes nor
re-labels the ten selected separately documented AI source reviews. No automatic
promotion, new full-content review, independent reviewer, device measurement or
performance rule is produced. The selected reviews remain separate records.

```
python3 tools/v109_research_index.py generate --source docs/v1.0.9/research/rolling/2026-11-15/radar.json.gz --source-receipt docs/v1.0.9/research/rolling/2026-11-15/receipt.json --index docs/v1.0.9/research/index.json.gz
python3 tools/v109_research_index.py validate --source docs/v1.0.9/research/rolling/2026-11-15/radar.json.gz --source-receipt docs/v1.0.9/research/rolling/2026-11-15/receipt.json --index docs/v1.0.9/research/index.json.gz --report docs/v1.0.9/research/index-validation.json
python3 -m unittest discover -s tools -p 'test_v109_research_index.py' -v
```

Validation reconstructs the normalized rows from the hash-bound original source;
missing fields, stale source mappings and unsupported claims fail even if an
altered index was rehashed. Unit tests cover deterministic output, source/receipt
changes, missing fields and fabricated measurement promotion. UNKNOWN remains
unknown; this is contract/integrity acceptance only, not source-coverage acceptance.
