# Shared by the installer and the TopSolid AppImage (sourced; needs TSL_VERSION and LOG)
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

# the command that installs a distribution package, run as root
package_install_command()
{
    if command -v apt-get >/dev/null; then echo "apt-get install -y $*"
    elif command -v dnf >/dev/null; then echo "dnf install -y $*"
    elif command -v zypper >/dev/null; then echo "zypper --non-interactive install $*"
    elif command -v pacman >/dev/null; then echo "pacman -S --noconfirm $*"
    fi
}

gearlever_installed() { command -v flatpak >/dev/null && flatpak info "$GEARLEVER" >/dev/null 2>&1; }

# Gear Lever from Flathub, and Flatpak itself when missing (that asks for the password)
install_gearlever()
{
    local cmd
    gearlever_installed && return 0
    if ! command -v flatpak >/dev/null; then
        cmd="$(package_install_command flatpak)"
        [ -n "$cmd" ] && command -v pkexec >/dev/null && pkexec sh -c "$cmd" >> "$LOG" 2>&1
    fi
    command -v flatpak >/dev/null || return 1
    flatpak remote-add --user --if-not-exists flathub https://dl.flathub.org/repo/flathub.flatpakrepo >> "$LOG" 2>&1
    flatpak install --user -y --noninteractive flathub "$GEARLEVER" >> "$LOG" 2>&1
    gearlever_installed
}

# Gear Lever moves FILE to its folder and adds it to the app menu. Prints where FILE is then, with the
# TopSo'Linux version back in its name: Gear Lever names it after the app (topsolid_7.20.appimage)
integrate_appimage()  # FILE
{
    local out new
    out="$(flatpak run "$GEARLEVER" --integrate "$1" -y 2>&1)"
    echo "$out" >> "$LOG"
    out="$(echo "$out" | sed -n 's/^\(\/.*\) was integrated successfully.*/\1/p' | tail -1)"
    [ -f "$out" ] || return 1
    new="$(versioned_name "$out")"
    if [ "$new" != "$out" ] && mv -f "$out" "$new"; then
        retarget_desktop_files "$out" "$new"
        out="$new"
    fi
    echo "$out"
}
