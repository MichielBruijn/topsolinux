#!/bin/bash
# Build topsolinux-installer-x86_64.AppImage.
#
# usage: ./build.sh [WINE_DIST]
#   WINE_DIST  folder with a built Wine (usr/bin, usr/lib/wine, ...), as made by wine/build-wine.sh;
#              built from source when left out
#
# Needs: x86_64-w64-mingw32-gcc, Samba's ntlm_auth (package winbind), cabextract, winetricks, curl.
set -eu
TOP="$(dirname "$(readlink -f "$0")")"
BUILD="$TOP/build"
DIR="$BUILD/AppDir"
TSL_VERSION="$(cat "$TOP/VERSION")"
OUT="$TOP/TopSoLinux-Installer-$TSL_VERSION-x86_64.AppImage"
TOOLS="$DIR/usr/lib/topsolinux"
mkdir -p "$BUILD"

# --- Wine -------------------------------------------------------------------------------------------
WINE_DIST="${1:-$BUILD/wine-dist}"
[ -x "$WINE_DIST/usr/bin/wine" ] || "$TOP/wine/build-wine.sh" "$WINE_DIST"

rm -rf "$DIR"
mkdir -p "$DIR/usr" "$TOOLS/bin" "$TOOLS/lib" "$DIR/usr/share/topsolinux" "$DIR/usr/share/doc/topsolinux"
cp -a "$WINE_DIST/usr/bin" "$WINE_DIST/usr/lib" "$WINE_DIST/usr/share" "$DIR/usr/"
rm -rf "$DIR/usr/lib/ntlm_auth" "$DIR/usr/lib/topsolinux.old"

# --- a binary with the shared libraries it needs, except the C library (always taken from the system)
bundle()  # BINARY DESTBIN DESTLIB
{
    cp -L "$1" "$2/"
    ldd "$1" | awk '/=> \// {print $3}' | while read -r lib; do
        case "$(basename "$lib")" in
            libc.so*|libm.so*|libdl.so*|libpthread.so*|librt.so*|ld-linux*|libresolv.so*) ;;
            *) [ -e "$3/$(basename "$lib")" ] || cp -L "$lib" "$3/" ;;
        esac
    done
}

# Samba's ntlm_auth: Wine's NTLM needs it and many desktops don't have it (package winbind)
NA="$DIR/usr/lib/ntlm_auth"
mkdir -p "$NA/bin" "$NA/lib"
bundle "$(command -v ntlm_auth)" "$NA/lib" "$NA/lib"
mv "$NA/lib/ntlm_auth" "$NA/lib/ntlm_auth.real"
# its own configuration, so a system smb.conf (or its absence) doesn't matter
printf '[global]\n' > "$NA/lib/smb.conf"
cat > "$NA/bin/ntlm_auth" <<'EOF'
#!/bin/sh
# Samba's ntlm_auth for Wine's NTLM, used when the system has none (package winbind)
lib="$(dirname "$(readlink -f "$0")")/../lib"
LD_LIBRARY_PATH="$lib${LD_LIBRARY_PATH:+:$LD_LIBRARY_PATH}" exec "$lib/ntlm_auth.real" --configfile="$lib/smb.conf" "$@"
EOF
chmod +x "$NA/bin/ntlm_auth"
"$NA/bin/ntlm_auth" --version

# winetricks and cabextract (needed by winetricks, often not installed)
cp "$(command -v winetricks)" "$TOOLS/bin/"
bundle "$(command -v cabextract)" "$TOOLS/bin" "$TOOLS/lib"

# appimagetool and the AppImage runtime, for building a TopSolid AppImage without network access
[ -f "$BUILD/appimagetool.AppImage" ] ||
    curl -fL -o "$BUILD/appimagetool.AppImage" https://github.com/AppImage/appimagetool/releases/download/continuous/appimagetool-x86_64.AppImage
[ -f "$BUILD/runtime-x86_64" ] ||
    curl -fL -o "$BUILD/runtime-x86_64" https://github.com/AppImage/type2-runtime/releases/download/continuous/runtime-x86_64
cp "$BUILD/appimagetool.AppImage" "$BUILD/runtime-x86_64" "$TOOLS/"
chmod +x "$TOOLS/appimagetool.AppImage"

# --- topsolinux itself ------------------------------------------------------------------------------
x86_64-w64-mingw32-gcc -O2 -s -o "$TOOLS/unstick.exe" "$TOP/installer/tools/unstick.c"
# the managed stacks for the debug command (needs the .NET SDK; DOTNET=path/to/dotnet)
DOTNET="${DOTNET:-$(command -v dotnet || true)}"
if [ -n "$DOTNET" ]; then
    DOTNET_CLI_TELEMETRY_OPTOUT=1 "$DOTNET" build "$TOP/installer/tools/clrstack/clrstack.csproj" -c Release -nologo \
        -v q -o "$TOOLS/clrstack" >/dev/null || exit 1
    rm -f "$TOOLS/clrstack/"*.pdb
else
    echo "warning: no dotnet, the debug command will show only the end of the log" >&2
fi
cp "$TOP/installer/tools/exeicon.py" "$TOP/installer/tools/fetchmedia.py" "$TOP/installer/tools/userconfig.py" \
    "$TOP/installer/tools/progress.py" "$TOP/installer/tools/splash.py" "$TOP/installer/tools/appimage-name.sh" \
    "$TOP/installer/tools/prefix-settings.sh" \
    "$TOP/installer/tools/desktop-dpi" "$TOOLS/"
cp -r "$TOP/installer/data/reg" "$TOP/installer/data/sql" "$DIR/usr/share/topsolinux/"
cp "$TOP/VERSION" "$DIR/usr/share/topsolinux/VERSION"
# the Gecko version this Wine expects, so the installer can fetch it beforehand
strings -el "$DIR/usr/lib/wine/x86_64-windows/appwiz.cpl" | grep -o 'wine-gecko-[0-9.]*-x86_64.msi' | head -1 |
    sed 's/wine-gecko-\(.*\)-x86_64.msi/#define GECKO_VERSION "\1"/' > "$DIR/usr/share/topsolinux/wine-addons"
cp "$TOP/README.md" "$TOP/LICENSE" "$TOP/NOTICE.md" "$DIR/usr/share/doc/topsolinux/"
cp "$TOP/installer/AppRun" "$TOP/installer/topsolinux-run" "$DIR/"
chmod +x "$DIR/AppRun" "$DIR/topsolinux-run"
# the dialogs use the SVG; file managers and Gear Lever want a PNG as .DirIcon
cp "$TOP/installer/topsolinux.svg" "$TOP/installer/topsolinux.png" "$DIR/"
ln -s topsolinux.png "$DIR/.DirIcon"
mkdir -p "$DIR/usr/share/icons/hicolor/256x256/apps"
cp "$TOP/installer/topsolinux.png" "$DIR/usr/share/icons/hicolor/256x256/apps/"
cat > "$DIR/topsolinux.desktop" <<'EOF'
[Desktop Entry]
Type=Application
Name=TopSo'Linux Installer
Comment=Install TopSolid on Linux
Exec=AppRun
Icon=topsolinux
Categories=Utility;
Terminal=false
EOF

# the versions of the bundled third-party binaries, for NOTICE.md
{
    echo "Wine: upstream $(cat "$TOP/wine/UPSTREAM_COMMIT") with the patches in wine/patches"
    for f in "$(command -v ntlm_auth)" "$(command -v cabextract)" "$(command -v winetricks)"; do
        dpkg -S "$(readlink -f "$f")" 2>/dev/null | cut -d: -f1 | xargs -r dpkg-query -W -f='${Package} ${Version} (source: ${source:Package} ${source:Version})\n'
    done
    for lib in "$NA"/lib/*.so* "$TOOLS"/lib/*.so*; do
        dpkg -S "$(basename "$lib")" 2>/dev/null | head -1 | cut -d: -f1
    done | sort -u | xargs -r dpkg-query -W -f='${Package} ${Version} (source: ${source:Package} ${source:Version})\n'
} | sort -u > "$DIR/usr/share/doc/topsolinux/bundled-versions.txt"

ARCH=x86_64 "$BUILD/appimagetool.AppImage" --comp zstd --runtime-file "$BUILD/runtime-x86_64" "$DIR" "$OUT"
ls -la "$OUT"
