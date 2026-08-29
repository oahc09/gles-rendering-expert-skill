# Frame Pacing — Swap Interval, Choreographer & Android Frame Pacing

> How frames are scheduled to the display on Android, and why "GPU finished in
> time" is not the same as "frame displayed smoothly". Complements
> `profiling-tools.md` (measurement) and `tbdr-bandwidth-rules.md` (per-frame cost).

---

## 1. The Core Problem

On Android the compositor (SurfaceFlinger) latches buffers on a vsync rhythm.
A renderer that submits at arbitrary times produces **jitter** even at high
average FPS: frames displayed at 4 ms, 22 ms, 10 ms intervals look worse than
a steady 16.7 ms cadence. Frame pacing is about *when* you present, not only
*how fast* you render.

---

## 2. `eglSwapInterval` Behavior on Mobile

| Value | Desktop expectation | Android reality |
|:---|:---|:---|
| `eglSwapInterval(dpy, 1)` | vsync, may tear-free block | Generally honored, but many drivers clamp/treat loosely; not a pacing guarantee |
| `eglSwapInterval(dpy, 0)` | immediate, tearing | Often ignored or clamped to 1 by the driver |

### Rules

- **Do not rely on `eglSwapInterval` alone for smooth pacing.** It is a hint
  that behaves inconsistently across Mali / Adreno / PowerVR drivers.
- Query `EGL_MIN_SWAP_INTERVAL` / `EGL_MAX_SWAP_INTERVAL` before setting.
- Keep the interval at **1** for games; avoid 0 (tearing) and values >1
  (locks to half/quarter refresh).

---

## 3. Choreographer (Native Activity / NDK)

`AChoreographer` gives vsync-aligned callbacks — the native analogue of
`Choreographer.postFrameCallback`.

### Rules

- Drive per-frame updates from `AChoreographer_postFrameCallback64`, not from
  a free-running loop with `sleep` — aligns simulation start to vsync.
- Use the **vsync timestamp** (callback `frameTimeNanos`) for animation time,
  not wall clock, so pacing glitches don't cause animation jumps.
- One buffer submitted per vsync: if a frame's GPU work is longer than the
  vsync period, the pipeline is full — measure first (Perfetto GPU track),
  then cut per-frame cost, don't just add buffering.

```cpp
// ✅ vsync-driven frame callback
void OnVsync(long long frameTimeNanos, void* data) {
    auto* app = static_cast<App*>(data);
    app->Update(frameTimeNanos);   // animate from vsync time
    app->Render();                 // draw + eglSwapBuffers
    AChoreographer_postFrameCallback64(AChoreographer_getInstance(),
                                       OnVsync, app);
}
```

---

## 4. Android Frame Pacing Library (Swappy / games-frame-pacing)

Google's `games-frame-pacing` library (Swappy) is the recommended solution for
steady cadence. It measures the display refresh period at runtime (including
90/120/144 Hz panels and variable refresh) and times buffer submission to
target a configurable frame period.

### Rules

- **Prefer Swappy over hand-rolled pacing** for anything beyond a simple demo:
  it handles multi-refresh-rate panels, auto-tunes the target period, and
  integrates with ADPF-style frame targets.
- Use the **GL integration** (`SwappyGL_init`, render with
  `SwappyGL_setWindow`, swap via `SwappyGL_swap`) instead of raw
  `eglSwapBuffers` when adopting it — Swappy takes over the swap.
- Set the target period explicitly (`SwappyGL_setSwapIntervalNS`) rather than
  accepting the auto value blindly; re-evaluate when refresh rate changes.
- Combine with **dynamic resolution / quality scaling**: when a frame misses
  its target, cut resolution or effects first; do not let the pacing library
  fight an over-budget frame indefinitely.
- Swappy is Android-only; on Windows/ANGLE keep `eglSwapInterval(1)`.

---

## 5. Buffer Count & Latency

- Triple buffering is the Android default for window surfaces; extra buffers
  add **latency**, not smoothness. Do not create more than 2–3 buffers in the
  swapchain-equivalent path.
- For lowest latency at steady cadence: one frame of CPU work ahead of GPU
  (CPU prepares frame N while GPU renders N−1); more overlap trades latency
  for resilience to spikes.

---

## 6. Quick Technique → Rule Map

| Symptom | Diagnosis path |
|:---|:---|
| High FPS but visible stutter | Pacing issue → Choreographer/Swappy cadence, check Perfetto frame timeline |
| Tearing | `eglSwapInterval` 0 or compositor bypass → force interval 1 |
| 60 FPS cap on a 120 Hz panel | Refresh-rate query missing → Swappy auto-detect, or `Surface.getRefreshRate` via JNI |
| Input feels laggy | Buffer queue too deep → reduce buffers / overlap |
