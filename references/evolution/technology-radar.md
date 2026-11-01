# Executable technology radar

Initial inclusive UTC window: **2026-10-02 through 2026-11-01**. See [discovery](../research/2026-11-01/discovery.md) and the evidence ledger.

Run from repo root:

```sh
python3 references/research/update_radar.py --start 2026-10-02 --end 2026-11-01
python3 -m unittest discover -s references/research -p 'test_*.py'
```

The standard-library script fetches public GitHub release metadata (CTS, Filament, AGI, Perfetto, RenderDoc and glslang) and ANGLE commits, archives `references/research/YYYY-MM-DD/radar.json`, filters original event timestamps, deduplicates source/ID against earlier archives, reports fetch/truncation failures, and does **not** auto-edit rules. Date folders are review dates (end of interval), not source release dates. Its UTC `fetched_at`, source states, item identity and printed SHA allow reproducible evidence inspection. Re-running the same date replaces that date's radar; version it before accepting later changes.

Weekly operation: choose explicit previous seven-day window; review original PR/commit diff and linked issue, preserve rejected items. Monthly operation: last 30 days inclusive with previous archives used for dedup; write discovery/evidence/accepted/rejected review. A successful fetch with zero candidates is not proof that the whole ecosystem had no updates. Use “no verified material updates” only after reviewing scope and failures.

Non-API sources (Khronos tables, Android policy pages, vendor manuals, Mesa GitLab and X) require manual dated review; a weekly operator checklist is not a background service. **No scheduler or recurring cloud task is enabled by this PR.** A release owner must separately authorize/configure scheduling. CI can validate the script offline without network or secrets. Network errors yield exit 2 and `INCOMPLETE`, never fabricated empty success.

Candidate outcomes: `VERIFIED_SPEC`, `VERIFIED_SOURCE`, `REPRODUCED`, `UNVERIFIED`, `REJECTED`. Hardware experiments retain `BLOCKED_BY_HARDWARE`. The two status axes must not be collapsed.
