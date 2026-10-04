# Shared by the installer and the TopSolid AppImage (sourced; needs TSL_VERSION)
GEARLEVER="${GEARLEVER:-it.mijorus.gearlever}"

# the name of a TopSolid AppImage shows the TopSo'Linux version that made it
versioned_name()  # PATH
{
    local dir="${1%/*}" base="${1##*/}"
    base="$(printf %s "$base" | sed -E 's/[-_]topsolinux[-_]([0-9]+(\.[0-9]+)*|dev)//I')"
    case "$base" in
        *-x86_64.*) base="${base/-x86_64./-TopSoLinux-$TSL_VERSION-x86_64.}" ;;
        *.*) base="${base%.*}_topsolinux-$TSL_VERSION.${base##*.}" ;;
        *) base="${base}_topsolinux-$TSL_VERSION" ;;
    esac
    echo "$dir/$base"
}

# the app menu entries that start OLD start NEW
retarget_desktop_files()  # OLD NEW
{
    local f o n
    o="$(printf %s "$1" | sed 's/[][\/.*^$&]/\\&/g')"
    n="$(printf %s "$2" | sed 's/[\/&]/\\&/g')"
    grep -lsF --null "$1" "$HOME/.local/share/applications/"*.desktop |
        while IFS= read -r -d '' f; do sed -i "s/$o/$n/g" "$f"; done
    # Gear Lever keeps its settings per app under the md5 of the path
    f="$HOME/.var/app/$GEARLEVER/config/gearlever.conf"
    [ -f "$f" ] || return 0
    sed -i -e "s/^\[app\.$(printf %s "$1" | md5sum | cut -c1-32)/[app.$(printf %s "$2" | md5sum | cut -c1-32)/" \
        -e "s/^file_path = $o\$/file_path = $n/" "$f"
}
