# Frame Extrapolation, Motion Estimation & SGSR2 — Spend Fewer Frames/Pixels

> Distilled from the `amfe_power_saving`, `motion_estimation`, and `sgsr2`
> samples. These are **power/throughput** techniques: produce the same visible
> output while doing less GPU work per frame.

All three trade a little accuracy for large CPU/GPU savings. Treat them as
opt-in, capability-gated features with a clean fallback to full-rate rendering.

---

## 1. AFME — Adaptive Frame Motion Extrapolation (`QCOM_frame_extrapolation`)

Render only *every other* frame and let the GPU **extrapolate** the in-between
frame from the two most recent real frames. This roughly halves per-frame CPU
and GPU cost on the extrapolated frames — spend the savings on lower power/heat
or extra quality.

```cpp
// Generate an extrapolated frame from the two previous rendered frames.
// src1 = frame N-1, src2 = frame N, output receives the predicted frame N+1.
glExtrapolateTex2DQCOM(src1, src2, output, /*scaleFactor*/1.0f);
```

**Rules**
- Best for content with **coherent, predictable motion** (racing, side-scroll,
  smooth camera). Avoid on erratic cuts, UI-heavy, or teleporting content.
- **Exclude UI/HUD and text** from extrapolation — composite them at full rate
  on top, or they will smear.
- Keep real and extrapolated frames on a stable cadence to avoid judder.
- Gate behind an extension check; fall back to rendering every frame.

---

## 2. Pixel Motion Estimation (`QCOM_motion_estimation`)

Hardware block that compares a **reference** and a **target** image and outputs
a **motion-vector texture**. It is the building block for frame extrapolation,
temporal AA/upscaling, motion blur, compression, and object tracking.

```cpp
// Whole-image motion vectors from ref -> target into an output texture.
glTexEstimateMotionQCOM(refTex, targetTex, motionVecTex);

// Or restrict/weight the search with a region mask.
glTexEstimateMotionRegionsQCOM(refTex, targetTex, motionVecTex, maskTex);
```

**Rules**
- Output is a motion-vector texture (typically two-channel float); feed it to
  your reprojection/extrapolation/blur pass instead of computing vectors in a
  shader.
- Repeating/low-contrast patterns can confuse estimation — provide a mask or use
  the regions variant to constrain the search where reliability matters.
- Runs on a dedicated block, freeing the shader cores for other work.

---

## 3. SGSR2 — Snapdragon Game Super Resolution 2

Temporal upscaler: **render the scene at a lower internal resolution**, then
reconstruct a higher-resolution image using history + motion vectors. Large
fragment and bandwidth savings for a modest quality cost — the mobile analogue
of desktop temporal upscalers.

**Rules**
- **Render 3D at reduced resolution; upscale to native** for display. Pair with
  dynamic resolution when GPU-bound (see [`lrz-and-flexrender.md`](lrz-and-flexrender.md)).
- **Provide accurate motion vectors** (from geometry or `QCOM_motion_estimation`)
  and jittered projection for the temporal accumulation to converge.
- **Render UI/text at native resolution** after upscaling to keep it crisp.
- Reset/clamp history on camera cuts to avoid ghosting.

---

## When to reach for which

| Goal | Technique |
|:---|:---|
| Cut power/heat with steady motion | AFME frame extrapolation |
| Need motion vectors for reprojection/blur | Motion estimation |
| GPU-bound on fragment/bandwidth | SGSR2 + dynamic resolution |
