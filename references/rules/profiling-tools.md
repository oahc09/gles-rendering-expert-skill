# GPU Profiling Toolchain — Structured Performance Diagnosis

> Vendor profiling tools for TBDR GPUs plus a structured diagnosis workflow.
> All performance claims must be backed by profiler evidence — never assert an
> optimization "will help" without measuring the relevant counter.

---

## 1. Tool Selection Matrix

| Tool | Vendor / Scope | Best For | Platform |
|:---|:---|:---|:---|
| **ARM Streamline Performance Analyzer** | ARM Mali | Bandwidth counters, shader core cycles, API frame capture, per-draw breakdown | Android / Linux (Mali) |
| **Android GPU Inspector (AGI)** | Google, multi-vendor (Mali, Adreno, PowerVR via Perfetto) | System-wide GPU timeline, counter graphs, Vulkan/GLES trace replay | Android |
| **Snapdragon Profiler** | Qualcomm Adreno | GMEM utilization, LRZ/FlexRender stats, shader hotspot, snapshot frame analysis | Android (Adreno) |
| **Perfetto** | Android platform | Lightweight long-duration tracing, GPU frequency / utilization / thermal context | Android (all) |
| **RenderDoc** | Cross-platform | Frame capture + per-draw state/resource inspection | Windows (ANGLE backend) |
| **GL_KHR_debug / `glGetError`** | API-level | Synchronous error and message capture in all builds | All |

### Selection rules

1. **Identify the GPU first** (`glGetString(GL_RENDERER)`); pick the vendor
   tool that matches. No vendor tool → use AGI/Perfetto.
2. On **Windows/ANGLE**, vendor mobile tools do not apply — use RenderDoc for
   frame inspection and ANGLE's own debug layers for validation.
3. Prefer **frame snapshots** (Snapdragon Profiler snapshot, RenderDoc capture)
   for per-draw investigation and **continuous counters** (Streamline, AGI,
   Perfetto) for time-based behavior (thermal throttling, spikes).

---

## 2. Key Counters per GPU Architecture

### ARM Mali (Streamline)
- **External bandwidth** (bytes read/written to DRAM) — the primary TBDR cost.
  Correlate with `glInvalidateFramebuffer` coverage.
- **Fragment pipe active cycles** vs **total cycles** → fill-rate bound?
- **Tile memory usage** — over-budget tile splits degrade performance.
- **Non-fragment-bound detection**: if GPU cycles are low but frame time is
  high, the bottleneck is CPU / synchronization, not the GPU.

### Qualcomm Adreno (Snapdragon Profiler)
- **GMEM utilization** — % of frame where GMEM loads/stores occur. Goal: near
  zero loads, minimal stores (see `adreno/gmem-load-store.md`).
- **LRZ efficiency** — % of fragments rejected by low-resolution Z. Drops when
  `discard`/`gl_FragDepth` are used or draw order is back-to-front.
- **SP (shader processor) utilization** per stage; unbalanced stages indicate
  vertex or fragment bound.
- **UCHE (unified cache) hit rate** — low rates point at texture streaming or
  layout issues.

### PowerVR (PVRTrace / PVRPerf, SDK tooling)
- **HSR efficiency** — % of fragments eliminated by hidden surface removal.
  Drops with `discard`, alpha test, or depth-write-off opaque draws.
- **Parameter Buffer / SPM events** — SPM partial renders are critical
  failures (see `powervr/bandwidth-and-tile-management.md`).
- **ISP load vs USC load** — geometry-bound vs shader-bound.

---

## 3. Structured Diagnosis Workflow

Follow this fixed pipeline when a performance problem is reported:

```
1. SYMPTOM     — quantify: fps / frame-time / ms budget, which frames, thermal state
2. TRIAGE      — CPU-bound or GPU-bound? (Perfetto CPU freq vs GPU busy %)
3. COUNTER     — capture the architecture-specific counters above
4. CLASSIFY    — bandwidth / fill-rate / shader-ALU / overdraw / sync / CPU submission
5. MAP TO RULE — link the classification to the matching rule document:
                   bandwidth  → tbdr-bandwidth-rules.md
                   overdraw   → HSR/LRZ rules + draw order
                   fill-rate  → MSAA / resolution / blending
                   sync       → egl-and-context.md §fences, glFinish/glFlush audit
6. FIX         — apply the smallest targeted change
7. VERIFY      — re-capture the same counter set; report delta, never eyeball-only
```

### Triage decision table

| Observation | Classification | First action |
|:---|:---|:---|
| GPU busy %, bandwidth counters high | Bandwidth-bound | Audit clear/invalidate coverage (§2 of tbdr-bandwidth-rules) |
| GPU busy %, bandwidth low, fragment cycles high | Fill-rate / ALU-bound | Reduce overdraw, simplify shader, VRS |
| GPU busy % low, frame time high | CPU or sync-bound | Check `glFinish`, fence stalls, draw-call count |
| Periodic spikes every N seconds | Thermal / GC / loading | Perfetto thermal track, asset streaming audit |
| First-frame or scene-change hitch | Shader compile / upload | `glProgramBinary` cache, PBO streaming uploads |

---

## 4. Rules

1. **Never profile on the Android Emulator** for bandwidth/fill-rate numbers —
   it is host-backed immediate-mode. Use real devices; keep the emulator for
   functional testing only.
2. Lock device state when comparing runs: fixed thermal state (cooldown
   between runs), fixed resolution, disable dynamic scaling if the tool
   supports it; record GPU frequency alongside counters.
3. Capture **before/after counter pairs** for every optimization you ship.
   Report results as "counter X reduced from A to B on device Y, driver Z" —
   no device-agnostic absolute claims.
4. Enable `GL_KHR_debug` (message callback) in debug builds; many bandwidth
   problems surface as driver warnings (e.g., incomplete FBO, synchronous
   readback).
5. For frame hitches, correlate with **Perfetto's GPU work slices** to see if
   the hitch is render-thread CPU time, GPU execution, or `eglSwapBuffers`
   backpressure.
