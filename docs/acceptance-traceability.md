# v1.0.3 candidate: requirements → implementation → evidence

This is a candidate implementation, **not a completed v1.0.3 release**. Metadata remains
1.0.2 because the taskbook explicitly requires all W0–W7 acceptance before a bump.
The original complete taskbook is archived alongside this report; nothing is silently
re-scoped to a documentation-only version. No tag, release, merge or automatic scheduled
workflow is performed by this PR.

| Work package | Implementation | Acceptance / limitations |
|---|---|---|
| W0 | `baseline-audit.md`, `baseline-files.txt`, archived exact taskbook | Clean baseline and authority verified; early remote checkpoint |
| W1 | SKILL + `.cursorrules`, API/EGL/GLSL rules/cards; `benchmarks/rules/` and research archive | 30 machine-readable rules / 112 distinct contract cases, not 112 source rules; compile/runtime negative controls separate |
| W2 | capability/lifecycle/backend matrices; `examples/validation/egl_smoke.cpp` | Actual software EGL capability snapshot, surface resize, explicit context rebuild, shared producer/consumer context; **no Android background/resume or injected real context loss** |
| W3 | GPU experiment specifications/capture validation, conditional vendor guidance | No physical Mali/Adreno/PowerVR device or counters available: `BLOCKED_BY_HARDWARE`; no measured performance gains claimed |
| W4 | six engineering playbooks + existing examples and capability fallbacks | Host subset executable; Android AHardwareBuffer, HDR display, device frame pacing and target ABI acceptance remain hardware/toolchain-dependent |
| W5 | `tools/validate_rules.py`, `tools/validate_shaders.py`, host runner, manual CI | Real C++17 host compile/link and software GLES runtime; 16 actual ESSL compiler/link checks; 6/6 legacy C++ files instantiate/compile/link; Android target build and physical-device smoke remain unrun |
| W6 | `benchmarks/agent/` paired runner, 64 annotated cases, scoring + infrastructure tests | Mock/fixture tests establish infrastructure only; no live provider benchmark or judged improvement claimed |
| W7 | routing, README, unreleased changelog, gates, this traceability + rollback | Candidate package assembled; final release remains blocked by W2–W6 acceptance |

## Mandatory C01–C12 mapping

| ID | Coverage | Acceptance interpretation |
|---|---|---|
| C01 ReadBuffer | R001/R002; actual host FBO positive/negative | API subset PASS on software driver |
| C02 TexImage formats | R003–R005; actual host format positive/negative | RGBA8 tested; not every spec tuple |
| C03 cross-context upload | R006–R009; actual two-context upload, producer fence/flush, consumer wait/readback | Software runtime PASS, target stress testing required |
| C04 surface/context lifecycle | R022/R023; host surface resize/context rebuild | Recovery policy covered; real Android/context-loss injection NOT_RUN |
| C05 shader versions | R010–R012; ESSL300/310/320 actual compiler and runtime fixtures | Positive/negative compiler behavior, not all extensions |
| C06 FBO invalidate | R016–R018; W3 capture spec | Correctness contracts; mobile bandwidth NOT_RUN |
| C07 ordering/discard | conditional rules/vendor guidance + W3 scenario | No universal speed assertion; hardware blocked |
| C08 FBO switch/MSAA | R019/R020 + W3 scenario | Resolve constraints covered; target tile traffic blocked |
| C09 AHardwareBuffer/video | R021/R028 + video example/playbook | Extension guards covered; Android import/fence hardware blocked |
| C10 backend choice | capability/backend matrix + paired Agent cases | Probe actual renderer rather than OS inference; backend matrix not physically exercised |
| C11 precision/UBO | R013/R029 + shaders + GPU scenario | Contract/compiler subset; target precision/perf evidence blocked |
| C12 branchless two textures | R026 + conditional optimization rule + Agent counterexamples | Reject unmeasured faster claim; hardware A/B blocked |

## Reproducible commands

```sh
python3 tools/validate_rules.py --output reports/rules.json
python3 tools/validate_shaders.py --output reports/shaders.json
EGL_PLATFORM=surfaceless LIBGL_ALWAYS_SOFTWARE=1 MESA_SHADER_CACHE_DISABLE=true sh examples/validation/run-host.sh
python3 -m unittest discover -s benchmarks/agent -p 'test_*.py' -v
python3 tools/check_release_gates.py
python3 tools/check_release_gates.py --require-release # expected nonzero while blocked
```

The GitHub workflow is **workflow_dispatch only**. It has not been dispatched as part
of this task. Source-local runs are evidence, not claims that GitHub CI passed.

## Rollback / continuation

Normal review and merge only after authorization; revert the candidate PR as one unit
if needed. No persisted GL resources or production configurations are changed. Keep
raw capture records and source hashes; never overwrite a previous measurement with a
new run. Run target-device and paired-provider acceptance later, append evidence, then
change gate statuses only after independent review. Version bump/tag is a separate,
explicit release action after **all** taskbook gates pass.

## Review corrections and actual test inventory

Independent review and compiler execution found and corrected additional defects:
- Named FBO invalidation accepts nonzero COLOR_ATTACHMENTi below the queried limit.
- Shader rejection controls reject tool crashes/missing-input failures as evidence.
- GLSL ES varying precision may differ; same-name shared uniforms and interface types follow their own matching rules.
- Normalized-color MSAA resolve does not make GL_LINEAR generically illegal; integer/depth/stencil filter restrictions are separate.
- Legacy examples needed default constructors, PBO unmap-before-upload, and pointer-sized EGLImage handling plus ESSL3 external-texture guards.

Actual local results are committed in `docs/validation/`: 112 structured contract
cases; 16 glslang compile/link checks; 24 software EGL assertion events (some
repeated after controlled context recreation); 6 legacy host C++ file checks.
Synthetic infrastructure results are separate: 15 Agent runner/scorer tests,
15 GPU capture tests, 9 research updater tests, 12 gate/shader-runner tests.
None is a live-model score or a physical mobile GPU performance result.
