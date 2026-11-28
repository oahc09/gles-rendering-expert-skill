# Research evidence, not performance claims

Original planned window: 2026-08-11–2026-11-08. Source receipts were refreshed
2026-11-15 from official GitHub release APIs and hashed in ledger.json. Perfetto
v59.1 and Filament v1.78.0 release dates match the plan. Their releases do not prove
any GLES GPU speedup. No X post has been promoted to a fact or rule.

Reuse `references/research/update_radar.py`, including its existing deduplication,
date filters and explicit review stages. A fresh complete 90-day corpus/manual
vendor review has NOT_RUN status. Two verified references are not full coverage.
Future weekly incremental or monthly rolling collection must retain source hash,
event date, claim, reproduction and review before linking an accepted rule.

Current chain: official release → engineering reference → candidate A/B protocol →
no accepted performance rule → protocol negative tests. GPU vendor-specific rules
remain blocked until actual trace/counter evidence and review exist.

## Third increment: current 90-day metadata collection

`rolling/2026-11-15/receipt.json` records a full **2026-08-18–2026-11-15**
90-day inclusive collection using the existing radar normalize/select/dedup logic.
Ten public GitHub sources yielded 1,319 unique metadata candidates. Initial
HTTP 403 failures for three sources were recovered with the authorized GitHub
connector's public API; empty second pages confirmed completion. Initial failures
remain in the archive. No credentials or environmental inventory are included.

`radar.json.gz` is deterministic gzip of the original JSON; receipt binds both
archive and decompressed hashes. To reproduce or feed the existing radar, decompress
first (`gzip -dc radar.json.gz > radar.json`). Metadata retrieval is complete,
**manual vendor/X review and promotion are NOT_RUN**, and no new performance rule
is accepted. This supersedes only the earlier NOT_RUN collection status, not review.


## Fourth increment: selected full-content analysis

`release-review.json` / `.md` contain six selected release-note reviews, including
one empty Vulkan CTS note explicitly deferred. `implementation-review.json` / `.md`
contain four actual implementation-patch reviews. This is AI source inspection,
not independent human approval. Source-confirmed engineering cautions are linked
to existing controls and explicit reproduction gaps; metadata titles alone are
not counted as source review. No source patch proves a local performance gain.

## Executable source-to-experiment linkage
`experiment-chain.json` binds the four previously inspected implementation
reviews to their exact local experiment/test file hashes. The GL-free async flush
review explicitly has no exact local experiment. `tools/check_v109_research_chain.py`
rejects stale review/code hashes, missing coverage and any attempted promotion
from these records to a verified performance rule or independent human sign-off.
This checks integrity and declared linkage only; it neither re-fetches upstream
nor counts the remaining metadata corpus as read. No new rules are promoted.

## Read-only schedule delivery, not an active schedule claim
.github/workflows/research-radar.yml reuses the existing collector for inclusive
7-day weekly and90-day monthly windows. Repository permissions are read-only:
no secret injection, commits or rule promotion; artifacts retained30days.
Fetch failures retain INCOMPLETE and fail the job. Cron only becomes eligible
on the default branch; no execution from this Draft branch is claimed.
Window arithmetic is unit tested.

## Cross-run candidate metadata (AUD-07)

The hosted lane restores the most recent available `gles-radar-state-v1`
artifact from a previous successful **scheduled** run of the same workflow,
on the repository default branch. A manual run can read this history but
cannot publish replacement state. The job only requests `actions: read` in
addition to `contents: read`; state does not write to repository branches.

The independently versioned state contains only source/id pairs and UTC event
days over the last 90 inclusive days. A first run, old workflow without the
artifact, or expired artifact is reported as `NO_PRIOR_COMPLETE_HISTORY`, not
as verified deduplication. An invalid history fails rather than being silently
trusted. Incomplete retrieval retains its candidate report but does not
publish a new state. Exact identities dedupe across weekly/monthly and
same-day runs; this does not compare title wording or replace source review.
The configured release sources include Cocos Engine, Unity Graphics and Godot;
releases endpoints alone do not cover those projects' full commits or papers.
Review, reproduction, promotion and withdrawal remain separate from metadata
collection.
