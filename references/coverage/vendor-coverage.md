# Vendor coverage and diagnostic boundaries

Reuse existing vendor adapters; never gate features by renderer substring or infer counters from aliases.

## Mali

Tile/transaction elimination hypotheses depend on architecture and attachment lifetime; count external-memory traffic, fragment work and frequency, not just draw count. [Source](https://developer.arm.com/Tools%20and%20Software/Arm%20Performance%20Studio).

Level: CONDITIONAL. Device evidence: BLOCKED_BY_HARDWARE.

## Adreno

GMEM/LRZ behavior is driver and pass dependent. Preserve attachment consumers; test spills, mixed MRT/MSAA and transparent ordering. [Source](https://docs.qualcomm.com/doc/80-54323-2).

Level: CONDITIONAL. Device evidence: BLOCKED_BY_HARDWARE.

## PowerVR

Desktop PVRVFrame is not physical PowerVR performance. Hidden-surface techniques do not eliminate all blended transparent work. [Source](https://docs.imgtec.com/tools-manuals/pvrvframe-manual/html/topics/introduction.html).

Level: CONDITIONAL. Device evidence: BLOCKED_BY_HARDWARE.

## Panfrost/Freedreno/etnaviv

Do not generalize a Mesa component fix across GPU families. Pin affected commit/driver and verify exact reproduction. [Source](https://docs.mesa3d.org/).

Level: CONDITIONAL. Device evidence: BLOCKED_BY_HARDWARE.

## ANGLE

Backend, translation and driver both matter; SwiftShader is software and cannot establish Windows hardware or mobile counter behavior. [Source](https://github.com/google/angle).

Level: CONDITIONAL. Device evidence: BLOCKED_BY_HARDWARE.

## Diagnostic tree
1. Establish API legality and actual advertised extension/entrypoint/limit snapshot. Unknown capability is not supported.
2. Reproduce wrong output independently of performance: fixed camera/state, numerical oracle and original thresholds. A failing baseline is unavailable, not a faster fallback.
3. For suspected device behavior, capture exact target/backend/driver with trace and heat/frequency conditions. Without these, retain a hypothesis, not a universal workaround.
4. Compare repeated interleaved runs and quality together. CPU submission duration or calculated logical bytes are not GPU/DRAM measurements.
5. Apply an evidence-bound conditional workaround only inside its driver range. Expiry, conflict or missing evidence requests review and baseline fallback; no automatic new mandatory rule.

Device report template: target/driver/backend; source/build SHA; capability snapshot; workload and oracle; before/after repetitions; raw trace; heat/frequency; counters with exact tool units; quality and performance conclusions separately; unknowns; reviewer; expiry and rollback. Keep private machine identifiers out of public reports.
