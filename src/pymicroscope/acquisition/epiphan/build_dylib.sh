#!/bin/bash
# Rebuild libfrmgrab.dylib from the static archives.
#
# When to rebuild:
#   - The committed libfrmgrab.dylib was compiled with -mmacosx-version-min=10.9
#     so it loads on Mavericks (the original DCC video acquisition machine).
#   - On older macOS where ctypes.CDLL fails with "load command 0x80000034 is unknown"
#     (LC_BUILD_VERSION, introduced in 10.13), rebuild with a deployment target
#     matching the target OS.
#   - On a machine where the dylib refuses to open (wrong architecture, missing
#     framework, mismatched expat/libc++), rebuild here.
#
# Usage:
#   cd src/pymicroscope/acquisition/epiphan
#   ./build_dylib.sh             # builds with -mmacosx-version-min=10.9
#   MACOS_MIN=11.0 ./build_dylib.sh
#
# Requirements:
#   - macOS with Xcode command-line tools (clang).
#   - The static archives libfrmgrab.a libslava.a libjpeg.a libpng.a libz.a in this dir.

set -euo pipefail
cd "$(dirname "$0")"

MACOS_MIN="${MACOS_MIN:-10.9}"
ARCH="${ARCH:-x86_64}"
OUTPUT="libfrmgrab.dylib"

if [ -f "$OUTPUT" ]; then
    cp "$OUTPUT" "${OUTPUT}.bak"
    echo "Backed up existing $OUTPUT to ${OUTPUT}.bak"
fi

clang -dynamiclib -arch "$ARCH" \
    -mmacosx-version-min="$MACOS_MIN" \
    -install_name "@rpath/$OUTPUT" \
    -Wl,-force_load,libfrmgrab.a \
    libslava.a libjpeg.a libpng.a libz.a \
    -framework CoreFoundation \
    -framework IOKit \
    -framework CoreServices \
    -lexpat -lc++ \
    -o "$OUTPUT"

echo "Built $OUTPUT (arch=$ARCH, min=$MACOS_MIN)"
file "$OUTPUT"
