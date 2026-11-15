# EGL lifecycle demo

From repository root, run `python3 examples/closure/egl-lifecycle/run.py --config DRIVER_JSON --output REPORT_JSON` using an already provisioned trusted Mesa/ANGLE GLES config. This Python/ctypes demo requires existing EGL/GLES libraries; it downloads/installs nothing.

See `references/coverage/egl-matrix.md` for exact tested host lifecycle, expected errors, synchronization and untested physical/native-platform boundaries. This is executable host scaffolding, not an Android/Windows build deliverable.
