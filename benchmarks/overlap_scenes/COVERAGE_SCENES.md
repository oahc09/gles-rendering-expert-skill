# Finite rain, volume and layered-UI coverage scenes

```sh
python3 benchmarks/overlap_scenes/coverage_scenes.py --config DRIVER_JSON --output REPORT_JSON
python3 -m unittest discover -s benchmarks/overlap_scenes -p test_coverage_scenes.py -v
```

New bounded types fill local W4 mechanism coverage rather than enlarging a
selection matrix:

* Nine rain-droplet proxies: narrow elliptical projected billboards with radial
  alpha falloff. Not droplet fluid simulation, refraction, lens distortion or a
  physically derived rain renderer.
* Eight volume slices: radial density and Beer–Lambert opacity
  `1-exp(-density*sqrt(1-r²)*0.25)`, back-to-front compositing. A sliced volume
  approximation, not general volume ray marching, scattering or self-shadowing.
* Six rounded layered UI panels: rounded-rectangle coverage, independently
  colored transparent layers at different depths. Not a complete UI layout,
  clipping or font system.

Each scene includes two offscreen objects. Actual GLES projects each billboard,
performs fragment coverage/opacity, blends to RGBA8, and reads all pixels. Cameras
translate -0.3/0/+0.3. Independent scalar CPU projection, shape, opacity and
per-layer quantization provide goldens. Baseline, conservative offscreen culling,
and deliberately incorrect visible-object removal are actually executed.

## Tile statistics

For each 16×16 tile in the 64×64 image, the CPU reference records:

- sample-count estimate of projected rectangular bounds and union covered pixels;
- shaded fragment samples, maximum/mean blend-layer count;
- source RGB/alpha ranges and final mean RGBA;
- participating depth range;
- mean background transmission `product(1-alpha)`.

Full per-pixel layer heatmaps and background-transmission arrays are retained.
Projected area is pixel-center sampled rectangular coverage, not analytic area
or a GPU invocation counter. Background transmission describes residual weighting
of a hypothetical background; the actual render target clears to transparent
black. It is not physical background illumination. Per-candidate tile color
error and silhouette disagreement are numerical proxies, **not calibrated human
perceptual error**.

## Verified evidence

Both Mesa and ANGLE report HOST_PASS. Each runs 27 readbacks: 18 positive
baseline/culling results and nine rejected removal negatives. All culled images
are exactly identical to their baselines. Existing limits are unchanged: color
max4, silhouette mismatch <=2, centroid error <=0.1 pixel. Maximum positive color
error is Mesa3 / ANGLE1; cross-camera parallax error is at most Mesa0.00281 pixel
and ANGLE0. Actual dynamic camera motion is checked, not inferred from static
frames. Culling removes offscreen submissions; visible coverage does not decrease.
No physical GPU timing/counters or reduction in visible overdraw is claimed.

Evidence JSON contains scene inputs, source hashes, metrics and per-tile errors.
The paired deterministic ZIP includes all actual/CPU RGBA images and complete
statistics JSON. Extract beside the report. Earlier tiered/precision failures
remain unchanged. Broad production-scene robustness, perceptual calibration and
physical performance acceptance remain open.
