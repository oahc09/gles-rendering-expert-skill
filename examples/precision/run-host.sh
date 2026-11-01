#!/bin/sh
set -eu
ROOT=$(CDPATH= cd -- "$(dirname -- "$0")/../.." && pwd)
BUILD=${GLES_PRECISION_BUILD_DIR:-/tmp/gles-precision-lab}
mkdir -p "$BUILD"
if [ -n "${GLES_SDK_ROOT:-}" ]; then
 export CPLUS_INCLUDE_PATH="$GLES_SDK_ROOT/include${CPLUS_INCLUDE_PATH:+:$CPLUS_INCLUDE_PATH}"
 export LIBRARY_PATH="$GLES_SDK_ROOT/lib/x86_64-linux-gnu${LIBRARY_PATH:+:$LIBRARY_PATH}"
 export LD_LIBRARY_PATH="$GLES_SDK_ROOT/lib/x86_64-linux-gnu${LD_LIBRARY_PATH:+:$LD_LIBRARY_PATH}"
fi
${CXX:-c++} -std=c++17 -Wall -Wextra -Werror -pedantic "$ROOT/examples/precision/precision_lab.cpp" -lEGL -lGLESv2 -o "$BUILD/precision-lab.tmp.$$"
mv "$BUILD/precision-lab.tmp.$$" "$BUILD/precision-lab"
exec "$BUILD/precision-lab" "$@"
