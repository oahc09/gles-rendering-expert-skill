# Candidate rollback and maintenance

Revert only this candidate's commits/PR, preserving the main baseline and historical gates. No settings, schedules, permissions, credentials or release tags are changed. XML updates require a new pinned SHA, license/hash verification, regenerated catalogs, source diff review and negative integrity tests; never fetch moving HEAD during validation.

Reproduce offline structural and test contracts first, then actual software compiler/runtime probes; read platform/provider blockers separately. Reject a capability route when its probe, entrypoint or conditions fail. Do not use a failed visual baseline as fallback. Frozen final-evaluation cases must not be edited in response to model failures; retain the original run and issue reviewed follow-up cases outside the terminal score set.
