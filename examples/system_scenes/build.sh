#!/bin/sh
set -eu
ROOT=$(CDPATH= cd -- "$(dirname -- "$0")/../.." && pwd)
BUILD=${GLES_SYSTEM_BUILD_DIR:-/tmp/gles-system-scenes}
mkdir -p "$BUILD"
if [ -n "${GLES_SDK_ROOT:-}" ]; then
 export CPLUS_INCLUDE_PATH="$GLES_SDK_ROOT/include${CPLUS_INCLUDE_PATH:+:$CPLUS_INCLUDE_PATH}"
 export LIBRARY_PATH="$GLES_SDK_ROOT/lib/x86_64-linux-gnu${LIBRARY_PATH:+:$LIBRARY_PATH}"
fi
for name in simulation effects precision; do
 if [ -f "$ROOT/examples/system_scenes/$name.cpp" ]; then
 ${CXX:-c++} -std=c++17 -Wall -Wextra -Werror -pedantic "$ROOT/examples/system_scenes/$name.cpp" -lEGL -lGLESv2 -o "$BUILD/$name.tmp.$$"
 mv "$BUILD/$name.tmp.$$" "$BUILD/$name"
 fi
done
