# v1.0.5 candidate acceptance and requirements traceability

This implements the feasible source/tooling scope of the exact archived plan,
not a claim of full device/model/release acceptance. Base main:
`e16ff0880d6c9f3d9435ca3f0027de9e92d6b5f1`; early remote source checkpoint:
`4607dc7082611d1f312188643a919f7f41dce1b6`.
Metadata remains **1.0.2**. Prior v1.0.3/v1.0.4 release blockers are preserved,
not relabeled as new features, and no risk waiver or release authorization exists.

| Work | Implementation | Actual evidence | Remaining boundary |
|---|---|---|---|
| W0 | baseline-and-delta.md + exact development-plan.md | Verified merged main/PR2/tag and old gate state | Previous physical/provider gates remain PREDECESSOR_BLOCKER |
| W1 | benchmarks/longrun/ + thermal-and-power playbook | Validated schema/ordered sample analysis, five authored600/1800s timelines with3 positive categories and2 conservative controls; separate real host workload capture | No physical cold/steady10/30min frame/thermal/power captures; synthetic duration is not elapsed execution |
| W2 | benchmarks/quality_policy/ + adaptive-quality playbook |25 deterministic policy/visual-bridge tests, bounded changes, spike/gap/background/off/floor/recovery controls, capability and visual gates | Policy recommends only; full presets need per-scene/device approval; scale-only imagery does not approve all controls |
| W3 | examples/precision/ + precision-and-color playbook | Real binary32/binary16 CPU oracle and compute readback; mediump separately measured; host and API26 arm64 compile/link | No universal mediump bit-width/speed claim; physical devices pending |
| W4 | examples/resource_pressure/ + benchmarks/resource_pressure/ |100 actual software scene cycles:800uploads/400readbacks/400cancel paths,10Surface+4controlledContext rebuilds; strict host/NDKcompile;12 regressions | Owned-object counts/estimated texture bytes, not driver leaks or physical VRAM; real pendingfences0, separate synthetic pending-policy tests; Androidloss NOT_RUN_DEVICE |
| W5 | benchmarks/traces/sql/ + trace-sql playbook |10schema-probed templates,17SQLite normalized fixtures; actual officialPerfetto v59.1 processor normal/empty/truncated syntheticprotobuf cases | Synthetic/source-labeled evidence, not a physical device trace or independent causal ground truth |
| W6 | benchmarks/visual_quality/ |8scenes×3times=24frozen goldens;120 actual software captures;174 runtime-extracted GLSLstage compiler checks;16comparer/manifest tests; masks/region/multiscale/temporal/heatmaps | P03 .85/.7 scale and P01/P03mediump correctly rejected; no threshold relaxation; physical Pareto time/power/memory/thermal fields null |
| W7 | references/research/2026-11-01-v105/ + existing radar extension | Officialsource/date/hash ledger; Perfetto release date verified;24research tests | X and unavailabledynamicvendor evidence remainsUNVERIFIED; historical releases not recast as new |
| W8 | existing agent runner/scorer + cases-v1.0.5.json + check_release_gates | Prior88 unchanged +24 new labeled tasks,112 total;37Agent infrastructure tests; optional independent visual/evidence/wrong-advice metrics with denominators;33gate/shader infrastructure tests | Zero realprovider calls; humanannotation review pending; APK still blocked by predecessor Gradle network path; no CI dispatch/required-policy changes |

## Commands and evidence levels

```sh
python3 -m unittest discover -s benchmarks/longrun -p 'test_*.py' -v
python3 -m unittest discover -s benchmarks/quality_policy -p 'test_*.py' -v
python3 -m unittest discover -s benchmarks/visual_quality -p 'test_*.py' -v
python3 -m unittest discover -s benchmarks/resource_pressure -p 'test_*.py' -v
python3 -m unittest discover -s benchmarks/traces/sql -p 'test_*.py' -v
python3 -m unittest discover -s benchmarks/agent -p 'test_*.py' -v
python3 -m unittest discover -s references/research -p 'test_*.py' -v
python3 -m unittest discover -s tools -p 'test_*.py' -v
python3 tools/check_release_gates.py --gates v1.0.5 --require-release # expected exit2
```

L0 schema/links and synthetic arithmetic are not L1 actual hostGL/GLSL/JVM tests;
L1 is not L2 APK/device lifecycle; cross-compilation is not target execution;
L3 physicalGPU thermal/power and L4 realpaired models remain blocked. Both earlier
gates and new release gate are checked, including explicit release authorization.
The existing workflow remains manual-only; extending its test commands did not run
Actions or enable PR triggers.

Evidence lives beside its module plus `docs/v1.0.5/evidence/`. Captures retain raw
stdout/SQL rows, source/tool/runner/artifact hashes and precise provenance.
Goldens were created once then tested without automatic overwrite. The numerical
binary16 experiment uses explicit half quantization; it does not assume every
mediump implementation equals half. Visual acceptance cannot excuse a missing
counter or imply energy savings. Data masks/thresholds require independent review
before adopting this as a production visual standard.

## Rollback and release

Revert this candidate's commits normally if needed; no production deployment or
device configuration was changed. Do not bump metadata or tag v1.0.5 until all
required predecessor/current evidence passes and a separate release authorization
is recorded. No later version is scheduled by this delivery.


## Actual sustained host run and review corrections

The final unchanged capture runner executed for **600.000379648 actual seconds**,
274 successful software workload iterations, with atomic progress checkpoints and
raw subprocess output. `host-longrun-600s.json` binds runner/scene/binary SHA;
`host-longrun-analysis.json` keeps frame, thermal, frequency and power fields null.
This is a real10-minute host harness run, **not a physical10-minute device/frame
benchmark**. The 30-minute timelines remain synthetic fixtures; the real1800s
protocol is provided but no physical cold/steady run is claimed.

Independent review prompted transactional quality-state updates, deep-isolated
returned presets and stricter device-capture identity/completion checks. Invalid
input no longer consumes policy time or mutates another instance; incomplete or
failed captures cannot supply diagnoses. Longrun regression suite now has26 tests,
quality policy25 including5 visual-bridge checks. SQL attribution now recomputes
thresholds only on temporally matched samples and retains matched row evidence;
a healthy overlap cannot validate unrelated high averages. Golden inventory now
requires the exact24 images and capture/storage metadata; omissions fail closed.
