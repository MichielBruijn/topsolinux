#!/bin/bash
# Build the patched Wine used by topsolinux.
#
# usage: wine/build-wine.sh OUTDIR
#   OUTDIR receives usr/bin, usr/lib/wine and usr/share/wine (stripped), ready for the installer.
#
# Needs the usual Wine build dependencies (see https://gitlab.winehq.org/wine/wine/-/wikis/Building-Wine),
# including the MinGW cross compilers for i386 and x86_64.
set -eu
HERE="$(dirname "$(readlink -f "$0")")"
OUT="$(readlink -f "${1:?usage: $0 OUTDIR}")"
SRC="${WINE_SRC:-$HERE/../build/wine-src}"
BUILD="${WINE_BUILD:-$HERE/../build/wine-build}"
COMMIT="$(cat "$HERE/UPSTREAM_COMMIT")"

if [ ! -d "$SRC/.git" ]; then
    git clone https://gitlab.winehq.org/wine/wine.git "$SRC"
fi
git -C "$SRC" fetch -q origin "$COMMIT" 2>/dev/null || true
git -C "$SRC" checkout -q -B topsolinux "$COMMIT"
git -C "$SRC" -c user.name=topsolinux -c user.email=topsolinux@invalid am -q "$HERE"/patches/*.patch
# tdxnavlib is a new dll: regenerate the build files
(cd "$SRC" && tools/make_makefiles >/dev/null && autoreconf -f >/dev/null 2>&1)

mkdir -p "$BUILD"
cd "$BUILD"
[ -f Makefile ] || "$SRC/configure" --enable-archs=i386,x86_64 --prefix=/usr
make -j"$(nproc)"
rm -rf "$OUT/usr"
make install-lib DESTDIR="$OUT" >/dev/null

# debug info makes Wine several times larger
find "$OUT/usr" -type f \( -name '*.so' -o -path '*/bin/*' \) -exec strip --strip-debug {} + 2>/dev/null || true
find "$OUT/usr/lib/wine/x86_64-windows" -type f -exec x86_64-w64-mingw32-strip --strip-debug {} + 2>/dev/null || true
find "$OUT/usr/lib/wine/i386-windows" -type f -exec i686-w64-mingw32-strip --strip-debug {} + 2>/dev/null || true
du -sh "$OUT/usr"
