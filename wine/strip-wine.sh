#!/bin/bash
# Strip debug info from an installed Wine (DIR/usr/...); it makes Wine several times larger.
#
# usage: wine/strip-wine.sh DIR
set -eu
OUT="${1:?usage: $0 DIR}"
find "$OUT/usr" -type f \( -name '*.so' -o -path '*/bin/*' \) -exec strip --strip-debug {} + 2>/dev/null || true
find "$OUT/usr/lib/wine/x86_64-windows" -type f -exec x86_64-w64-mingw32-strip --strip-debug {} + 2>/dev/null || true
find "$OUT/usr/lib/wine/i386-windows" -type f -exec i686-w64-mingw32-strip --strip-debug {} + 2>/dev/null || true
