# 90-day pipeline research review

Window: **2026-08-05–2026-11-02 UTC**, inclusive 90 days. Discovery occurred
2026-11-07. The plan's original window is preserved instead of silently moving
the cutoff. `2026-11-02/radar.json` uses the existing collector and normalizer;
`sources/` retains exact API responses for source-diff review. `decisions.json`
records independent source verification, local reproduction scope and adoption.

Accepted engineering principles:
- Filament `1758f2c`: validate duplicate and mismatched material binding records
  before use. Its independent serialized chunks and type matching were read in
  the actual diff. Our GLES checker uses GLES's distinct binding namespaces;
  Filament descriptor sets are not asserted to be GLES core objects.
- Filament `3513739`: explicit material-package compatibility versioning informs
  our cache/ABI invalidation tests. The previous `89be95d` 78→79 diff is also
  archived. These changes are not new GLES APIs or measured performance gains.

Deferred: conditional MOT program sharing (`4e2df5e`), which requires semantic
depth/displacement equivalence beyond this checker; Perfetto 59.1's agent-mode
and GPU slice additions, pending captured producer/schema compatibility tests.
Rejected: transferring a Vulkan-only depth-view optimization (`26b4277`) and
its upstream device timing into a GLES performance claim.

GLES CTS active-series status and original X posts remain unverified here.
The release API yields Vulkan tags in this window; they do not become GLES
features. No X URL, date or benchmark has been invented. Specifications used
by the pipeline references are stable historical normative context, not claimed
as 90-day discoveries.

## Repeatable maintenance, without creating a remote schedule

Use the same `update_radar.py` with explicit `--start` and `--end` for weekly
increments or monthly inclusive 90-day review. The added `filament-commits` and
`spirv-tools` sources share its source/ID deduplication and completeness policy.
Keep candidate metadata separate from `validate_v107_evidence` decisions.

```sh
python3 references/research/update_radar.py --start 2026-08-05 --end 2026-11-02 \
  --archive references/research/2026-11-02-v107
python3 -m unittest discover -s references/research -p 'test_*.py' -v
```

No new recurring task, remote compute, provider call or automatic rule promotion
was created. Broad metadata collection completeness does not mean every upstream
change or every manual source was semantically verified.
