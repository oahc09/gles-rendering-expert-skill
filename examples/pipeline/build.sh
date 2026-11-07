#!/bin/sh
set -eu
ROOT=$(CDPATH= cd -- "$(dirname -- "$0")/../.." && pwd)
BUILD=${GLES_PIPELINE_BUILD_DIR:-/tmp/gles-pipeline-lab}
mkdir -p "$BUILD"
if [ -n "${GLES_SDK_ROOT:-}" ]; then
 export CPLUS_INCLUDE_PATH="$GLES_SDK_ROOT/include${CPLUS_INCLUDE_PATH:+:$CPLUS_INCLUDE_PATH}"
 export LIBRARY_PATH="$GLES_SDK_ROOT/lib/x86_64-linux-gnu${LIBRARY_PATH:+:$LIBRARY_PATH}"
 export LD_LIBRARY_PATH="$GLES_SDK_ROOT/lib/x86_64-linux-gnu${LD_LIBRARY_PATH:+:$LD_LIBRARY_PATH}"
fi
${CXX:-c++} -std=c++17 -Wall -Wextra -Werror -pedantic "$ROOT/examples/pipeline/pipeline_lab.cpp" -l:libEGL.so.1 -lGLESv2 -o "$BUILD/pipeline-lab"
printf '%s\n' "$BUILD/pipeline-lab"
