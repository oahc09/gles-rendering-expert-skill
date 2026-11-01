#!/bin/sh
# Dependencies: C++17 compiler, EGL/GLES3 development headers, EGL/GLESv2 libraries.
# Optional local SDK: GLES_SDK_ROOT=/path/to/extracted/usr
set -eu
ROOT=$(CDPATH= cd -- "$(dirname -- "$0")/../.." && pwd)
BUILD=${GLES_BUILD_DIR:-/tmp/gles-skill-validation}
mkdir -p "$BUILD"
if [ -n "${GLES_SDK_ROOT:-}" ]; then
  export CPLUS_INCLUDE_PATH="$GLES_SDK_ROOT/include${CPLUS_INCLUDE_PATH:+:$CPLUS_INCLUDE_PATH}"
  export LIBRARY_PATH="$GLES_SDK_ROOT/lib/x86_64-linux-gnu${LIBRARY_PATH:+:$LIBRARY_PATH}"
  export LD_LIBRARY_PATH="$GLES_SDK_ROOT/lib/x86_64-linux-gnu${LD_LIBRARY_PATH:+:$LD_LIBRARY_PATH}"
fi
${CXX:-c++} -std=c++17 -Wall -Wextra -Werror -pedantic "$ROOT/examples/validation/egl_smoke.cpp" -lEGL -lGLESv2 -pthread -o "$BUILD/egl-smoke"
"$BUILD/egl-smoke" "$ROOT/examples/validation/shaders"
